"""
Blockchain Anchoring Service.

Connects to Ganache (local Ethereum) and stores SHA-256 hashes of healthcare
records on-chain as transaction data. No smart contracts in MVP — uses raw
transactions with hash embedded in the data field.

On-chain storage:
- record_id (UUID)
- SHA-256 hash of the encrypted record
- timestamp

No healthcare data is ever stored on-chain.
"""

import hashlib
import json
from typing import Optional

from web3 import Web3
from web3.exceptions import TransactionNotFound

from app.utils.helpers import generate_uuid, utc_now


class BlockchainService:
    """Manages blockchain hash anchoring on Ganache."""

    def __init__(self, db, w3: Web3, config=None):
        self.db = db
        self.anchors = db["blockchain_anchors"]
        self.w3 = w3

        # Pull blockchain settings from the passed config, else the Flask app
        # config, else safe defaults (keeps every existing 2-arg caller working).
        self._network = "ganache"
        self._private_key = ""
        self._chain_id = None
        self._explorer_url = ""
        cfg = config
        if cfg is None:
            try:
                from flask import current_app
                cfg = current_app.config
            except Exception:
                cfg = None
        if cfg is not None:
            getter = cfg.get if hasattr(cfg, "get") else (lambda k, d=None: getattr(cfg, k, d))
            self._network = (getter("BLOCKCHAIN_NETWORK", "ganache") or "ganache").lower()
            self._private_key = getter("SEPOLIA_PRIVATE_KEY", "") or ""
            self._explorer_url = getter("BLOCKCHAIN_EXPLORER_URL", "") or ""
            self._chain_id = getter("SEPOLIA_CHAIN_ID", None) if self._network == "sepolia" else getter("GANACHE_CHAIN_ID", None)

        # Sender account. Ganache exposes unlocked accounts; Sepolia derives the
        # sender from the configured private key.
        self._account = None
        if w3:
            try:
                if self._network == "sepolia" and self._private_key:
                    self._account = w3.eth.account.from_key(self._private_key).address
                elif w3.is_connected():
                    self._account = w3.eth.accounts[0]
            except Exception:
                pass

    @property
    def is_connected(self) -> bool:
        """Check if Web3 is connected to Ganache."""
        try:
            return self.w3 is not None and self.w3.is_connected()
        except Exception:
            return False

    # ─────────────────────────────────────────────────────────────────
    # HASH COMPUTATION
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_record_hash(record: dict) -> str:
        """
        Compute SHA-256 hash of a record for blockchain anchoring.

        Uses the encrypted field values (as stored in MongoDB) to create
        the hash — this ensures the anchor verifies against the stored state.

        Excludes volatile metadata fields that change independently.
        """
        exclude = {
            "verification_hash", "blockchain_tx_ref", "blockchain_anchor_id",
        }
        hashable = {k: v for k, v in record.items() if k not in exclude}
        canonical = json.dumps(hashable, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # ─────────────────────────────────────────────────────────────────
    # ANCHOR CREATION
    # ─────────────────────────────────────────────────────────────────

    def anchor_record(
        self,
        resource_type: str,
        resource_id: str,
        data_hash: str,
        patient_id: str = None,
        anchor_type: str = "record_verification",
    ) -> dict:
        """
        Anchor a hash on the blockchain.

        Sends a transaction to Ganache with the hash as data payload.
        Stores the transaction reference in MongoDB blockchain_anchors collection.

        Args:
            resource_type: Collection name (e.g., "healthcare_records")
            resource_id: UUID of the source document
            data_hash: SHA-256 hex hash to anchor
            patient_id: UUID of related patient (optional)
            anchor_type: Type of anchor (record_verification, consent, audit)

        Returns:
            blockchain_anchor document with tx_hash and block_number
        """
        anchor_id = generate_uuid()
        now = utc_now()

        tx_hash = None
        block_number = None
        tx_status = "failed"

        if self.is_connected:
            try:
                tx_hash, block_number = self._send_hash_transaction(
                    resource_id, data_hash
                )
                tx_status = "success"
            except Exception as e:
                tx_status = f"failed: {str(e)[:100]}"

        anchor_doc = {
            "_id": anchor_id,
            "anchor_type": anchor_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "patient_id": patient_id,
            "data_hash": data_hash,
            "hash_algorithm": "sha256",
            "transaction_hash": tx_hash,
            "block_number": block_number,
            "transaction_status": tx_status,
            "network": self._network,
            "explorer_url": self.explorer_link(tx_hash),
            "created_at": now,
        }

        self.anchors.insert_one(anchor_doc)
        return anchor_doc

    def _send_hash_transaction(self, resource_id: str, data_hash: str) -> tuple:
        """
        Send a transaction containing the hash as its data payload.

        Two modes:
          - Ganache: accounts are unlocked, so we use eth.send_transaction.
          - Sepolia (public testnet): we sign a raw transaction locally with
            the configured private key and broadcast it (eth.send_raw_transaction),
            which is required because public nodes don't hold your keys.

        The hash is embedded as a self-transaction data field. No smart
        contract, no healthcare data on-chain — only the SHA-256 anchor.

        Returns:
            Tuple of (tx_hash_hex, block_number)
        """
        payload = f"{resource_id}|{data_hash}".encode("utf-8")

        # ── Sepolia: locally-signed raw transaction ────────────────────
        if self._network == "sepolia" and self._private_key:
            nonce = self.w3.eth.get_transaction_count(self._account)
            tx = {
                "from": self._account,
                "to": self._account,
                "value": 0,
                "data": self.w3.to_hex(payload),
                "nonce": nonce,
                "chainId": self._chain_id or self.w3.eth.chain_id,
                "gas": 60000,
                "maxFeePerGas": self.w3.to_wei(30, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(2, "gwei"),
            }
            signed = self.w3.eth.account.sign_transaction(tx, self._private_key)
            raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            return "0x" + receipt.transactionHash.hex(), receipt.blockNumber

        # ── Ganache: unlocked account ──────────────────────────────────
        tx = {
            "from": self._account,
            "to": self._account,
            "value": 0,
            "data": self.w3.to_hex(payload),
            "gas": 100000,
            "gasPrice": self.w3.to_wei(20, "gwei"),
        }
        tx_hash = self.w3.eth.send_transaction(tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=10)
        return "0x" + receipt.transactionHash.hex(), receipt.blockNumber

    def explorer_link(self, tx_hash: str) -> Optional[str]:
        """Build a human-clickable block-explorer URL for a tx (Sepolia)."""
        if not tx_hash or not self._explorer_url or self._network != "sepolia":
            return None
        return f"{self._explorer_url}{tx_hash}"

    # ─────────────────────────────────────────────────────────────────
    # VERIFICATION
    # ─────────────────────────────────────────────────────────────────

    def verify_record(self, resource_type: str, resource_id: str, current_record: dict) -> dict:
        """
        Verify a record's integrity against its blockchain-stored hash.

        Computes the current hash and compares against the latest anchor.

        Returns:
            Verification result dict with status and details
        """
        now = utc_now()

        # Get the latest blockchain anchor for this resource
        anchor = self.anchors.find_one(
            {"resource_type": resource_type, "resource_id": resource_id},
            sort=[("created_at", -1)],
        )

        if not anchor:
            return {
                "status": "NO_ANCHOR",
                "message": "No blockchain anchor found for this record.",
                "record_id": resource_id,
                "verified_at": now,
            }

        # Compute current hash
        current_hash = self.compute_record_hash(current_record)
        blockchain_hash = anchor["data_hash"]

        if current_hash == blockchain_hash:
            return {
                "status": "VERIFIED",
                "message": "Record integrity confirmed. Hash matches blockchain anchor.",
                "record_id": resource_id,
                "current_hash": current_hash,
                "blockchain_hash": blockchain_hash,
                "transaction_hash": anchor.get("transaction_hash"),
                "block_number": anchor.get("block_number"),
                "anchored_at": anchor["created_at"],
                "verified_at": now,
            }
        else:
            return {
                "status": "INTEGRITY_VIOLATION",
                "message": "Record hash does not match blockchain anchor. Possible tampering.",
                "record_id": resource_id,
                "current_hash": current_hash,
                "blockchain_hash": blockchain_hash,
                "transaction_hash": anchor.get("transaction_hash"),
                "block_number": anchor.get("block_number"),
                "anchored_at": anchor["created_at"],
                "verified_at": now,
            }

    def get_anchor(self, resource_type: str, resource_id: str) -> Optional[dict]:
        """Get the latest anchor for a resource."""
        return self.anchors.find_one(
            {"resource_type": resource_type, "resource_id": resource_id},
            sort=[("created_at", -1)],
        )

    def get_anchors_for_patient(self, patient_id: str) -> list:
        """Get all anchors related to a patient."""
        return list(
            self.anchors.find({"patient_id": patient_id}).sort("created_at", -1)
        )

    def get_status(self) -> dict:
        """Get blockchain connection status."""
        connected = self.is_connected
        block_number = None
        if connected:
            try:
                block_number = self.w3.eth.block_number
            except Exception:
                pass
        return {
            "connected": connected,
            "network": "sepolia" if self._network == "sepolia" else "ganache-local",
            "chain_id": self._chain_id or (11155111 if self._network == "sepolia" else 1337),
            "block_number": block_number,
            "account": self._account,
            "explorer_base": self._explorer_url if self._network == "sepolia" else None,
            "total_anchors": self.anchors.count_documents({}),
        }
