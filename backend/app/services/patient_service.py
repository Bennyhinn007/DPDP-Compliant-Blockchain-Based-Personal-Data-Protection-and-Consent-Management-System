"""
Patient Service.

Handles patient profile creation and retrieval.
Patients are created automatically during registration.
All sensitive fields are encrypted before storage and decrypted on retrieval.
"""

from app.utils.helpers import generate_uuid, utc_now
from app.utils.errors import NotFoundError, ValidationError
from app.services.encryption_service import get_encryption_service


class PatientService:
    """Manages patient profile operations."""

    def __init__(self, db):
        self.db = db
        self.patients = db["patients"]
        self.enc = get_encryption_service()

    def create_patient_profile(self, user_id: str, full_name: str) -> dict:
        """
        Create a patient profile linked to a user account.
        Sensitive fields encrypted before MongoDB insertion.
        Returns decrypted document for API response.
        """
        existing = self.patients.find_one({"user_id": user_id})
        if existing:
            return self.enc.decrypt_document(existing)

        patient_id = generate_uuid()
        now = utc_now()

        patient_doc = {
            "_id": patient_id,
            "user_id": user_id,
            "full_name": full_name,
            "phone_number": None,
            "address": None,
            "identity_type": None,
            "identity_number": None,
            "blood_group": None,
            "allergies": [],
            "chronic_conditions": [],
            "emergency_contact": None,
            "data_categories_stored": ["personal_info"],
            "version": 1,
            "redacted": False,
            "redacted_at": None,
            "redacted_by": None,
            "redaction_reason": None,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id,
        }

        # Encrypt before storage
        encrypted_doc = self.enc.encrypt_document(patient_doc)
        self.patients.insert_one(encrypted_doc)

        # Return plaintext for API
        return patient_doc

    def get_patient_by_user_id(self, user_id: str) -> dict:
        """Get patient profile by user account ID. Auto-creates if missing. Returns decrypted."""
        patient = self.patients.find_one({"user_id": user_id})
        if not patient:
            from app.extensions import get_db
            db = get_db()
            user = db["users"].find_one({"_id": user_id})
            if user and user.get("role") == "patient":
                return self.create_patient_profile(user_id, user.get("full_name", ""))
            else:
                raise NotFoundError("Patient profile not found")
        return self.enc.decrypt_document(patient)

    def get_patient_by_id(self, patient_id: str) -> dict:
        """Get patient profile by patient ID. Returns decrypted."""
        patient = self.patients.find_one({"_id": patient_id})
        if not patient:
            raise NotFoundError("Patient not found")
        return self.enc.decrypt_document(patient)

    def update_patient_profile(self, patient_id: str, user_id: str, updates: dict) -> dict:
        """
        Update patient profile fields.
        Encrypts updated sensitive fields before storage.
        """
        patient = self.patients.find_one({"_id": patient_id})
        if not patient:
            raise NotFoundError("Patient not found")

        allowed_fields = {
            "full_name", "phone_number", "address", "identity_type",
            "identity_number", "blood_group", "allergies",
            "chronic_conditions", "emergency_contact",
        }

        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        if "allergies" in filtered_updates:
            allergies = filtered_updates["allergies"]
            if not isinstance(allergies, list) or any(not isinstance(a, str) or not a.strip() for a in allergies):
                raise ValidationError("Enter allergies as a list of names.")
            filtered_updates["allergies"] = list(dict.fromkeys(a.strip() for a in allergies))
        if not filtered_updates:
            raise ValidationError("No valid fields to update")

        filtered_updates["updated_at"] = utc_now()
        filtered_updates["updated_by"] = user_id
        filtered_updates["version"] = patient.get("version", 1) + 1

        # Encrypt sensitive fields in the update
        encrypted_updates = self.enc.encrypt_document(filtered_updates)

        self.patients.update_one(
            {"_id": patient_id},
            {"$set": encrypted_updates}
        )

        updated = self.patients.find_one({"_id": patient_id})
        return self.enc.decrypt_document(updated)

    def list_all_patients(self, skip: int = 0, limit: int = 20) -> list:
        """List all patients (admin only). Returns decrypted."""
        cursor = self.patients.find({"redacted": False}).skip(skip).limit(limit).sort("created_at", -1)
        return [self.enc.decrypt_document(p) for p in cursor]

    def get_raw_patient(self, patient_id: str) -> dict:
        """Get raw encrypted document (for testing/verification only)."""
        return self.patients.find_one({"_id": patient_id})
