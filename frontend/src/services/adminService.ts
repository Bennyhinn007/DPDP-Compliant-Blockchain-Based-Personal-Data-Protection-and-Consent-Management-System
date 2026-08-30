/**
 * Admin Governance API Service.
 *
 * Full user lifecycle management, DPDP operations, blockchain explorer,
 * compliance export, and system health monitoring.
 */

import api from "./api";

export interface GovernanceUser {
  id: string;
  full_name: string;
  email: string;
  role: string;
  status: string;
  last_login: string | null;
  failed_login_attempts: number;
  records_count: number;
  consents_count: number;
  risk_level: "low" | "medium" | "high";
  created_at: string;
}

export interface GovernanceMetrics {
  total_users: number;
  active_today: number;
  patients: number;
  doctors: number;
  admins: number;
  locked: number;
  dormant: number;
  never_logged_in: number;
  failed_login_attempts_users: number;
  patients_with_consent: number;
  patients_without_consent: number;
  doctor_access_events_7d: number;
}

export interface GovernanceData {
  metrics: GovernanceMetrics;
  users: GovernanceUser[];
  generated_at: string;
}

export interface UserDetail {
  user: {
    _id: string;
    full_name: string;
    email: string;
    role: string;
    status: string;
    last_login: string | null;
    failed_login_attempts: number;
    locked_until: string | null;
    mfa_enabled: boolean;
    webauthn_enrolled: boolean;
    created_at: string;
    updated_at: string;
  };
  patient: Record<string, unknown> | null;
  records: Record<string, unknown>[];
  consents: Record<string, unknown>[];
  audit_history: AuditEntry[];
}

export interface AuditEntry {
  _id: string;
  actor_id: string;
  actor_role: string;
  action_type: string;
  resource_type: string;
  resource_id: string;
  reason: string;
  severity: string;
  created_at: string;
  details?: Record<string, unknown>;
}

export interface BlockchainAnchor {
  _id: string;
  resource_type: string;
  resource_id: string;
  data_hash: string;
  transaction_hash: string | null;
  transaction_status: string;
  block_number: number | null;
  patient_id: string;
  anchor_type: string;
  created_at: string;
}

export interface ChameleonRequest {
  _id: string;
  resource_type: string;
  resource_id: string;
  patient_id: string;
  redaction_type: string;
  reason: string;
  requested_by: string;
  status: string;
  affected_fields: string[];
  created_at: string;
  authorized_at?: string;
  authorizer_id?: string;
  legal_basis?: string;
}

export interface SystemHealth {
  subsystems: Record<string, { status: string; description: string }>;
  checked_at: string;
}

export const adminService = {
  // ─── Governance Data ───────────────────────────────────────────
  async getGovernanceData(): Promise<GovernanceData> {
    const { data } = await api.get<{ governance: GovernanceData }>("/compliance/governance");
    return data.governance;
  },

  // ─── User Lifecycle Management ─────────────────────────────────
  async getUserDetail(userId: string): Promise<UserDetail> {
    const { data } = await api.get<UserDetail>(`/compliance/user/${userId}`);
    return data;
  },

  async lockUser(userId: string, reason: string, durationHours = 24): Promise<{ message: string }> {
    const { data } = await api.post(`/compliance/lock-user/${userId}`, {
      reason,
      duration_hours: durationHours,
    });
    return data;
  },

  async unlockUser(userId: string): Promise<{ message: string }> {
    const { data } = await api.post(`/compliance/unlock-user/${userId}`);
    return data;
  },

  async suspendUser(userId: string, reason: string): Promise<{ message: string }> {
    const { data } = await api.post(`/compliance/suspend-user/${userId}`, { reason });
    return data;
  },

  async activateUser(userId: string): Promise<{ message: string }> {
    const { data } = await api.post(`/compliance/activate-user/${userId}`);
    return data;
  },

  async resetMFA(userId: string): Promise<{ message: string }> {
    const { data } = await api.post(`/compliance/reset-mfa/${userId}`);
    return data;
  },

  async deleteUser(userId: string, reason: string): Promise<{ message: string }> {
    const { data } = await api.delete(`/compliance/delete-user/${userId}`, {
      data: { reason },
    });
    return data;
  },

  async getUserAudit(userId: string, skip = 0, limit = 50): Promise<{ audit_history: AuditEntry[]; count: number }> {
    const { data } = await api.get(`/compliance/user/${userId}/audit`, {
      params: { skip, limit },
    });
    return data;
  },

  async getUserConsents(userId: string): Promise<{ consents: Record<string, unknown>[]; count: number }> {
    const { data } = await api.get(`/compliance/user/${userId}/consents`);
    return data;
  },

  async getUserRecords(userId: string): Promise<{ records: Record<string, unknown>[]; count: number }> {
    const { data } = await api.get(`/compliance/user/${userId}/records`);
    return data;
  },

  // ─── DPDP Operations ───────────────────────────────────────────
  async getPendingRequests(): Promise<{
    pending_corrections: ChameleonRequest[];
    pending_erasures: ChameleonRequest[];
    executed_corrections: ChameleonRequest[];
    executed_erasures: ChameleonRequest[];
    totals: { pending: number; executed: number };
  }> {
    const { data } = await api.get("/compliance/operations/pending-requests");
    return data;
  },

  async getRequestDetail(requestId: string): Promise<{
    request: ChameleonRequest;
    blockchain_anchors: BlockchainAnchor[];
    version_history: Record<string, unknown>[];
    audit_trail: AuditEntry[];
  }> {
    const { data } = await api.get(`/compliance/operations/request/${requestId}`);
    return data;
  },

  // ─── Blockchain Explorer ───────────────────────────────────────
  async getBlockchainAnchors(search = "", skip = 0, limit = 50): Promise<{
    anchors: BlockchainAnchor[];
    total: number;
    skip: number;
    limit: number;
  }> {
    const { data } = await api.get("/compliance/blockchain/explorer", {
      params: { search, skip, limit },
    });
    return data;
  },

  async getAnchorDetail(anchorId: string): Promise<{
    anchor: BlockchainAnchor;
    record: Record<string, unknown> | null;
  }> {
    const { data } = await api.get(`/compliance/blockchain/anchor/${anchorId}`);
    return data;
  },

  // ─── System Health ─────────────────────────────────────────────
  async getSystemHealth(): Promise<SystemHealth> {
    const { data } = await api.get("/compliance/system-health");
    return data;
  },

  // ─── Compliance Export ─────────────────────────────────────────
  async exportComplianceJSON(): Promise<Record<string, unknown>> {
    const { data } = await api.get("/compliance/export/json");
    return data;
  },

  // ─── Audit Logs (All) ─────────────────────────────────────────
  async getAllAuditLogs(params: {
    skip?: number;
    limit?: number;
    action_type?: string;
    severity?: string;
    actor_id?: string;
  } = {}): Promise<{ logs: AuditEntry[]; total: number }> {
    const { data } = await api.get("/compliance/audit/all", { params });
    return data;
  },
};
