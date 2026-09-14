/**
 * Digital Asset + NFT + Roles API Service — SIH 26125 Phase 3 (ADDITIVE).
 */

import api from "./api";

export interface DigitalAsset {
  _id: string;
  asset_type: string;
  asset_type_index?: number;
  metadata_hash: string;
  name?: string;
  description?: string;
  spec?: string;
  document?: string;
  created_by?: string;
  created_at?: string;
}

export interface NftToken {
  _id: string;
  token_id: number | null;
  owner_did: string;
  asset_id: string;
  metadata_hash: string;
  mint_tx?: string;
  status: string;
  created_at?: string;
}

export interface NftVerification {
  token_id: number;
  found: boolean;
  chain_available: boolean;
  owner_did?: string;
  asset_id?: string;
  off_chain_metadata_hash?: string;
  on_chain_metadata_hash?: string;
  on_chain_owner_did_hash?: string;
  on_chain_status?: number;
  metadata_hash_match?: boolean;
  owner_match?: boolean;
  verified?: boolean | null;
}

export interface ChainEvent {
  _id: string;
  event_name: string;
  contract: string;
  tx_hash?: string;
  block_number?: number | null;
  args?: Record<string, unknown>;
  indexed_at?: string;
}

export const assetService = {
  async assetTypes(): Promise<string[]> {
    const { data } = await api.get<{ asset_types: string[] }>("/assets/types");
    return data.asset_types;
  },
  async registerAsset(assetType: string, metadata: Record<string, unknown>): Promise<DigitalAsset> {
    const { data } = await api.post<{ asset: DigitalAsset }>("/assets", { asset_type: assetType, metadata });
    return data.asset;
  },
  async listAssets(): Promise<DigitalAsset[]> {
    const { data } = await api.get<{ assets: DigitalAsset[] }>("/assets");
    return data.assets;
  },
  async mint(assetId: string, ownerDid: string): Promise<{ token_id: number; tx_hash: string }> {
    const { data } = await api.post("/nft/mint", { asset_id: assetId, owner_did: ownerDid });
    return data;
  },
  async assign(tokenId: number, toDid: string) {
    const { data } = await api.post(`/nft/${tokenId}/assign`, { to_did: toDid });
    return data;
  },
  async transfer(tokenId: number, toDid: string) {
    const { data } = await api.post(`/nft/${tokenId}/transfer`, { to_did: toDid });
    return data;
  },
  async verify(tokenId: number): Promise<NftVerification> {
    const { data } = await api.get<NftVerification>(`/nft/${tokenId}/verify`);
    return data;
  },
  async listNfts(ownerDid?: string): Promise<NftToken[]> {
    const { data } = await api.get<{ nfts: NftToken[] }>("/nft", {
      params: ownerDid ? { owner_did: ownerDid } : {},
    });
    return data.nfts;
  },
  async chainEvents(limit = 100): Promise<ChainEvent[]> {
    const { data } = await api.get<{ events: ChainEvent[] }>("/blockchain/events", { params: { limit } });
    return data.events;
  },
};

// Roles (SIH RBAC)
export interface RoleMatrix {
  roles: string[];
  matrix: Record<string, Record<string, boolean>>;
  chain_available: boolean;
}

export const rolesService = {
  async matrix(): Promise<RoleMatrix> {
    const { data } = await api.get<RoleMatrix>("/roles/matrix");
    return data;
  },
  async grant(did: string, role: string) {
    const { data } = await api.post("/roles/grant", { did, role });
    return data;
  },
  async revoke(did: string, role: string) {
    const { data } = await api.post("/roles/revoke", { did, role });
    return data;
  },
  async check(did: string, role: string) {
    const { data } = await api.get("/roles/check", { params: { did, role } });
    return data;
  },
};
