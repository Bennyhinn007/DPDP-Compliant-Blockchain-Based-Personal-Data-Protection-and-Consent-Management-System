"""
Asset & NFT Service — SIH 26125 Phase 3 (ADDITIVE).

Manages DIGITAL / ORGANIZATIONAL assets (e.g. medical device certificate,
software license) as ERC-721 NFTs linked to DIDs. Healthcare records are NOT
assets here and are never minted — they remain encrypted off-chain.

Off-chain (MongoDB, Fernet-encrypted): asset metadata (name/description/spec/document).
On-chain (AssetNFT): tokenId, ownerDidHash, metadataHash (keccak256), assetType, status.

metadataHash derivation (matches the Solidity/data_model spec):
    keccak256( utf8( json.dumps(plaintext_metadata, sort_keys=True, separators=(",",":")) ) )
    -> 0x-prefixed lowercase hex (bytes32). Computed BEFORE encryption.

All chain interaction is best-effort via ContractService; writes fail closed at
the API layer when the chain is unavailable.
"""

from __future__ import annotations

import json
from typing import Optional

from eth_utils import keccak

from app.utils.helpers import generate_uuid, utc_now
from app.services.encryption_service import get_encryption_service


# Demo asset types (synthetic). Index maps to the uint8 assetType on-chain.
ASSET_TYPES = [
    "medical_device",
    "device_certificate",
    "software_license",
    "digital_certificate",
    "authorized_document",
    "equipment_ownership",
    "maintenance_certificate",
]

# Fields of an asset that hold sensitive/descriptive content (encrypted at rest).
ASSET_SENSITIVE_FIELDS = ("name", "description", "spec", "document")

# No-PHI guard: metadata keys that indicate a healthcare record / patient PHI.
# Assets are organizational/digital items (devices, licenses, certificates) — a
# healthcare record must NEVER be turned into an asset/NFT (governing rule:
# "records are never NFTs; no PHI on-chain"). Registration is rejected if any of
# these keys appear, so PHI can never reach the (hashed) on-chain path.
PHI_FORBIDDEN_KEYS = frozenset({
    "patient_id", "patient_name", "mrn", "medical_record_id", "medical_record",
    "diagnosis", "diagnoses", "prescription", "prescriptions", "medication",
    "medications", "lab_result", "lab_results", "clinical_notes", "clinical_note",
    "symptoms", "treatment", "treatments", "allergy", "allergies", "vitals",
    "blood_group", "phi", "healthcare_record", "health_record", "record_id",
    "aadhaar", "ssn", "dob", "date_of_birth",
})


class PHINotAllowedError(ValueError):
    """Raised when asset metadata appears to contain healthcare PHI."""


class AssetNFTService:
    """Registers assets, mints/assigns/transfers NFTs, verifies ownership."""

    def __init__(self, db, contract_service=None):
        self.db = db
        self.assets = db["assets"]
        self.nft_tokens = db["nft_tokens"]
        self.enc = get_encryption_service()
        self.cs = contract_service  # ContractService or None

    # ── metadata hashing ────────────────────────────────────────────────

    @staticmethod
    def compute_metadata_hash(metadata: dict) -> str:
        """keccak256 of canonical JSON of the PLAINTEXT metadata -> 0x-hex bytes32."""
        canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return "0x" + keccak(canonical.encode("utf-8")).hex()

    def asset_type_index(self, asset_type: str) -> int:
        try:
            return ASSET_TYPES.index(asset_type)
        except ValueError:
            return len(ASSET_TYPES)  # "other"

    # ── asset registration (encrypted off-chain) ───────────────────────

    @staticmethod
    def assert_no_phi(metadata: dict) -> None:
        """
        Guard against putting healthcare PHI into an asset. Raises PHINotAllowedError
        if any metadata key (case-insensitively) matches a known PHI/record key.
        Enforces "records are never NFTs; no PHI on-chain".
        """
        if not isinstance(metadata, dict):
            return
        for key in metadata.keys():
            if str(key).strip().lower() in PHI_FORBIDDEN_KEYS:
                raise PHINotAllowedError(
                    f"Metadata field '{key}' looks like healthcare PHI. Assets are for "
                    "organizational/digital items only — healthcare records are never NFTs."
                )

    def register_asset(self, created_by: str, asset_type: str, metadata: dict) -> dict:
        """
        Store an asset's encrypted metadata off-chain + its keccak256 metadata hash.
        Does NOT mint — minting is a separate admin action.
        """
        # No-PHI guard (governing rule): reject healthcare-record-shaped metadata.
        self.assert_no_phi(metadata)

        asset_id = generate_uuid()
        now = utc_now()

        # Hash the PLAINTEXT canonical metadata before encryption.
        metadata_hash = self.compute_metadata_hash(metadata)

        doc = {
            "_id": asset_id,
            "asset_type": asset_type,
            "asset_type_index": self.asset_type_index(asset_type),
            "metadata_hash": metadata_hash,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
        # Encrypt sensitive metadata fields (reuse existing EncryptionService).
        for field in ASSET_SENSITIVE_FIELDS:
            if field in metadata and metadata[field] is not None:
                doc[field] = self.enc.encrypt_field(metadata[field])

        self.assets.insert_one(doc)
        return self._decrypt_asset(doc)

    def list_assets(self) -> list:
        return [self._decrypt_asset(a) for a in self.assets.find().sort("created_at", -1)]

    def get_asset(self, asset_id: str) -> Optional[dict]:
        doc = self.assets.find_one({"_id": asset_id})
        return self._decrypt_asset(doc) if doc else None

    def _decrypt_asset(self, doc: dict) -> dict:
        out = dict(doc)
        for field in ASSET_SENSITIVE_FIELDS:
            if field in out and out[field] is not None:
                out[field] = self.enc.decrypt_field(out[field])
        return out

    # ── NFT lifecycle (on-chain via ContractService) ────────────────────

    def mint(self, asset_id: str, owner_did: str) -> dict:
        """
        Mint an NFT for a registered asset to a DID. Requires chain availability
        (caller enforces fail-closed). Returns {ok, token_id, tx_hash} or {ok:False}.
        """
        asset = self.assets.find_one({"_id": asset_id})
        if not asset:
            return {"ok": False, "reason": "asset_not_found"}
        if self.cs is None or not self.cs.nft_available:
            return {"ok": False, "reason": "chain_or_contracts_unavailable"}

        result = self.cs.mint_asset(owner_did, asset["metadata_hash"], asset.get("asset_type_index", 0))
        if not result.get("ok"):
            return result

        token_doc = {
            "_id": generate_uuid(),
            "token_id": result.get("token_id"),
            "owner_did": owner_did,
            "asset_id": asset_id,
            "metadata_hash": asset["metadata_hash"],
            "mint_tx": result.get("tx_hash"),
            "status": "active",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        self.nft_tokens.insert_one(token_doc)
        return {"ok": True, "token_id": result.get("token_id"), "tx_hash": result.get("tx_hash")}

    def assign(self, token_id: int, to_did: str) -> dict:
        if self.cs is None or not self.cs.nft_available:
            return {"ok": False, "reason": "chain_or_contracts_unavailable"}
        result = self.cs.assign_asset(token_id, to_did)
        if result.get("ok"):
            self.nft_tokens.update_one(
                {"token_id": token_id},
                {"$set": {"owner_did": to_did, "updated_at": utc_now()}},
            )
        return result

    def transfer(self, token_id: int, to_did: str) -> dict:
        if self.cs is None or not self.cs.nft_available:
            return {"ok": False, "reason": "chain_or_contracts_unavailable"}
        result = self.cs.transfer_asset(token_id, to_did)
        if result.get("ok"):
            self.nft_tokens.update_one(
                {"token_id": token_id},
                {"$set": {"owner_did": to_did, "updated_at": utc_now()}},
            )
        return result

    def list_nfts(self, owner_did: str = None) -> list:
        query = {"owner_did": owner_did} if owner_did else {}
        return list(self.nft_tokens.find(query).sort("created_at", -1))

    def verify_ownership(self, token_id: int) -> dict:
        """
        Verify a token: on-chain ownerDidHash + metadata-hash match between the
        on-chain value and keccak256 of the (decrypted) off-chain metadata.
        Read-only: degrades gracefully when chain is unavailable.
        """
        token = self.nft_tokens.find_one({"token_id": token_id})
        result = {
            "token_id": token_id,
            "found": bool(token),
            "chain_available": False,
        }
        if not token:
            return result

        result["owner_did"] = token.get("owner_did")
        result["asset_id"] = token.get("asset_id")

        # Recompute metadata hash from the decrypted off-chain asset.
        asset = self.get_asset(token["asset_id"]) if token.get("asset_id") else None
        off_chain_hash = token.get("metadata_hash")
        result["off_chain_metadata_hash"] = off_chain_hash

        if self.cs is not None and self.cs.nft_available:
            result["chain_available"] = True
            on_chain_hash = self.cs.asset_metadata_hash(token_id)
            on_chain_owner = self.cs.asset_owner_did_hash(token_id)
            status = self.cs.asset_status(token_id)
            result["on_chain_metadata_hash"] = on_chain_hash
            result["on_chain_owner_did_hash"] = on_chain_owner
            result["on_chain_status"] = status
            # Compare on-chain metadata hash with off-chain stored hash.
            result["metadata_hash_match"] = (
                on_chain_hash is not None
                and off_chain_hash is not None
                and on_chain_hash.lower() == off_chain_hash.lower()
            )
            # Compare on-chain owner did-hash with keccak(owner_did) from cache.
            if on_chain_owner and token.get("owner_did"):
                expected = "0x" + keccak(token["owner_did"].encode("utf-8")).hex()
                result["owner_match"] = on_chain_owner.lower() == expected.lower()
            result["verified"] = bool(result.get("metadata_hash_match")) and bool(result.get("owner_match", False))
        else:
            result["verified"] = None  # cannot verify without chain
        return result
