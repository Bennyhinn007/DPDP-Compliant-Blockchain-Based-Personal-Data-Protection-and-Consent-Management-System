/**
 * Integrity Verification API Service.
 */

import api from "./api";
import type { VerificationResult } from "@/types";

export const integrityService = {
  async verifyRecord(recordId: string): Promise<VerificationResult> {
    const { data } = await api.get<{ verification: VerificationResult }>(
      `/integrity/record/${recordId}`
    );
    return data.verification;
  },

  async getStatus(): Promise<{
    connected: boolean;
    block_number: number | null;
    total_anchors: number;
  }> {
    const { data } = await api.get<{
      blockchain: { connected: boolean; block_number: number | null; total_anchors: number };
    }>("/integrity/status");
    return data.blockchain;
  },

  // Live REAL chameleon-hash collision demo
  async chameleonCollisionDemo(original: string, modified: string): Promise<ChameleonDemoResult> {
    const { data } = await api.post<ChameleonDemoResult>("/blockchain/chameleon/demo", {
      original,
      modified,
    });
    return data;
  },

  // Live tamper-attempt demo: unauthorized tamper vs lawful chameleon correction
  async tamperDemo(original: string, modified: string): Promise<TamperDemoResult> {
    const { data } = await api.post<TamperDemoResult>("/integrity/tamper-demo", {
      original,
      modified,
    });
    return data;
  },
};

export interface TamperDemoResult {
  original_content: string;
  modified_content: string;
  content_changed: boolean;
  tamper: {
    scenario: string;
    title: string;
    anchor_hash: string;
    current_hash: string;
    hashes_match: boolean;
    status: "INTEGRITY_VIOLATION";
    message: string;
  };
  lawful: {
    scenario: string;
    title: string;
    chameleon_hash: string;
    original_r: string;
    collision_r: string;
    public_key_y: string;
    modulus_bits: number;
    hash_identical_after_edit: boolean;
    status: "VERIFIED_MODIFIED" | "INTEGRITY_VIOLATION";
    message: string;
    formula: string;
  };
}

export interface ChameleonDemoResult {
  original_content: string;
  modified_content: string;
  content_changed: boolean;
  hash_identical: boolean;
  proof: {
    scheme: string;
    chameleon_hash: string;
    original_r: string;
    collision_r: string;
    public_key_y: string;
    modulus_bits: number;
    verified: boolean;
  };
}
