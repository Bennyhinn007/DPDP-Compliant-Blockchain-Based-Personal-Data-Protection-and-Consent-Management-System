/**
 * Patient + Healthcare Record API Service.
 */

import api from "./api";
import type { Patient, HealthcareRecord, RecordLifecycle } from "@/types";

export const patientService = {
  async getProfile(): Promise<Patient> {
    const { data } = await api.get<{ patient: Patient }>("/patients/me");
    return data.patient;
  },

  async updateProfile(updates: Partial<Patient>): Promise<Patient> {
    const { data } = await api.put<{ patient: Patient }>("/patients/me", updates);
    return data.patient;
  },

  async listRecords(): Promise<HealthcareRecord[]> {
    const { data } = await api.get<{ records: HealthcareRecord[] }>("/patients/me/records");
    return data.records;
  },

  async correctRecord(recordId: string, corrections: Record<string, unknown>, reason: string) {
    const { data } = await api.post(`/patients/me/records/${recordId}/correct`, {
      corrections,
      reason,
    });
    return data;
  },

  async eraseRecord(recordId: string, fieldsToErase: string[], reason: string) {
    const { data } = await api.post(`/patients/me/records/${recordId}/erase`, {
      fields_to_erase: fieldsToErase,
      reason,
    });
    return data;
  },

  async getRecordLifecycle(recordId: string): Promise<RecordLifecycle> {
    const { data } = await api.get<{ lifecycle: RecordLifecycle }>(
      `/patients/me/records/${recordId}/lifecycle`
    );
    return data.lifecycle;
  },
};
