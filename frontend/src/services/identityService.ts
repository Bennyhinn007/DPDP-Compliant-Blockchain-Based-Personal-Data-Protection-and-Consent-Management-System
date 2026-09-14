/**
 * DID Identity API Service — SIH 26125 (ADDITIVE).
 *
 * Talks to the new /api/v1/did endpoints. Does not touch existing auth services.
 */

import api from "./api";
import type { LoginResponse } from "@/types";

export interface DidRecord {
  did: string;
  did_hash: string;
  pub_key_hash?: string;
  address: string;
  status: string;
  sih_role?: string | null;
  did_document?: unknown;
}

export interface DidChallenge {
  did: string;
  nonce: string;
  message: string;
  expires_at: string;
  exp: number;
}

export const identityService = {
  /** Register a DID for the current user (client sends its public key). */
  async createDid(publicKey: string): Promise<DidRecord> {
    const { data } = await api.post<DidRecord>("/did", { public_key: publicKey });
    return data;
  },

  /** Get the current user's DID (null if none). */
  async myDid(): Promise<DidRecord | null> {
    const { data } = await api.get<{ did: string | null } & Partial<DidRecord>>("/did/me");
    return data.did ? (data as DidRecord) : null;
  },

  /** Resolve a DID document. */
  async resolveDid(did: string): Promise<DidRecord & { verified: boolean }> {
    const { data } = await api.get<DidRecord & { verified: boolean }>(`/did/${encodeURIComponent(did)}`);
    return data;
  },

  /** Request a challenge nonce for DID login. */
  async challenge(did: string): Promise<DidChallenge> {
    const { data } = await api.post<DidChallenge>("/did/challenge", { did });
    return data;
  },

  /** Verify a signed challenge → issues the same JWT as password login. */
  async verify(did: string, nonce: string, signature: string): Promise<LoginResponse & { did: string }> {
    const { data } = await api.post<LoginResponse & { did: string }>("/did/verify", {
      did,
      nonce,
      signature,
    });
    return data;
  },
};
