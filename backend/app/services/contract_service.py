"""
Contract Service — SIH 26125 (ADDITIVE).

Thin web3.py wrapper around the deployed Solidity contracts
(PlatformAccessControl, IdentityRegistry). It composes with — and never replaces —
the existing BlockchainService hash-anchoring.

Design goals:
  - GRACEFUL DEGRADATION: if web3 is unavailable, the chain is unreachable, or the
    contract addresses/ABIs are not configured, methods return a structured
    "not available" result instead of raising. Healthcare functionality NEVER
    depends on this service. (Read endpoints -> serve degraded; critical writes ->
    the caller returns HTTP 503 fail-closed, per the spec.)
  - keccak256 / bytes32 conventions match did_service.py and the Solidity contracts
    (Canonical Derivation & Encoding).

Networks:
  - ganache: uses the first unlocked account as sender.
  - sepolia: signs locally with SEPOLIA_PRIVATE_KEY.
"""

from __future__ import annotations

import json
import os
from typing import Optional


ABI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "contracts", "abi")


class ContractService:
    """Interacts with the deployed identity/access contracts (best-effort)."""

    def __init__(self, w3=None, config=None):
        self.w3 = w3
        self._network = "ganache"
        self._private_key = ""
        self._chain_id = None
        self._access_addr = ""
        self._registry_addr = ""

        cfg = config
        if cfg is None:
            try:
                from flask import current_app
                cfg = current_app.config
            except Exception:
                cfg = None
        if cfg is not None:
            g = cfg.get if hasattr(cfg, "get") else (lambda k, d=None: getattr(cfg, k, d))
            self._network = (g("BLOCKCHAIN_NETWORK", "ganache") or "ganache").lower()
            self._private_key = g("SEPOLIA_PRIVATE_KEY", "") or ""
            self._access_addr = g("SIH_ACCESS_CONTROL_ADDRESS", "") or ""
            self._registry_addr = g("SIH_IDENTITY_REGISTRY_ADDRESS", "") or ""
            self._chain_id = g("SEPOLIA_CHAIN_ID", None) if self._network == "sepolia" else g("GANACHE_CHAIN_ID", None)

        self._account = None
        if self.w3 is not None:
            try:
                if self._network == "sepolia" and self._private_key:
                    self._account = self.w3.eth.account.from_key(self._private_key).address
                elif self._is_connected():
                    accts = self.w3.eth.accounts
                    self._account = accts[0] if accts else None
            except Exception:
                self._account = None

    # ── availability ───────────────────────────────────────────────────

    def _is_connected(self) -> bool:
        try:
            return self.w3 is not None and self.w3.is_connected()
        except Exception:
            return False

    @property
    def available(self) -> bool:
        """True only if chain is connected AND both contract addresses are set."""
        return self._is_connected() and bool(self._access_addr) and bool(self._registry_addr)

    def status(self) -> dict:
        return {
            "chain_available": self._is_connected(),
            "contracts_configured": bool(self._access_addr and self._registry_addr),
            "available": self.available,
            "network": self._network,
            "access_control_address": self._access_addr or None,
            "identity_registry_address": self._registry_addr or None,
        }

    # ── ABI / contract loading ──────────────────────────────────────────

    @staticmethod
    def _load_abi(name: str) -> Optional[list]:
        path = os.path.join(ABI_DIR, f"{name}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("abi")
        except Exception:
            return None

    def _access_control(self):
        abi = self._load_abi("PlatformAccessControl")
        if not abi or not self._access_addr:
            return None
        return self.w3.eth.contract(address=self.w3.to_checksum_address(self._access_addr), abi=abi)

    def _registry(self):
        abi = self._load_abi("IdentityRegistry")
        if not abi or not self._registry_addr:
            return None
        return self.w3.eth.contract(address=self.w3.to_checksum_address(self._registry_addr), abi=abi)

    # ── hashing (matches did_service.py + Solidity) ─────────────────────

    def did_hash(self, did: str) -> bytes:
        """keccak256(utf8(did)) -> 32 bytes."""
        from eth_utils import keccak
        return keccak(did.encode("utf-8"))

    def role_hash(self, role_name: str) -> bytes:
        """keccak256("ROLE_NAME") -> 32 bytes (matches Solidity constants)."""
        from eth_utils import keccak
        return keccak(text=role_name)

    @staticmethod
    def _to_bytes32(hex_str: str) -> bytes:
        h = hex_str[2:] if hex_str.startswith("0x") else hex_str
        return bytes.fromhex(h)

    # ── transaction sending (ganache unlocked / sepolia signed) ─────────

    def _send(self, fn):
        """Send a contract function transaction; returns tx hash hex."""
        if self._network == "sepolia" and self._private_key:
            nonce = self.w3.eth.get_transaction_count(self._account)
            tx = fn.build_transaction({
                "from": self._account,
                "nonce": nonce,
                "chainId": self._chain_id or self.w3.eth.chain_id,
                "gas": 300000,
                "maxFeePerGas": self.w3.to_wei(30, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(2, "gwei"),
            })
            signed = self.w3.eth.account.sign_transaction(tx, self._private_key)
            raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
            tx_hash = self.w3.eth.send_raw_transaction(raw)
        else:
            tx_hash = fn.transact({"from": self._account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        return "0x" + receipt.transactionHash.hex()

    # ── identity operations ─────────────────────────────────────────────

    def register_identity(self, did: str, pub_key_hash_hex: str) -> dict:
        """Register a DID on-chain. Returns {ok, tx_hash} or {ok:False, reason}."""
        if not self.available:
            return {"ok": False, "reason": "chain_or_contracts_unavailable"}
        reg = self._registry()
        if reg is None:
            return {"ok": False, "reason": "registry_not_loaded"}
        try:
            fn = reg.functions.register(self.did_hash(did), self._to_bytes32(pub_key_hash_hex))
            tx = self._send(fn)
            return {"ok": True, "tx_hash": tx}
        except Exception as e:
            return {"ok": False, "reason": str(e)[:160]}

    def revoke_identity(self, did: str) -> dict:
        if not self.available:
            return {"ok": False, "reason": "chain_or_contracts_unavailable"}
        reg = self._registry()
        if reg is None:
            return {"ok": False, "reason": "registry_not_loaded"}
        try:
            tx = self._send(reg.functions.revoke(self.did_hash(did)))
            return {"ok": True, "tx_hash": tx}
        except Exception as e:
            return {"ok": False, "reason": str(e)[:160]}

    def is_identity_verified(self, did: str) -> Optional[bool]:
        """On-chain verification status. None if chain/contracts unavailable."""
        if not self.available:
            return None
        reg = self._registry()
        if reg is None:
            return None
        try:
            return bool(reg.functions.isVerified(self.did_hash(did)).call())
        except Exception:
            return None

    # ── role operations ─────────────────────────────────────────────────

    _ROLE_CONST = {
        "admin": "ADMIN_ROLE",
        "manager": "MANAGER_ROLE",
        "auditor": "AUDITOR_ROLE",
        "user": "USER_ROLE",
    }

    def _role_bytes(self, sih_role: str) -> Optional[bytes]:
        const = self._ROLE_CONST.get(sih_role.lower())
        if not const:
            return None
        return self.role_hash(const)

    def grant_role(self, did: str, sih_role: str) -> dict:
        if not self.available:
            return {"ok": False, "reason": "chain_or_contracts_unavailable"}
        role = self._role_bytes(sih_role)
        if role is None:
            return {"ok": False, "reason": "unknown_role"}
        pac = self._access_control()
        if pac is None:
            return {"ok": False, "reason": "access_control_not_loaded"}
        try:
            tx = self._send(pac.functions.grantSIHRole(self.did_hash(did), role))
            return {"ok": True, "tx_hash": tx}
        except Exception as e:
            return {"ok": False, "reason": str(e)[:160]}

    def revoke_role(self, did: str, sih_role: str) -> dict:
        if not self.available:
            return {"ok": False, "reason": "chain_or_contracts_unavailable"}
        role = self._role_bytes(sih_role)
        if role is None:
            return {"ok": False, "reason": "unknown_role"}
        pac = self._access_control()
        if pac is None:
            return {"ok": False, "reason": "access_control_not_loaded"}
        try:
            tx = self._send(pac.functions.revokeSIHRole(self.did_hash(did), role))
            return {"ok": True, "tx_hash": tx}
        except Exception as e:
            return {"ok": False, "reason": str(e)[:160]}

    def did_has_role(self, did: str, sih_role: str) -> Optional[bool]:
        if not self.available:
            return None
        role = self._role_bytes(sih_role)
        if role is None:
            return None
        pac = self._access_control()
        if pac is None:
            return None
        try:
            return bool(pac.functions.didHasRole(self.did_hash(did), role).call())
        except Exception:
            return None
