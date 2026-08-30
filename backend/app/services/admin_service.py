"""
Admin Service — Identity & Access Governance.

Aggregates user identity data, access patterns, risk levels,
and healthcare relationships for the governance dashboard.
Provides full user lifecycle management: lock, unlock, suspend, activate, delete, reset MFA.
"""

from datetime import datetime, timezone, timedelta
from app.utils.helpers import utc_now
from app.services.encryption_service import get_encryption_service


class AdminService:
    """Provides user governance data aggregation and lifecycle management."""

    def __init__(self, db):
        self.db = db
        self.users = db["users"]
        self.patients = db["patients"]
        self.consents = db["consents"]
        self.records = db["healthcare_records"]
        self.audit_logs = db["audit_logs"]
        self.enc = get_encryption_service()

    # ─────────────────────────────────────────────────────────────────
    # USER LIFECYCLE MANAGEMENT
    # ─────────────────────────────────────────────────────────────────

    def get_user_detail(self, user_id: str) -> dict:
        """Get comprehensive user details including audit history and related data."""
        user = self.users.find_one({"_id": user_id})
        if not user:
            return None

        # Get patient profile if patient role
        patient = None
        records = []
        consents_list = []
        if user.get("role") == "patient":
            patient = self.patients.find_one({"user_id": user_id})
            if patient:
                records = list(self.records.find(
                    {"patient_id": patient["_id"]}
                ).sort("created_at", -1).limit(20))
                consents_list = list(self.consents.find(
                    {"patient_id": patient["_id"]}
                ).sort("created_at", -1))
                # Decrypt patient fields
                patient = self.enc.decrypt_document(patient)
                records = [self.enc.decrypt_document(r) for r in records]

        # Get audit history for this user
        audit_history = list(self.audit_logs.find(
            {"actor_id": user_id}
        ).sort("created_at", -1).limit(50))

        return {
            "user": {
                "_id": user["_id"],
                "full_name": user.get("full_name", "Unknown"),
                "email": user.get("email_encrypted", ""),
                "role": user.get("role", "unknown"),
                "status": self._user_status(user),
                "last_login": user.get("last_login"),
                "failed_login_attempts": user.get("failed_login_attempts", 0),
                "locked_until": user.get("locked_until"),
                "mfa_enabled": user.get("mfa_enabled", False),
                "webauthn_enrolled": user.get("webauthn_enrolled", False),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
            },
            "patient": patient,
            "records": records,
            "consents": consents_list,
            "audit_history": audit_history,
        }

    def lock_user(self, user_id: str, admin_id: str, reason: str = "Admin action", duration_hours: int = 24) -> dict:
        """Lock a user account."""
        user = self.users.find_one({"_id": user_id})
        if not user:
            return {"error": True, "message": "User not found"}

        locked_until = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat()
        self.users.update_one(
            {"_id": user_id},
            {"$set": {
                "locked_until": locked_until,
                "updated_at": utc_now(),
            }}
        )
        self._log_admin_action(admin_id, "ACCOUNT_LOCKED", "users", user_id, reason)
        return {"message": "Account locked", "locked_until": locked_until}

    def unlock_user(self, user_id: str, admin_id: str) -> dict:
        """Unlock a user account."""
        user = self.users.find_one({"_id": user_id})
        if not user:
            return {"error": True, "message": "User not found"}

        self.users.update_one(
            {"_id": user_id},
            {"$set": {
                "failed_login_attempts": 0,
                "locked_until": None,
                "updated_at": utc_now(),
            }}
        )
        self._log_admin_action(admin_id, "ACCOUNT_UNLOCKED", "users", user_id, "Admin manual unlock")
        return {"message": "Account unlocked"}

    def suspend_user(self, user_id: str, admin_id: str, reason: str = "Admin action") -> dict:
        """Suspend a user account (indefinite until reactivated)."""
        user = self.users.find_one({"_id": user_id})
        if not user:
            return {"error": True, "message": "User not found"}

        self.users.update_one(
            {"_id": user_id},
            {"$set": {
                "status": "suspended",
                "updated_at": utc_now(),
            }}
        )
        self._log_admin_action(admin_id, "ACCOUNT_SUSPENDED", "users", user_id, reason)
        return {"message": "Account suspended"}

    def activate_user(self, user_id: str, admin_id: str) -> dict:
        """Reactivate a suspended user account."""
        user = self.users.find_one({"_id": user_id})
        if not user:
            return {"error": True, "message": "User not found"}

        self.users.update_one(
            {"_id": user_id},
            {"$set": {
                "status": "active",
                "locked_until": None,
                "failed_login_attempts": 0,
                "updated_at": utc_now(),
            }}
        )
        self._log_admin_action(admin_id, "ACCOUNT_ACTIVATED", "users", user_id, "Admin reactivation")
        return {"message": "Account activated"}

    def reset_mfa(self, user_id: str, admin_id: str) -> dict:
        """Reset MFA for a user (remove TOTP secret and disable MFA)."""
        user = self.users.find_one({"_id": user_id})
        if not user:
            return {"error": True, "message": "User not found"}

        self.users.update_one(
            {"_id": user_id},
            {"$set": {
                "mfa_enabled": False,
                "mfa_secret": None,
                "updated_at": utc_now(),
            }}
        )
        self._log_admin_action(admin_id, "MFA_RESET", "users", user_id, "Admin MFA reset")
        return {"message": "MFA reset successfully"}

    def delete_user(self, user_id: str, admin_id: str, reason: str = "Admin action") -> dict:
        """
        Delete a user and all associated data.
        Archives user record before deletion for compliance.
        """
        user = self.users.find_one({"_id": user_id})
        if not user:
            return {"error": True, "message": "User not found"}

        # Prevent self-deletion
        if user_id == admin_id:
            return {"error": True, "message": "Cannot delete your own account"}

        # Archive before deletion
        archive = {
            "_id": f"deleted_{user_id}_{utc_now()}",
            "original_user_id": user_id,
            "role": user.get("role"),
            "deleted_by": admin_id,
            "deleted_at": utc_now(),
            "reason": reason,
        }
        self.db["version_history"].insert_one(archive)

        # Delete associated data for patient
        if user.get("role") == "patient":
            patient = self.patients.find_one({"user_id": user_id})
            if patient:
                # Mark records as redacted rather than deleting (DPDP compliance)
                self.records.update_many(
                    {"patient_id": patient["_id"]},
                    {"$set": {"redacted": True, "redacted_at": utc_now(), "redacted_by": admin_id}}
                )
                # Mark patient profile as redacted
                self.patients.update_one(
                    {"_id": patient["_id"]},
                    {"$set": {"redacted": True, "redacted_at": utc_now()}}
                )

        # Remove user document
        self.users.delete_one({"_id": user_id})

        self._log_admin_action(admin_id, "USER_DELETED", "users", user_id, reason, severity="critical")
        return {"message": "User deleted successfully"}

    def get_user_audit_history(self, user_id: str, skip: int = 0, limit: int = 50) -> list:
        """Get audit history for a specific user."""
        return list(self.audit_logs.find(
            {"$or": [{"actor_id": user_id}, {"resource_id": user_id}]}
        ).sort("created_at", -1).skip(skip).limit(limit))

    def get_user_consents(self, user_id: str) -> list:
        """Get all consents for a user (via patient profile)."""
        patient = self.patients.find_one({"user_id": user_id})
        if not patient:
            return []
        return list(self.consents.find({"patient_id": patient["_id"]}).sort("created_at", -1))

    def get_user_records(self, user_id: str) -> list:
        """Get all healthcare records for a user (via patient profile)."""
        patient = self.patients.find_one({"user_id": user_id})
        if not patient:
            return []
        records = list(self.records.find({"patient_id": patient["_id"]}).sort("created_at", -1))
        return [self.enc.decrypt_document(r) for r in records]

    def _log_admin_action(self, admin_id: str, action: str, resource_type: str,
                          resource_id: str, reason: str, severity: str = "warning"):
        """Create audit log entry for admin action."""
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log_event(
            actor_id=admin_id,
            actor_role="admin",
            action_type="update" if "UNLOCK" in action or "ACTIVATE" in action else "delete" if "DELETE" in action else "update",
            resource_type=resource_type,
            resource_id=resource_id,
            reason=f"{action}: {reason}",
            severity=severity,
        )

    def get_governance_data(self) -> dict:
        """
        Aggregate full governance dataset for the Identity Center.

        Returns user directory, lifecycle metrics, access security,
        and healthcare relationships.
        """
        now = datetime.now(timezone.utc)
        day_ago = (now - timedelta(hours=24)).isoformat()
        thirty_days_ago = (now - timedelta(days=30)).isoformat()

        # Lifecycle metrics
        total = self.users.count_documents({})
        active_today = self.users.count_documents({"last_login": {"$gte": day_ago}})
        patients_count = self.users.count_documents({"role": "patient"})
        doctors_count = self.users.count_documents({"role": "doctor"})
        admins_count = self.users.count_documents({"role": {"$in": ["admin", "dpo"]}})
        locked = self.users.count_documents({"locked_until": {"$ne": None}})
        dormant = self.users.count_documents({
            "last_login": {"$lt": thirty_days_ago, "$ne": None}
        })
        never_logged = self.users.count_documents({"last_login": None})

        # Access security
        failed_attempts_users = self.users.count_documents({"failed_login_attempts": {"$gt": 0}})

        # Healthcare relationships
        patients_with_consent = len(self.consents.distinct("patient_id", {"status": "active"}))
        total_patients_profiles = self.patients.count_documents({"redacted": False})
        patients_without_consent = max(0, total_patients_profiles - patients_with_consent)

        # Doctor access events (last 7 days)
        week_ago = (now - timedelta(days=7)).isoformat()
        doctor_access_events = self.audit_logs.count_documents({
            "actor_role": "doctor",
            "action_type": "read",
            "created_at": {"$gte": week_ago},
        })

        # User directory
        users_list = self._build_user_directory()

        return {
            "metrics": {
                "total_users": total,
                "active_today": active_today,
                "patients": patients_count,
                "doctors": doctors_count,
                "admins": admins_count,
                "locked": locked,
                "dormant": dormant,
                "never_logged_in": never_logged,
                "failed_login_attempts_users": failed_attempts_users,
                "patients_with_consent": patients_with_consent,
                "patients_without_consent": patients_without_consent,
                "doctor_access_events_7d": doctor_access_events,
            },
            "users": users_list,
            "generated_at": utc_now(),
        }

    def _build_user_directory(self) -> list:
        """Build user directory with risk levels and activity counts."""
        users_raw = list(self.users.find().sort("created_at", -1).limit(50))
        directory = []

        for u in users_raw:
            user_id = u["_id"]

            # Get record/consent counts for patients
            records_count = 0
            consents_count = 0
            if u.get("role") == "patient":
                patient = self.patients.find_one({"user_id": user_id})
                if patient:
                    records_count = self.records.count_documents({"patient_id": patient["_id"]})
                    consents_count = self.consents.count_documents({
                        "patient_id": patient["_id"], "status": "active"
                    })

            # Compute risk level
            risk = self._compute_risk(u, consents_count)

            # Decrypt name
            full_name = u.get("full_name", "Unknown")

            directory.append({
                "id": user_id,
                "full_name": full_name,
                "email": u.get("email_encrypted", ""),
                "role": u.get("role", "unknown"),
                "status": self._user_status(u),
                "last_login": u.get("last_login"),
                "failed_login_attempts": u.get("failed_login_attempts", 0),
                "records_count": records_count,
                "consents_count": consents_count,
                "risk_level": risk,
                "created_at": u.get("created_at"),
            })

        return directory

    def _compute_risk(self, user: dict, consents_count: int) -> str:
        """Compute identity risk level based on user behavior."""
        score = 0

        # Failed logins
        failures = user.get("failed_login_attempts", 0)
        if failures >= 3:
            score += 3
        elif failures > 0:
            score += 1

        # Locked account
        if user.get("locked_until"):
            score += 2

        # Dormancy
        last_login = user.get("last_login")
        if last_login:
            try:
                login_dt = datetime.fromisoformat(last_login)
                days_inactive = (datetime.now(timezone.utc) - login_dt).days
                if days_inactive > 30:
                    score += 2
                elif days_inactive > 14:
                    score += 1
            except (ValueError, TypeError):
                pass
        elif user.get("role") == "patient":
            score += 1  # Never logged in

        # Missing consent (patients only)
        if user.get("role") == "patient" and consents_count == 0:
            score += 2

        if score >= 4:
            return "high"
        elif score >= 2:
            return "medium"
        return "low"

    @staticmethod
    def _user_status(user: dict) -> str:
        """Determine display status."""
        if user.get("locked_until"):
            return "locked"
        if user.get("status") == "suspended":
            return "suspended"
        return "active"
