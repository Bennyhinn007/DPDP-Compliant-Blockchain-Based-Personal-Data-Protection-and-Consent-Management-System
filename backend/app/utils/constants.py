"""
Application Constants.

Enums and constant values used across the application.
"""

from enum import Enum


class UserRole(str, Enum):
    """User roles in the system (existing healthcare roles — UNCHANGED)."""
    PATIENT = "patient"
    DOCTOR = "doctor"
    PHARMACY_STAFF = "pharmacy_staff"
    ADMIN = "admin"
    DPO = "dpo"


class SIHRole(str, Enum):
    """
    SIH 26125 blockchain/identity roles (ADDITIVE).

    These exist ALONGSIDE the existing healthcare UserRole values — they do NOT
    rename or replace them. Used by the DID/identity/asset layer and mirrored
    on-chain by PlatformAccessControl.
    """
    ADMIN = "admin"
    MANAGER = "manager"
    AUDITOR = "auditor"
    USER = "user"


# Advisory (non-authoritative) mapping from existing healthcare roles to SIH
# roles, for demo convenience only. This does NOT rename healthcare roles and is
# NOT the authority for on-chain access control (PlatformAccessControl is).
HEALTHCARE_TO_SIH_ROLE_ADVISORY = {
    UserRole.ADMIN.value: SIHRole.ADMIN.value,
    UserRole.DPO.value: SIHRole.AUDITOR.value,
    UserRole.DOCTOR.value: SIHRole.MANAGER.value,
    UserRole.PHARMACY_STAFF.value: SIHRole.USER.value,
    UserRole.PATIENT.value: SIHRole.USER.value,
}


class ConsentType(str, Enum):
    """Consent purpose types."""
    HEALTHCARE_TREATMENT = "healthcare_treatment"
    PHARMACY_ACCESS = "pharmacy_access"
    RESEARCH_ACCESS = "research_access"
    INSURANCE_ACCESS = "insurance_access"
    ANALYTICS_ACCESS = "analytics_access"
    MARKETING_ACCESS = "marketing_access"


class ConsentStatus(str, Enum):
    """Consent lifecycle states."""
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    MODIFIED = "modified"


class AuditActionType(str, Enum):
    """Audit log action categories."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    CONSENT_GRANT = "consent_grant"
    CONSENT_WITHDRAW = "consent_withdraw"
    CONSENT_MODIFY = "consent_modify"
    LOGIN = "login"
    LOGOUT = "logout"
    BREAK_GLASS = "break_glass"
    REDACTION = "redaction"
    VERIFICATION = "verification"
    EXPORT = "export"


class AuditSeverity(str, Enum):
    """Audit log severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DataCategory(str, Enum):
    """Patient data categories."""
    PERSONAL_INFO = "personal_info"
    CONTACT_INFO = "contact_info"
    IDENTITY_INFO = "identity_info"
    MEDICAL_HISTORY = "medical_history"
    ALLERGIES = "allergies"
    PRESCRIPTIONS = "prescriptions"
    LAB_REPORTS = "lab_reports"
    HEALTHCARE_RECORDS = "healthcare_records"


# Purpose Limitation Matrix: which categories each consent type allows
PURPOSE_LIMITATION_MATRIX = {
    ConsentType.HEALTHCARE_TREATMENT: [
        DataCategory.MEDICAL_HISTORY,
        DataCategory.ALLERGIES,
        DataCategory.PRESCRIPTIONS,
        DataCategory.LAB_REPORTS,
    ],
    ConsentType.PHARMACY_ACCESS: [
        DataCategory.PRESCRIPTIONS,
        DataCategory.ALLERGIES,
    ],
    ConsentType.RESEARCH_ACCESS: [
        DataCategory.MEDICAL_HISTORY,
        DataCategory.LAB_REPORTS,
    ],
    ConsentType.INSURANCE_ACCESS: [
        DataCategory.MEDICAL_HISTORY,
        DataCategory.PRESCRIPTIONS,
    ],
    ConsentType.ANALYTICS_ACCESS: [],  # Aggregated only
    ConsentType.MARKETING_ACCESS: [
        DataCategory.CONTACT_INFO,
    ],
}
