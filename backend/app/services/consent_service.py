"""
Consent Management Service.

Handles the full DPDP consent lifecycle:
- Grant consent (with purpose, scope, expiry)
- Modify consent scope
- Withdraw consent (immediate revocation)
- Expiry tracking
- Consent receipt generation

Consent Types (DPDP Act Section 5-6):
- healthcare_treatment
- pharmacy_access
- research_access
- insurance_access
- analytics_access
- marketing_access
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.services.encryption_service import get_encryption_service
from app.services.provider_directory import resolve_recipient

from app.utils.helpers import generate_uuid, utc_now, utc_now_datetime
from app.utils.errors import NotFoundError, ValidationError, AuthorizationError
from app.utils.constants import ConsentType, ConsentStatus, PURPOSE_LIMITATION_MATRIX


VALID_CONSENT_TYPES = [ct.value for ct in ConsentType]


class ConsentService:
    """Manages DPDP consent lifecycle operations."""

    def __init__(self, db):
        self.db = db
        self.consents = db["consents"]
        self.receipts = db["consent_receipts"]
        self.patients = db["patients"]

    # ─────────────────────────────────────────────────────────────────
    # GRANT
    # ─────────────────────────────────────────────────────────────────

    def grant_consent(
        self,
        user_id: str,
        patient_id: str,
        consent_type: str,
        processing_entity_name: str,
        expiry_days: int = 365,
        custom_scope: list[str] = None,
        patient_did: str = None,
        doctor_did: str = None,
        recipient: dict = None,
        selected_allergies: list[str] = None,
    ) -> dict:
        """
        Grant consent for a specific processing purpose.

        Args:
            user_id: UUID of the user granting consent
            patient_id: UUID of the patient profile
            consent_type: One of the 6 consent types
            processing_entity_name: Name of entity receiving access
            expiry_days: Days until consent expires (default 365)
            custom_scope: Override default scope (optional)
            patient_did: OPTIONAL SIH DID of the patient (nullable, additive).
                Recorded for cross-referencing only; consent works without it.
            doctor_did: OPTIONAL SIH DID of the receiving doctor/entity (nullable,
                additive). Recorded for cross-referencing only.

        Returns:
            Dict with consent document and receipt

        Raises:
            ValidationError: Invalid inputs or duplicate active consent
        """
        recipient_key = None
        if consent_type == "healthcare_treatment" or recipient is not None:
            recipient_key, processing_entity_name = resolve_recipient(self.db, recipient)
        self._validate_grant(consent_type, processing_entity_name, expiry_days)

        # Check for existing active consent of same type
        existing = self.get_active_consent(patient_id, consent_type, recipient_key)
        if existing:
            raise ValidationError(
                f"Active consent already exists for {consent_type} and this recipient. "
                "Withdraw or modify the existing consent first."
            )

        allowed = [category.value for category in PURPOSE_LIMITATION_MATRIX[ConsentType(consent_type)]]
        data_categories = allowed if custom_scope is None else self._validated_scope(consent_type, custom_scope)

        granted_at = utc_now_datetime()
        now = granted_at.isoformat()
        expires_at = (granted_at + timedelta(days=expiry_days)).isoformat()

        consent_id = generate_uuid()
        consent_doc = {
            "_id": consent_id,
            "patient_id": patient_id,
            "user_id": user_id,
            "consent_type": consent_type,
            "status": ConsentStatus.ACTIVE.value,
            "purpose_description": self._get_purpose_description(consent_type),
            "data_categories_in_scope": data_categories,
            "processing_entity_id": recipient_key,
            "allergy_selection": self._allergy_selection(patient_id, data_categories, selected_allergies),
            "processing_entity_name": processing_entity_name,
            "granted_at": now,
            "expires_at": expires_at,
            "withdrawn_at": None,
            "withdrawal_reason": None,
            "modified_at": None,
            "previous_scope": None,
            "modification_reason": None,
            "consent_hash": None,
            "blockchain_tx_ref": None,
            "blockchain_anchor_id": None,
            # Optional SIH identity bridge (nullable, additive). Null when the
            # patient/doctor has no DID — consent behaves exactly as before.
            "patient_did": patient_did or None,
            "doctor_did": doctor_did or None,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id,
        }

        try:
            self.consents.insert_one(consent_doc)
        except DuplicateKeyError:
            raise ValidationError("Active consent already exists for this purpose and recipient.")

        # Generate receipt
        receipt = self._generate_receipt(consent_doc, "grant")

        return {"consent": consent_doc, "receipt": receipt}

    # ─────────────────────────────────────────────────────────────────
    # LIST / GET
    # ─────────────────────────────────────────────────────────────────

    def list_consents(
        self,
        patient_id: str,
        status: str = None,
        consent_type: str = None,
    ) -> list:
        """
        List all consents for a patient.

        Args:
            patient_id: UUID of the patient
            status: Filter by status (optional)
            consent_type: Filter by type (optional)

        Returns:
            List of consent documents
        """
        self.check_and_expire_consents(patient_id)
        query = {"patient_id": patient_id}
        if status:
            query["status"] = status
        if consent_type:
            query["consent_type"] = consent_type

        return list(self.consents.find(query).sort("created_at", -1))

    def get_consent(self, consent_id: str, user_id: str) -> dict:
        """
        Get a single consent by ID (ownership enforced).

        Args:
            consent_id: UUID of the consent
            user_id: UUID of requesting user

        Returns:
            Consent document

        Raises:
            NotFoundError: Consent not found
            AuthorizationError: User doesn't own this consent
        """
        consent = self.consents.find_one({"_id": consent_id})
        if not consent:
            raise NotFoundError("Consent not found")

        if consent["user_id"] != user_id:
            raise AuthorizationError("You can only access your own consents")

        self._expire_if_due(consent, utc_now_datetime())
        return consent

    def get_active_consent(self, patient_id: str, consent_type: str, recipient_key: str) -> Optional[dict]:
        """
        Check if patient has active consent of a specific type.

        Used by other services for consent enforcement.

        Returns:
            Active consent document or None
        """
        for consent in self.consents.find({
            "patient_id": patient_id,
            "processing_entity_id": recipient_key,
            "consent_type": consent_type,
            "status": ConsentStatus.ACTIVE.value,
        }):
            self._expire_if_due(consent, utc_now_datetime())
            if consent["status"] == ConsentStatus.ACTIVE.value:
                return consent
        return None

    def latest_inactive_consent(self, patient_id: str, consent_type: str, recipient_keys: list) -> Optional[dict]:
        return self.consents.find_one(
            {"patient_id": patient_id, "consent_type": consent_type,
             "processing_entity_id": {"$in": recipient_keys}, "status": {"$in": [ConsentStatus.EXPIRED.value, ConsentStatus.WITHDRAWN.value]}},
            sort=[("granted_at", -1)],
        )

    # ─────────────────────────────────────────────────────────────────
    # MODIFY
    # ─────────────────────────────────────────────────────────────────

    def modify_consent(
        self,
        consent_id: str,
        user_id: str,
        new_scope: list[str],
        reason: str,
        selected_allergies: list[str] = None,
    ) -> dict:
        """
        Modify consent scope (data categories).

        Args:
            consent_id: UUID of the consent to modify
            user_id: UUID of the user modifying
            new_scope: New list of data categories
            reason: Reason for modification

        Returns:
            Dict with updated consent and receipt

        Raises:
            NotFoundError: Consent not found
            AuthorizationError: Not owner
            ValidationError: Invalid scope or not active
        """
        consent = self.get_consent(consent_id, user_id)
        if consent["status"] != ConsentStatus.ACTIVE.value:
            raise ValidationError("Can only modify active consents")

        new_scope = self._validated_scope(consent["consent_type"], new_scope)

        if not reason or len(reason.strip()) < 5:
            raise ValidationError("Modification reason required (min 5 characters)")

        now = utc_now()
        previous_scope = consent.get("data_categories_in_scope")

        updated = self.consents.find_one_and_update(
            {"_id": consent_id, "status": ConsentStatus.ACTIVE.value, "version": consent.get("version")},
            {"$set": {
                "data_categories_in_scope": new_scope,
                "allergy_selection": self._allergy_selection(consent["patient_id"], new_scope, selected_allergies),
                "previous_scope": previous_scope,
                "modification_reason": reason,
                "modified_at": now,
                "updated_at": now,
                "updated_by": user_id,
                "version": consent.get("version", 1) + 1,
            }},
            return_document=ReturnDocument.AFTER,
        )

        if updated is None:
            raise ValidationError("Consent has changed. Refresh and try again.")

        receipt = self._generate_receipt(updated, "modify")

        return {"consent": updated, "receipt": receipt}

    # ─────────────────────────────────────────────────────────────────
    # WITHDRAW
    # ─────────────────────────────────────────────────────────────────

    def withdraw_consent(
        self,
        consent_id: str,
        user_id: str,
        reason: str = None,
    ) -> dict:
        """
        Withdraw consent (immediate access revocation).

        Per DPDP Act Section 6(6), withdrawal is immediate and irrevocable
        for the current consent period. Patient can re-grant later.

        Args:
            consent_id: UUID of the consent to withdraw
            user_id: UUID of the user withdrawing
            reason: Optional reason for withdrawal

        Returns:
            Dict with withdrawn consent and receipt

        Raises:
            NotFoundError: Consent not found
            AuthorizationError: Not owner
            ValidationError: Consent not active
        """
        consent = self.get_consent(consent_id, user_id)
        if consent["status"] != ConsentStatus.ACTIVE.value:
            raise ValidationError("Can only withdraw active consents")

        now = utc_now()

        update = self.consents.update_one(
            {"_id": consent_id, "status": ConsentStatus.ACTIVE.value, "version": consent.get("version")},
            {"$set": {
                "status": ConsentStatus.WITHDRAWN.value,
                "withdrawn_at": now,
                "withdrawal_reason": reason or "Patient exercised right to withdraw",
                "updated_at": now,
                "updated_by": user_id,
                "version": consent.get("version", 1) + 1,
            }}
        )

        if not update.matched_count:
            raise ValidationError("Consent has changed. Refresh and try again.")

        updated = self.consents.find_one({"_id": consent_id})
        receipt = self._generate_receipt(updated, "withdraw")

        return {"consent": updated, "receipt": receipt}

    # ─────────────────────────────────────────────────────────────────
    # EXPIRY
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _expiry_utc(value) -> Optional[datetime]:
        """Read ISO timestamps and UTC datetimes returned by PyMongo."""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return None
        if not isinstance(value, datetime):
            return None
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _expire_if_due(self, consent: dict, now: datetime) -> bool:
        if consent["status"] != ConsentStatus.ACTIVE.value:
            return False
        deadline = self._expiry_utc(consent.get("expires_at"))
        if deadline is not None and now < deadline:
            return False

        # Missing or unreadable deadlines cannot authorize access. Only the
        # first reader transitions the grant; a concurrent withdrawal wins.
        changes = {"status": ConsentStatus.EXPIRED.value, "updated_at": now.isoformat()}
        result = self.consents.update_one(
            {"_id": consent["_id"], "status": ConsentStatus.ACTIVE.value},
            {"$set": changes},
        )
        if result.matched_count:
            consent.update(changes)
        else:
            current = self.consents.find_one({"_id": consent["_id"]})
            consent.update(current or changes)
        return bool(result.modified_count)

    def check_and_expire_consents(self, patient_id: str = None) -> int:
        """Persist elapsed grants, optionally scoped to a single patient."""
        query = {"status": ConsentStatus.ACTIVE.value}
        if patient_id is not None:
            query["patient_id"] = patient_id
        now = utc_now_datetime()
        return sum(self._expire_if_due(consent, now) for consent in self.consents.find(query))

    def get_expiring_soon(self, patient_id: str, days: int = 7) -> list:
        """
        Get consents expiring within N days.

        Args:
            patient_id: UUID of the patient
            days: Look-ahead window (default 7)

        Returns:
            List of consents expiring soon
        """
        now = utc_now_datetime()
        threshold = now + timedelta(days=days)
        expiring = []
        for consent in self.get_active_sharing(patient_id):
            deadline = self._expiry_utc(consent.get("expires_at"))
            if deadline is not None and now < deadline <= threshold:
                expiring.append(consent)
        return expiring

    # ─────────────────────────────────────────────────────────────────
    # RECEIPTS
    # ─────────────────────────────────────────────────────────────────

    def list_receipts(self, patient_id: str) -> list:
        """List all consent receipts for a patient."""
        return list(self.receipts.find({"patient_id": patient_id}).sort("issued_at", -1))

    def get_receipt(self, receipt_id: str, user_id: str) -> dict:
        """Get a specific receipt (ownership enforced)."""
        receipt = self.receipts.find_one({"_id": receipt_id})
        if not receipt:
            raise NotFoundError("Receipt not found")
        if receipt["user_id"] != user_id:
            raise AuthorizationError("You can only access your own receipts")
        return receipt

    # ─────────────────────────────────────────────────────────────────
    # ACTIVE SHARING
    # ─────────────────────────────────────────────────────────────────

    def get_active_sharing(self, patient_id: str) -> list:
        """
        Get all entities with active access to patient data.

        Returns:
            List of active consents showing who has access and to what.
        """
        self.check_and_expire_consents(patient_id)
        return list(self.consents.find({
            "patient_id": patient_id,
            "status": ConsentStatus.ACTIVE.value,
        }).sort("granted_at", -1))

    # ─────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _allergy_selection(self, patient_id, scope, selected):
        if selected is None:
            selected = []
        if not isinstance(selected, list) or any(not isinstance(a, str) or not a.strip() for a in selected):
            raise ValidationError("Select allergies from your saved profile.")
        if selected:
            patient = self.patients.find_one({"_id": patient_id}, {"allergies": 1})
            saved = get_encryption_service().decrypt_field((patient or {}).get("allergies"))
            if "allergies" not in scope or not isinstance(saved, list) or any(a not in saved for a in selected):
                raise ValidationError("Only saved allergies within the selected scope can be shared.")
        return get_encryption_service().encrypt_field(list(dict.fromkeys(selected)))

    @staticmethod
    def selected_allergies(consent):
        values = get_encryption_service().decrypt_field(consent.get("allergy_selection"))
        return [a for a in values if isinstance(a, str)] if isinstance(values, list) else []

    @classmethod
    def patient_view(cls, document):
        result = dict(document)
        result["selected_allergies"] = cls.selected_allergies(document)
        result.pop("allergy_selection", None)
        return result

    @staticmethod
    def _validated_scope(consent_type: str, scope: list) -> list[str]:
        allowed = PURPOSE_LIMITATION_MATRIX[ConsentType(consent_type)]
        if not isinstance(scope, list) or (allowed and not scope):
            raise ValidationError("Select at least one permitted data category.")
        if any(not isinstance(category, str) or category not in allowed for category in scope):
            raise ValidationError("The selected data categories are outside this consent purpose.")
        return list(dict.fromkeys(scope))

    def _validate_grant(self, consent_type: str, entity_name: str, expiry_days: int) -> None:
        """Validate consent grant inputs."""
        errors = {}

        if consent_type not in VALID_CONSENT_TYPES:
            errors["consent_type"] = f"Must be one of: {VALID_CONSENT_TYPES}"

        if not entity_name or len(entity_name.strip()) < 2:
            errors["processing_entity_name"] = "Processing entity name required"

        if not isinstance(expiry_days, int) or expiry_days < 1 or expiry_days > 730:
            errors["expiry_days"] = "Expiry must be between 1 and 730 days"

        if errors:
            raise ValidationError("Validation failed", details=errors)

    def _generate_receipt(self, consent: dict, action_type: str) -> dict:
        """Generate a consent receipt document."""
        receipt_id = generate_uuid()
        now = utc_now()

        receipt_doc = {
            "_id": receipt_id,
            "consent_id": consent["_id"],
            "patient_id": consent["patient_id"],
            "user_id": consent["user_id"],
            "action_type": action_type,
            "consent_type": consent["consent_type"],
            "purpose_description": consent["purpose_description"],
            "data_categories": consent["data_categories_in_scope"],
            "scope_before": consent.get("previous_scope"),
            "scope_after": consent["data_categories_in_scope"] if action_type == "modify" else None,
            "expiry_date": consent["expires_at"],
            "processing_entity_name": consent["processing_entity_name"],
            "processing_entity_id": consent.get("processing_entity_id"),
            "allergy_selection": consent.get("allergy_selection"),
            "blockchain_tx_ref": None,
            "blockchain_anchor_id": None,
            "receipt_hash": None,
            "issued_at": now,
        }

        self.receipts.insert_one(receipt_doc)
        return receipt_doc

    @staticmethod
    def _get_purpose_description(consent_type: str) -> str:
        """Get human-readable purpose description."""
        descriptions = {
            ConsentType.HEALTHCARE_TREATMENT.value: (
                "Access to medical records for diagnosis and treatment by authorized healthcare providers"
            ),
            ConsentType.PHARMACY_ACCESS.value: (
                "Access to prescriptions and allergy information for medication dispensing"
            ),
            ConsentType.RESEARCH_ACCESS.value: (
                "Access to anonymized health data for approved clinical research"
            ),
            ConsentType.INSURANCE_ACCESS.value: (
                "Access to medical history and prescriptions for insurance claims processing"
            ),
            ConsentType.ANALYTICS_ACCESS.value: (
                "Access to aggregated health statistics for population health analytics"
            ),
            ConsentType.MARKETING_ACCESS.value: (
                "Access to contact information for healthcare service communications"
            ),
        }
        return descriptions.get(consent_type, "Data processing as specified")
