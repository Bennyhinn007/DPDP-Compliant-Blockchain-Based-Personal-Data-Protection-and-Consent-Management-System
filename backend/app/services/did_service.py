"""
DID Identity Service — SIH 26125 Identity & Asset Extension (ADDITIVE).

Implements a PROTOTYPE decentralized-identity layer on top of the existing
DPDP healthcare accounts. This does NOT replace the existing user_id, JWT,
password, OAuth, or MFA login — it is an additional cryptographic identity.

Prototype disclosure: `did:rakshaid:<id>` is a project-specific DID method for
demonstration. It is NOT an interoperable production DID network (e.g. ION/Sovrin).

Cryptography (must match frontend `lib/wallet.ts` and Solidity — see the
Canonical Derivation & Encoding section in
.kiro/specs/sih-26125-identity-asset-extension/data_model.md):

  keypair        secp256k1 (Ethereum curve)
  public_key     uncompressed 65 bytes: 0x04 || X(32) || Y(32), stored as 0x-hex
  pubKeyHash     keccak256(65-byte uncompressed pubkey)  -> bytes32 (0x-hex)
  DID identifier did:rakshaid:<base58btc( keccak256(pubkey)[0:16] )>
  didHash        keccak256(utf8(full_did_string))        -> bytes32 (0x-hex)
  auth signature EIP-191 personal_sign over the exact challenge message; verified
                 with eth_account.recover_message against the DID's registered key.

All hashes here are keccak256 (native to Solidity/bytes32). The existing
healthcare SHA-256 record anchoring is a SEPARATE, UNCHANGED subsystem.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_keys import keys as eth_keys
from eth_utils import keccak
from pymongo.errors import DuplicateKeyError

from app.utils.helpers import utc_now


# Bitcoin Base58 alphabet (base58btc).
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _base58btc(data: bytes) -> str:
    """Minimal, dependency-free base58btc encoder (must match the frontend)."""
    n = int.from_bytes(data, "big")
    out = ""
    while n > 0:
        n, rem = divmod(n, 58)
        out = _B58_ALPHABET[rem] + out
    # Preserve leading zero bytes as '1'.
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    return ("1" * pad) + out


def _to_hex(b: bytes) -> str:
    """0x-prefixed lowercase hex (canonical on-chain string form)."""
    return "0x" + b.hex()


class DIDService:
    """
    DID registration, resolution, revocation, and EIP-191 challenge-response.

    Storage:
      dids            — DID ↔ user_id link + public key + status
      did_challenges  — single-use nonces (application-level expiry, NO Mongo TTL)
    """

    DID_METHOD = "rakshaid"
    CHALLENGE_TTL_SECONDS = 120
    CHALLENGE_MESSAGE_PREFIX = "DPDP-DID-AUTH"

    def __init__(self, db, config=None):
        self.db = db
        self.dids = db["dids"]
        self.challenges = db["did_challenges"]
        # Config is optional; fall back to defaults so unit tests can pass a bare db.
        if config is not None:
            getter = config.get if hasattr(config, "get") else (lambda k, d=None: getattr(config, k, d))
            self.DID_METHOD = getter("SIH_DID_METHOD", self.DID_METHOD) or self.DID_METHOD
            self.CHALLENGE_TTL_SECONDS = int(getter("SIH_DID_CHALLENGE_TTL_SECONDS", self.CHALLENGE_TTL_SECONDS))

    # ── Canonical derivation ──────────────────────────────────────────

    @staticmethod
    def normalize_public_key(public_key_hex: str) -> bytes:
        """
        Accept a public key as 0x-hex in either 65-byte uncompressed form
        (0x04||X||Y) or 64-byte raw (X||Y), and return the 65-byte uncompressed
        bytes used for all hashing.
        """
        h = public_key_hex[2:] if public_key_hex.startswith("0x") else public_key_hex
        raw = bytes.fromhex(h)
        if len(raw) == 64:
            raw = b"\x04" + raw
        if len(raw) != 65 or raw[0] != 0x04:
            raise ValueError("public_key must be 65-byte uncompressed secp256k1 (0x04||X||Y)")
        return raw

    def derive_did(self, public_key_hex: str) -> dict:
        """
        Derive the canonical DID identity material from a public key.

        Returns dict: did, did_hash, pub_key_hash, public_key, address.
        """
        uncompressed = self.normalize_public_key(public_key_hex)
        pub_key_hash = keccak(uncompressed)                       # bytes32
        identifier = _base58btc(pub_key_hash[:16])                # first 16 bytes
        did = f"did:{self.DID_METHOD}:{identifier}"
        did_hash = keccak(did.encode("utf-8"))                    # bytes32
        # Ethereum address = last 20 bytes of keccak(pubkey without 0x04 prefix).
        address = "0x" + keccak(uncompressed[1:])[-20:].hex()
        return {
            "did": did,
            "did_hash": _to_hex(did_hash),
            "pub_key_hash": _to_hex(pub_key_hash),
            "public_key": _to_hex(uncompressed),
            "address": address,
        }

    # ── Registration / resolution / revocation ────────────────────────

    def register_did(self, user_id: str, public_key_hex: str) -> dict:
        """
        Create a DID for an existing user (the user_id is preserved; the DID is
        an additional layer). One DID per user (enforced by unique index).
        """
        material = self.derive_did(public_key_hex)
        now = utc_now()

        existing = self.dids.find_one({"user_id": user_id})
        if existing:
            raise ValueError("This user already has a DID")

        # Guard against a DID-string (_id) collision. The DID is derived from the
        # public key, so the same key always yields the same DID. Inserting a doc
        # whose _id already exists would raise an uncaught DuplicateKeyError (HTTP
        # 500), so detect it here and surface a clean validation error instead.
        did_owner = self.dids.find_one({"_id": material["did"]})
        if did_owner:
            if did_owner.get("user_id") == user_id:
                raise ValueError("This user already has a DID")
            raise ValueError("This DID is already registered to another account")

        did_document = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": material["did"],
            "verificationMethod": [{
                "id": f"{material['did']}#key-1",
                "type": "EcdsaSecp256k1VerificationKey2019",
                "controller": material["did"],
                "publicKeyHex": material["public_key"],
            }],
            "note": "Prototype DID method (rakshaid) — not a production DID network.",
        }

        doc = {
            "_id": material["did"],
            "user_id": user_id,
            "public_key": material["public_key"],
            "pub_key_hash": material["pub_key_hash"],
            "did_hash": material["did_hash"],
            "address": material["address"],
            "status": "active",
            "sih_role": None,                # set later by the roles layer (Week 2)
            "did_document": did_document,
            "created_at": now,
            "updated_at": now,
        }
        try:
            self.dids.insert_one(doc)
        except DuplicateKeyError:
            # Concurrent insert or a leftover doc with the same DID/user_id.
            # Convert to a clean validation error (HTTP 422) instead of a 500.
            raise ValueError("This DID is already registered")
        return doc

    def resolve_did(self, did: str) -> Optional[dict]:
        return self.dids.find_one({"_id": did})

    def get_did_for_user(self, user_id: str) -> Optional[dict]:
        return self.dids.find_one({"user_id": user_id})

    def is_verified(self, did: str) -> bool:
        """Mirror of on-chain IdentityRegistry.isVerified (off-chain source)."""
        doc = self.dids.find_one({"_id": did})
        return bool(doc) and doc.get("status") == "active"

    def revoke_did(self, did: str) -> bool:
        res = self.dids.update_one(
            {"_id": did}, {"$set": {"status": "revoked", "updated_at": utc_now()}}
        )
        return res.matched_count > 0

    # ── EIP-191 challenge-response ─────────────────────────────────────

    def create_challenge(self, did: str) -> dict:
        """
        Issue a single-use nonce bound to the DID. Application-level expiry.
        Returns { did, nonce, message, expires_at, exp }.
        """
        doc = self.dids.find_one({"_id": did})
        if not doc:
            raise ValueError("Unknown DID")
        if doc.get("status") != "active":
            raise ValueError("DID is not active")

        nonce = "0x" + secrets.token_hex(32)
        now_dt = datetime.now(timezone.utc)
        expires_dt = now_dt + timedelta(seconds=self.CHALLENGE_TTL_SECONDS)
        exp_unix = int(expires_dt.timestamp())
        message = self._build_message(did, nonce, exp_unix)

        self.challenges.insert_one({
            "_id": nonce,                 # nonce is unique
            "did": did,
            "nonce": nonce,
            "message": message,
            "exp": exp_unix,
            "expires_at": expires_dt.isoformat(),   # existing ISO-string convention
            "used": False,
            "created_at": utc_now(),
        })
        return {"did": did, "nonce": nonce, "message": message,
                "expires_at": expires_dt.isoformat(), "exp": exp_unix}

    def _build_message(self, did: str, nonce: str, exp_unix: int) -> str:
        """Exact challenge message format (must match the frontend signer)."""
        return f"{self.CHALLENGE_MESSAGE_PREFIX}|did={did}|nonce={nonce}|exp={exp_unix}"

    def verify_signature(self, did: str, nonce: str, signature: str) -> dict:
        """
        Verify an EIP-191 personal_sign signature over the challenge message.

        Enforces (application-level): DID active, challenge exists & matches DID,
        not used, not expired, signer address matches the DID's registered key.

        Returns the DID document on success. Raises ValueError otherwise.
        Marks the challenge used on success (single-use replay protection).
        """
        did_doc = self.dids.find_one({"_id": did})
        if not did_doc:
            raise ValueError("Unknown DID")
        if did_doc.get("status") != "active":
            raise ValueError("DID is not active")

        challenge = self.challenges.find_one({"_id": nonce})
        if not challenge:
            raise ValueError("Unknown or missing challenge")
        if challenge.get("did") != did:
            raise ValueError("Challenge does not belong to this DID")
        if challenge.get("used"):
            raise ValueError("Challenge already used")

        # Application-level expiry (no Mongo TTL).
        try:
            expires_dt = datetime.fromisoformat(challenge["expires_at"])
        except (ValueError, TypeError, KeyError):
            raise ValueError("Invalid challenge expiry")
        if datetime.now(timezone.utc) > expires_dt:
            raise ValueError("Challenge expired")

        message = challenge["message"]
        try:
            recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
        except Exception:
            raise ValueError("Invalid signature")

        expected_address = did_doc.get("address")
        if not expected_address or recovered.lower() != expected_address.lower():
            raise ValueError("Signature does not match the DID's registered key")

        # Single-use: consume the challenge.
        self.challenges.update_one({"_id": nonce}, {"$set": {"used": True}})
        return did_doc

    # ── Hygiene (optional; correctness never depends on it) ────────────

    def cleanup_expired_challenges(self) -> int:
        """Opportunistic/periodic cleanup of expired or used challenges."""
        now_iso = datetime.now(timezone.utc).isoformat()
        res = self.challenges.delete_many(
            {"$or": [{"used": True}, {"expires_at": {"$lt": now_iso}}]}
        )
        return res.deleted_count

    # ── Test helper (server-side keygen for demos/tests only) ──────────

    @staticmethod
    def generate_keypair() -> dict:
        """
        Generate a secp256k1 keypair. Intended for tests/demos; in the real flow
        the PRIVATE KEY is generated and held CLIENT-SIDE (browser wallet) and
        never sent to the server. Returns private_key, public_key (65-byte hex).
        """
        acct = Account.create()
        priv = acct.key
        pk = eth_keys.PrivateKey(priv)
        uncompressed = b"\x04" + pk.public_key.to_bytes()
        return {
            "private_key": "0x" + priv.hex(),
            "public_key": _to_hex(uncompressed),
            "address": acct.address,
        }
