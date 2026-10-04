"""
Healthcare Record Service.

Handles CRUD operations for healthcare records (consultations, diagnoses, etc.).
Enforces ownership: patients see only their own records.
All sensitive clinical data encrypted before storage.
"""

from app.utils.helpers import generate_uuid, utc_now
from app.utils.errors import NotFoundError, ValidationError, AuthorizationError
from app.services.encryption_service import get_encryption_service


VALID_RECORD_TYPES = ["consultation", "diagnosis", "treatment_plan", "follow_up", "discharge_summary"]


class HealthcareRecordService:
    """Manages healthcare record CRUD operations."""

    def __init__(self, db):
        self.db = db
        self.records = db["healthcare_records"]
        self.patients = db["patients"]
        self.users = db["users"]
        self.enc = get_encryption_service()

    # ─────────────────────────────────────────────────────────────────
    # PROVENANCE (derived at read time — no stored/migrated fields)
    # ─────────────────────────────────────────────────────────────────

    def _provider_org(self) -> str:
        """Configured healthcare-provider/organization display name."""
        import os
        from app.config import get_config
        cfg = get_config(os.environ.get("FLASK_ENV", "development"))
        return getattr(cfg, "PROVIDER_ORG_NAME", "Healthcare Provider")

    def _with_provenance(self, record: dict) -> dict:
        """
        Attach derived, NON-PERSISTED provenance to a decrypted record so the UI
        can show its healthcare-provider origin. Derived from the existing
        `created_by` user_id + the configured org name — nothing is stored.
            created_by_name  — full name of the creating user (fallback generic)
            created_by_role  — role of the creating user (doctor/admin/patient)
            provider_org     — configured organization name
        """
        if not record:
            return record
        creator = None
        created_by = record.get("created_by")
        if created_by:
            creator = self.users.find_one({"_id": created_by})
        role = (creator or {}).get("role")
        record["created_by_name"] = (creator or {}).get("full_name") or (
            "Healthcare Provider" if role in ("doctor", "admin") else "You"
        )
        record["created_by_role"] = role
        # A record authored by a provider (doctor/admin) carries the org as its
        # source; a patient-self-authored record is sourced to the patient.
        record["provider_org"] = self._provider_org() if role in ("doctor", "admin") else "Self-reported"
        return record

    # ─────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────

    def create_record(
        self,
        patient_id: str,
        created_by: str,
        record_type: str,
        title: str,
        description: str,
        diagnosis_codes: list = None,
        symptoms: list = None,
        treatment_notes: str = None,
    ) -> dict:
        """
        Create a new healthcare record.

        Args:
            patient_id: UUID of patient this record belongs to
            created_by: UUID of user creating the record
            record_type: Type of record (consultation, diagnosis, etc.)
            title: Record title
            description: Detailed clinical notes
            diagnosis_codes: ICD-10 codes (optional)
            symptoms: Reported symptoms (optional)
            treatment_notes: Treatment details (optional)

        Returns:
            Created healthcare record document

        Raises:
            ValidationError: Invalid inputs
            NotFoundError: Patient not found
        """
        # Validate inputs
        self._validate_create_inputs(patient_id, record_type, title, description)

        # Verify patient exists
        patient = self.patients.find_one({"_id": patient_id})
        if not patient:
            raise NotFoundError(f"Patient {patient_id} not found")

        record_id = generate_uuid()
        now = utc_now()

        record_doc = {
            "_id": record_id,
            "patient_id": patient_id,
            "record_type": record_type,
            "title": title,
            "description": description,
            "diagnosis_codes": diagnosis_codes or [],
            "symptoms": symptoms or [],
            "treatment_notes": treatment_notes or "",
            "follow_up_date": None,
            "status": "active",
            "version": 1,
            "redacted": False,
            "redacted_at": None,
            "redacted_by": None,
            "redaction_reason": None,
            "verification_hash": None,
            "blockchain_tx_ref": None,
            "blockchain_anchor_id": None,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "updated_by": created_by,
        }

        # Encrypt and store
        encrypted_doc = self.enc.encrypt_document(record_doc)
        self.records.insert_one(encrypted_doc)

        # Blockchain anchoring: hash the encrypted document
        try:
            from app.services.blockchain_service import BlockchainService
            from app.extensions import get_db, get_web3
            bc = BlockchainService(get_db(), get_web3())
            data_hash = bc.compute_record_hash(encrypted_doc)
            anchor = bc.anchor_record(
                resource_type="healthcare_records",
                resource_id=record_id,
                data_hash=data_hash,
                patient_id=patient_id,
            )
            # Update record with anchor references
            self.records.update_one(
                {"_id": record_id},
                {"$set": {
                    "verification_hash": data_hash,
                    "blockchain_tx_ref": anchor.get("transaction_hash"),
                    "blockchain_anchor_id": anchor["_id"],
                }}
            )
            record_doc["verification_hash"] = data_hash
            record_doc["blockchain_tx_ref"] = anchor.get("transaction_hash")
            record_doc["blockchain_anchor_id"] = anchor["_id"]
        except Exception:
            pass  # Blockchain anchoring is non-blocking; record still saved

        return record_doc

    # ─────────────────────────────────────────────────────────────────
    # READ
    # ─────────────────────────────────────────────────────────────────

    def get_record(self, record_id: str, requesting_user_id: str, user_role: str) -> dict:
        """
        Get a single healthcare record by ID.

        Ownership enforced: patients see only their own records.
        Admins can see all records.

        Args:
            record_id: UUID of the record
            requesting_user_id: UUID of the requesting user
            user_role: Role of the requesting user

        Returns:
            Healthcare record document

        Raises:
            NotFoundError: Record not found
            AuthorizationError: Patient trying to access another patient's record
        """
        record = self.records.find_one({"_id": record_id})
        if not record:
            raise NotFoundError("Healthcare record not found")

        # Ownership check for patients
        if user_role == "patient":
            patient = self.patients.find_one({"user_id": requesting_user_id})
            if not patient or record["patient_id"] != patient["_id"]:
                raise AuthorizationError("You can only access your own records")

        return self._with_provenance(self.enc.decrypt_document(record))

    def list_records_for_patient(
        self,
        patient_id: str,
        requesting_user_id: str,
        user_role: str,
        record_type: str = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list:
        """
        List healthcare records for a specific patient.

        Args:
            patient_id: UUID of the patient
            requesting_user_id: UUID of requesting user
            user_role: Role of requesting user
            record_type: Filter by type (optional)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of healthcare record documents
        """
        # Ownership check for patients
        if user_role == "patient":
            patient = self.patients.find_one({"user_id": requesting_user_id})
            if not patient or patient["_id"] != patient_id:
                raise AuthorizationError("You can only access your own records")

        query = {"patient_id": patient_id, "redacted": False}
        if record_type:
            query["record_type"] = record_type

        cursor = self.records.find(query).skip(skip).limit(limit).sort("created_at", -1)
        return [self._with_provenance(self.enc.decrypt_document(r)) for r in cursor]

    def list_my_records(
        self,
        user_id: str,
        record_type: str = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list:
        """
        List all records for the current patient (by user_id).

        Args:
            user_id: UUID of the patient's user account
            record_type: Optional filter
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of healthcare records
        """
        patient = self.patients.find_one({"user_id": user_id})
        if not patient:
            raise NotFoundError("Patient profile not found")

        query = {"patient_id": patient["_id"], "redacted": False}
        if record_type:
            query["record_type"] = record_type

        cursor = self.records.find(query).skip(skip).limit(limit).sort("created_at", -1)
        return [self._with_provenance(self.enc.decrypt_document(r)) for r in cursor]

    # ─────────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────────

    def update_record(
        self,
        record_id: str,
        requesting_user_id: str,
        user_role: str,
        updates: dict,
    ) -> dict:
        """
        Update a healthcare record.

        Patients can update only their own records.
        Admins can update any record.

        Args:
            record_id: UUID of the record
            requesting_user_id: UUID of the requesting user
            user_role: Role of the requesting user
            updates: Dict of field:value to update

        Returns:
            Updated record document
        """
        record = self.records.find_one({"_id": record_id})
        if not record:
            raise NotFoundError("Healthcare record not found")

        # Ownership check for patients
        if user_role == "patient":
            patient = self.patients.find_one({"user_id": requesting_user_id})
            if not patient or record["patient_id"] != patient["_id"]:
                raise AuthorizationError("You can only update your own records")

        # Only allow specific fields to be updated
        allowed_fields = {
            "title", "description", "diagnosis_codes", "symptoms",
            "treatment_notes", "follow_up_date", "status",
        }
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}
        if not filtered:
            raise ValidationError("No valid fields to update")

        filtered["updated_at"] = utc_now()
        filtered["updated_by"] = requesting_user_id
        filtered["version"] = record.get("version", 1) + 1

        encrypted_filtered = self.enc.encrypt_document(filtered)
        self.records.update_one({"_id": record_id}, {"$set": encrypted_filtered})

        # Re-anchor the updated record on blockchain
        try:
            from app.services.blockchain_service import BlockchainService
            from app.extensions import get_db, get_web3
            bc = BlockchainService(get_db(), get_web3())
            updated_raw = self.records.find_one({"_id": record_id})
            data_hash = bc.compute_record_hash(updated_raw)
            anchor = bc.anchor_record(
                resource_type="healthcare_records",
                resource_id=record_id,
                data_hash=data_hash,
                patient_id=record["patient_id"],
            )
            self.records.update_one(
                {"_id": record_id},
                {"$set": {
                    "verification_hash": data_hash,
                    "blockchain_tx_ref": anchor.get("transaction_hash"),
                    "blockchain_anchor_id": anchor["_id"],
                }}
            )
        except Exception:
            pass

        updated = self.records.find_one({"_id": record_id})
        return self.enc.decrypt_document(updated)

    # ─────────────────────────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────────────────────────

    def _validate_create_inputs(
        self, patient_id: str, record_type: str, title: str, description: str
    ) -> None:
        """Validate record creation inputs."""
        errors = {}

        if not patient_id:
            errors["patient_id"] = "Patient ID required"

        if record_type not in VALID_RECORD_TYPES:
            errors["record_type"] = f"Must be one of: {VALID_RECORD_TYPES}"

        if not title or len(title.strip()) < 3:
            errors["title"] = "Title required (min 3 characters)"

        if not description or len(description.strip()) < 10:
            errors["description"] = "Description required (min 10 characters)"

        if errors:
            raise ValidationError("Validation failed", details=errors)
