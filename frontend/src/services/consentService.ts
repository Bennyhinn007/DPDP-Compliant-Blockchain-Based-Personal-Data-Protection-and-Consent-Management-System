/**
 * Consent API Service.
 */

import api from "./api";
import type { Consent, ConsentType } from "@/types";

export type ScopeOptions = Record<ConsentType, string[]>;

export interface Hospital {
  id: string;
  name: string;
  hospital_grant: boolean;
  doctors: { id: string; name: string }[];
}

export type Recipient =
  | { kind: "hospital"; hospital_id: string }
  | { kind: "doctor"; hospital_id: string; doctor_id: string };

export const consentService = {
  async providers(): Promise<Hospital[]> {
    const { data } = await api.get<{ hospitals: Hospital[] }>("/consents/providers");
    return data.hospitals;
  },

  async scopeOptions(): Promise<ScopeOptions> {
    const { data } = await api.get<ScopeOptions>("/consents/scope-options");
    return data;
  },

  async list(): Promise<Consent[]> {
    const { data } = await api.get<{ consents: Consent[] }>("/consents/");
    return data.consents;
  },

  async grant(
    consentType: ConsentType,
    processingEntityName: string,
    expiryDays = 365,
    customScope: string[],
    recipient: Recipient | null,
    selectedAllergies: string[]
  ): Promise<Consent> {
    const { data } = await api.post<{ consent: Consent }>("/consents/grant", {
      consent_type: consentType,
      processing_entity_name: processingEntityName,
      expiry_days: expiryDays,
      custom_scope: customScope,
      recipient,
      selected_allergies: selectedAllergies,
    });
    return data.consent;
  },

  async modify(consentId: string, newScope: string[], reason: string, selectedAllergies: string[]): Promise<Consent> {
    const { data } = await api.put<{ consent: Consent }>(`/consents/${consentId}/modify`, {
      new_scope: newScope,
      selected_allergies: selectedAllergies,
      reason,
    });
    return data.consent;
  },

  async withdraw(consentId: string, reason: string): Promise<Consent> {
    const { data } = await api.post<{ consent: Consent }>(`/consents/${consentId}/withdraw`, {
      reason,
    });
    return data.consent;
  },
};
