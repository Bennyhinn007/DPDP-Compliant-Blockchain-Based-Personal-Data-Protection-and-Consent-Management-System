"""
Doctor Service.

Provides consent-gated access to patient healthcare records.
Every access attempt is audited regardless of outcome.
"""

from app.utils.errors import NotFoundError, ConsentRequiredError
from app.services.encryption_service import get_encryption_service
from app.services.consent_service import ConsentService
from app.services.provider_directory import doctor_recipient_keys
from app.services.audit_service import AuditService


class DoctorService:
    """Manages doctor's consent-gated access to patient data."""

    def __init__(self, db):
        self.db = db
        self.patients = db["patients"]
        self.records = db["healthcare_records"]
        self.users = db["users"]
        self.enc = get_encryption_service()
        self.consent_svc = ConsentService(db)
        self.audit_svc = AuditService(db)

    def search_patients(self, query: str, doctor_id: str) -> list:
        """
        Search patients by name (decrypted match).

        Returns basic patient info without sensitive data.
        Does NOT require consent (searching ≠ accessing records).
        """
        # Get all non-redacted patients
        results = []

        recipient_keys = doctor_recipient_keys(self.db, doctor_id)
        for p in self.patients.find({"redacted": False}, {"full_name": 1, "user_id": 1}):
            decrypted = self.enc.decrypt_document(p)
            name = decrypted.get("full_name", "")
            if name and query.lower() in name.lower():
                results.append({
                    "_id": p["_id"],
                    "user_id": p["user_id"],
                    "full_name": name,
                    "has_treatment_consent": bool(self._chart_scope(self._chart_consent(p["_id"], recipient_keys))),
                })
                if len(results) >= 50:
                    break

        # Audit the search
        self.audit_svc.log_event(
            actor_id=doctor_id,
            actor_role="doctor",
            action_type="read",
            resource_type="patients",
            reason=f"Patient search: '{query}'",
            details={"search_query": query, "results_count": len(results)},
        )

        return results

    def get_patient_records(
        self, patient_id: str, doctor_id: str, doctor_name: str
    ) -> dict:
        """
        Access patient's healthcare records (consent-gated).

        Requires active 'healthcare_treatment' consent from the patient.
        Every attempt is audited.

        Returns:
            Dict with records if consent exists, or denial info

        Raises:
            ConsentRequiredError: No active consent for this patient
        """
        # Get patient
        patient = self.patients.find_one({"_id": patient_id}, {"user_id": 1})
        if not patient:
            self.audit_svc.log_event(
                actor_id=doctor_id,
                actor_role="doctor",
                action_type="read",
                resource_type="healthcare_records",
                patient_id=None,
                reason="Access denied. Patient not found.",
                severity="warning",
                details={"patient_id": patient_id, "doctor_name": doctor_name},
            )
            raise NotFoundError("Patient not found")

        # Check consent
        recipient_keys = doctor_recipient_keys(self.db, doctor_id)
        consent = self._chart_consent(patient_id, recipient_keys)

        chart_scope = self._chart_scope(consent)
        if not chart_scope:
            latest = consent or self.consent_svc.latest_inactive_consent(patient_id, "healthcare_treatment", recipient_keys)
            status = latest["status"] if latest else "absent"
            if consent:
                status = "scope_restricted"
                message = "The patient has not shared allergies or medical history for this chart."
            elif status == "expired":
                message = "Treatment consent has expired."
            else:
                message = "Active treatment consent is required to open this chart."
            # Audit the DENIED access
            self.audit_svc.log_event(
                actor_id=doctor_id,
                actor_role="doctor",
                action_type="read",
                resource_type="healthcare_records",
                patient_id=patient["user_id"],
                reason=f"Access denied. {message}",
                severity="warning",
                details={"patient_id": patient_id, "doctor_name": doctor_name, "consent_status": status,
                         "consent_id": latest["_id"] if latest else None},
            )
            raise ConsentRequiredError(message, consent_status=status)

        profile_fields = {}
        if "allergies" in chart_scope:
            profile_fields["allergies"] = 1
        if "medical_history" in chart_scope:
            profile_fields["blood_group"] = 1
        profile = self.enc.decrypt_document(self.patients.find_one({"_id": patient_id}, profile_fields))
        if profile is None:
            raise NotFoundError("Patient not found")

        if "allergies" in chart_scope:
            selected = self.consent_svc.selected_allergies(consent)
            current = profile.get("allergies")
            profile["allergies"] = [a for a in selected if isinstance(current, list) and a in current]

        records = []
        if "medical_history" in chart_scope:
            # New document fields must be explicitly assigned to a category before disclosure.
            record_fields = {key: 1 for key in (
                "record_type", "title", "description", "diagnosis_codes", "symptoms",
                "treatment_notes", "follow_up_date", "created_at", "version",
            )}
            cursor = self.records.find({"patient_id": patient_id, "redacted": False}, record_fields)
            records = [self.enc.decrypt_document(doc) for doc in cursor.sort("created_at", -1).limit(20)]

        disclosed = []
        if "allergies" in profile and profile["allergies"] is not None:
            disclosed.append("allergies")
        if records or profile.get("blood_group"):
            disclosed.append("medical_history")

        # Audit the GRANTED access
        self.audit_svc.log_event(
            actor_id=doctor_id,
            actor_role="doctor",
            action_type="read",
            resource_type="healthcare_records",
            patient_id=patient["user_id"],
            reason="Access GRANTED: Valid healthcare_treatment consent",
            details={
                "patient_id": patient_id,
                "doctor_name": doctor_name,
                "consent_id": consent["_id"],
                "records_accessed": len(records),
                "data_categories": disclosed,
            },
        )

        # Log data access for patient timeline
        self.audit_svc.log_data_access(
            patient_id=patient["user_id"],
            accessor_id=doctor_id,
            accessor_role="doctor",
            accessor_name=doctor_name,
            access_type="view",
            data_categories=disclosed,
            purpose="Healthcare treatment consultation",
            consent_id=consent["_id"],
        )

        return {
            "patient": profile,
            "consent": {
                "_id": consent["_id"],
                "consent_type": consent["consent_type"],
                "granted_at": consent["granted_at"],
                "expires_at": consent["expires_at"],
                "chart_scope": chart_scope,
            },
            "records": records,
            "access_status": "granted",
        }

    @staticmethod
    def _chart_scope(consent):
        # These are the two categories served by this chart endpoint.
        scope = consent.get("data_categories_in_scope") if consent else None
        return [key for key in ("allergies", "medical_history")
                if isinstance(scope, list) and key in scope]

    def _chart_consent(self, patient_id, recipient_keys):
        # A direct grant takes precedence over a matching hospital grant.
        for key in recipient_keys:
            grant = self.consent_svc.get_active_consent(patient_id, "healthcare_treatment", key)
            if grant:
                return grant
        return None
