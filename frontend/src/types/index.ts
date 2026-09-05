/**
 * Shared TypeScript type definitions.
 */

export type UserRole = "patient" | "doctor" | "pharmacy_staff" | "admin" | "dpo";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  full_name: string;
  status: string;
  mfa_enabled: boolean;
  last_login: string | null;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface ApiError {
  error: boolean;
  message: string;
  status_code: number;
  details?: Record<string, string>;
}

export interface Patient {
  _id: string;
  user_id: string;
  full_name: string;
  phone_number: string | null;
  address: string | null;
  identity_type: string | null;
  identity_number: string | null;
  blood_group: string | null;
  allergies: string[];
  chronic_conditions: string[];
  emergency_contact: string | null;
  version: number;
  redacted: boolean;
  created_at: string;
  updated_at: string;
}

export interface HealthcareRecord {
  _id: string;
  patient_id: string;
  record_type: string;
  title: string;
  description: string;
  diagnosis_codes: string[];
  symptoms: string[];
  treatment_notes: string;
  status: string;
  version: number;
  redacted: boolean;
  verification_hash: string | null;
  blockchain_tx_ref: string | null;
  blockchain_anchor_id: string | null;
  created_at: string;
  updated_at: string;
}

// ── Record Lifecycle Story ──────────────────────────────────────────
export interface ChameleonCollisionProof {
  chameleon_hash: string | null;
  original_r: string | null;
  collision_r: string | null;
  public_key_y: string | null;
  modulus_bits: number | null;
  verified: boolean | null;
}

export interface LifecycleEvent {
  type: "created" | "anchored" | "corrected" | "erased" | "audit";
  timestamp: string;
  title: string;
  description?: string;
  data_hash?: string;
  transaction_hash?: string | null;
  block_number?: number | null;
  anchor_type?: string;
  network?: string;
  explorer_url?: string | null;
  redaction_type?: "correction" | "erasure";
  legal_basis?: string | null;
  affected_fields?: string[];
  chameleon_proof_hash?: string | null;
  chameleon_collision?: ChameleonCollisionProof | null;
  severity?: "info" | "warning" | "critical";
}

export interface RecordLifecycle {
  record_id: string;
  record_type: string;
  redacted: boolean;
  current_status: string;
  anchor_count: number;
  redaction_count: number;
  events: LifecycleEvent[];
}

export type ConsentStatus = "active" | "withdrawn" | "expired" | "modified";
export type ConsentType =
  | "healthcare_treatment"
  | "pharmacy_access"
  | "research_access"
  | "insurance_access"
  | "analytics_access"
  | "marketing_access";

export interface Consent {
  _id: string;
  patient_id: string;
  user_id: string;
  consent_type: ConsentType;
  status: ConsentStatus;
  purpose_description: string;
  data_categories_in_scope: string[];
  processing_entity_name: string;
  granted_at: string;
  expires_at: string;
  withdrawn_at: string | null;
  version: number;
}

export interface AuditEvent {
  _id: string;
  actor_id: string;
  actor_role: string;
  action_type: string;
  action_category: string;
  severity: "info" | "warning" | "critical";
  resource_type: string;
  resource_id: string | null;
  patient_id: string | null;
  reason: string;
  created_at: string;
}

export interface VerificationResult {
  status: "VERIFIED" | "VERIFIED_MODIFIED" | "VERIFIED_REDACTED" | "INTEGRITY_VIOLATION" | "NO_ANCHOR";
  message: string;
  record_id: string;
  current_hash?: string;
  blockchain_hash?: string;
  transaction_hash?: string;
  block_number?: number;
  anchored_at?: string;
  verified_at: string;
  chameleon_proof?: string;
}

export interface ComplianceScore {
  overall_score: number;
  max_score: number;
  grade: string;
  breakdown: {
    encryption: number;
    consent_management: number;
    audit_logging: number;
    blockchain_anchoring: number;
    dpdp_rights: number;
  };
  evaluated_at: string;
}
