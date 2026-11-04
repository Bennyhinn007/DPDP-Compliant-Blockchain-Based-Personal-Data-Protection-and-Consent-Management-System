/**
 * Biometric (fingerprint) API Service - admin enroll / verify / remove.
 *
 * Matching happens in the browser (SecuGen local service); the server trusts the
 * reported score (prototype limitation).
 */
import { isAxiosError } from "axios";
import api from "./api";

export interface BiometricStatus {
  enrolled: boolean;
  provider?: string;
  quality?: number;
  enrolled_at?: string;
}

export interface BiometricTemplate {
  template: string;
  provider: string;
}

export interface BiometricVerifyResult {
  verified: boolean;
  physical_presence_expires_at?: string;
}

/** True when the API refused because a recent physical-presence proof is missing. */
export function presenceRequired(err: unknown): boolean {
  return (
    isAxiosError(err) &&
    err.response?.status === 403 &&
    !!(err.response.data as { requires_physical_verification?: boolean } | undefined)
      ?.requires_physical_verification
  );
}

export const biometricService = {
  async status(): Promise<BiometricStatus> {
    const { data } = await api.get<BiometricStatus>("/biometric/status");
    return data;
  },
  async enroll(template: string, provider: string, quality: number): Promise<BiometricStatus> {
    const { data } = await api.post<BiometricStatus>("/biometric/enroll", { template, provider, quality });
    return data;
  },
  async getTemplate(): Promise<BiometricTemplate> {
    const { data } = await api.get<BiometricTemplate>("/biometric/template");
    return data;
  },
  async verify(score: number, provider: string): Promise<BiometricVerifyResult> {
    const { data } = await api.post<BiometricVerifyResult>("/biometric/verify", { score, provider });
    return data;
  },
  async remove(): Promise<{ removed: boolean }> {
    const { data } = await api.delete<{ removed: boolean }>("/biometric/enroll");
    return data;
  },
};
