/**
 * Audit API Service.
 */

import api from "./api";
import type { AuditEvent } from "@/types";

export const auditService = {
  async getTimeline(actionType?: string, limit = 100): Promise<AuditEvent[]> {
    const params = actionType ? { action_type: actionType, limit } : { limit };
    const { data } = await api.get<{ timeline: AuditEvent[] }>("/audit/timeline", { params });
    return data.timeline;
  },

  async getAccessHistory(): Promise<{ access_history: unknown[]; summary: { total_access_events: number } }> {
    const { data } = await api.get("/audit/access-history");
    return data;
  },
};
