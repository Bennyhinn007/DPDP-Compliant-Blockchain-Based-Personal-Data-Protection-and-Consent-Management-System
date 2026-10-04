/**
 * Doctor API Service.
 */

import api from "./api";

export interface PatientSearchResult {
  _id: string;
  user_id: string;
  full_name: string;
  has_treatment_consent: boolean;
}

export interface PatientAccessResult {
  patient: { _id: string; full_name: string; blood_group: string; allergies: string[] };
  consent: { _id: string; consent_type: string; granted_at: string; expires_at: string };
  records: Array<{
    _id: string; title: string; record_type: string; description: string;
    diagnosis_codes: string[]; symptoms: string[]; treatment_notes: string;
    created_at: string; version: number;
  }>;
  access_status: string;
}

export interface AccessDeniedResult {
  error: boolean;
  access_status: string;
  message: string;
  reason: string;
  patient_id: string;
  required_consent: string;
}

export interface CreateRecordInput {
  record_type: string;
  title: string;
  description: string;
  diagnosis_codes?: string[];
  symptoms?: string[];
  treatment_notes?: string;
}

export interface CreatedRecord {
  _id: string;
  title: string;
  record_type: string;
  verification_hash: string | null;
  blockchain_tx_ref: string | null;
  blockchain_anchor_id: string | null;
  created_at: string;
}

export const doctorService = {
  async searchPatients(query: string): Promise<PatientSearchResult[]> {
    const { data } = await api.get<{ patients: PatientSearchResult[] }>(
      "/doctors/patients/search",
      { params: { q: query } }
    );
    return data.patients;
  },

  async getPatientRecords(patientId: string): Promise<PatientAccessResult> {
    const { data } = await api.get<PatientAccessResult>(
      `/doctors/patients/${patientId}/records`
    );
    return data;
  },

  /**
   * Provider (doctor) creates a healthcare record for a patient at point of care.
   * Reuses the existing POST /patients/:id/records endpoint — same encryption,
   * blockchain anchoring, and audit as all other record creation.
   */
  async createRecord(patientId: string, input: CreateRecordInput): Promise<CreatedRecord> {
    const { data } = await api.post<{ record: CreatedRecord }>(
      `/patients/${patientId}/records`,
      input
    );
    return data.record;
  },
};
