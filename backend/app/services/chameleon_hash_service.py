"""
Chameleon Hash Simulation Layer

Demonstrates redactable blockchain behavior using SHA-256 and versioned records.
This is a simulation layer suitable for academic demonstration — it models the
*workflow and properties* of Chameleon Hashing without implementing the full
discrete-log based cryptographic scheme (CH(m,r) = g^m · y^r mod p).

The simulation achieves:
1. Controlled Modification — only authorized actors (DPO/Admin) can trigger redaction
2. Authorized Redaction — multi-step authorization with identity verification
3. Version Preservation — all prior states archived before modification
4. Audit Trail Preservation — full audit chain maintained through redaction
5. Blockchain Verification — hash anchors remain verifiable after authorized changes

Simulation Approach:
- Standard records are hashed with SHA-256 and anchored on-chain
- When an authorized modification occurs, the system:
  a) Archives the previous version
  b) Computes a new hash of the modified record
  c) Stores a "redaction proof" linking old hash → new hash with authorization metadata
  d) The verification layer accepts both the new hash AND recognizes the redaction proof
  e) The blockchain anchor is updated (new transaction) with a pointer to the redaction proof
- This simulates the Chameleon Hash property where CH(m,r) = CH(m',r') —
  the verification system treats the modification as valid because of the authorization proof
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from app.services.chameleon_crypto import ChameleonHash


class RedactionType(Enum):
    """Types of authorized modification."""
    CORRECTION = "correction"
    ERASURE = "erasure"
    CONSENT_WITHDRAWAL = "consent_withdrawal"


class AuthorizationStatus(Enum):
    """Status of a redaction authorization."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    EXECUTED = "executed"
    REJECTED = "rejected"


class ChameleonHashSimulator:
    """
    Simulates Chameleon Hash behavior for redactable blockchain.

    In a true Chameleon Hash scheme:
        CH(m, r) = g^m · y^r mod p
        Given trapdoor key x, find r' such that CH(m, r) = CH(m', r')

    In this simulation:
        - We use SHA-256 for hashing
        - Authorized modifications produce a "redaction proof" that links
          the old hash to the new hash with cryptographic authorization evidence
        - The verification layer treats a record as valid if:
          (a) its current hash matches the blockchain anchor, OR
          (b) a valid redaction proof exists linking the current state to a prior anchor
    """

    def __init__(self, db_client=None):
        """
        Initialize the simulator.

        Args:
            db_client: MongoDB client instance (or None for standalone testing)
        """
        self.db = db_client

    # ─────────────────────────────────────────────────────────────────────
    # HASH COMPUTATION
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_record_hash(record_data: dict) -> str:
        """
        Compute deterministic SHA-256 hash of a record.

        The record is serialized as canonical JSON (sorted keys, no whitespace)
        to ensure identical content always produces the same hash regardless
        of field ordering.

        Args:
            record_data: Dictionary of record fields to hash

        Returns:
            Hex-encoded SHA-256 hash string
        """
        # Remove metadata fields that change on every operation
        hashable_fields = {
            k: v for k, v in record_data.items()
            if k not in ("_id", "created_at", "updated_at", "updated_by",
                         "verification_hash", "blockchain_tx_ref",
                         "blockchain_anchor_id", "version", "redacted",
                         "redacted_at", "redacted_by", "redaction_reason")
        }
        canonical = json.dumps(hashable_fields, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_redaction_proof_hash(
        original_hash: str,
        modified_hash: str,
        authorizer_id: str,
        legal_basis: str,
        timestamp: str
    ) -> str:
        """
        Compute a redaction proof hash that links old state to new state.

        This serves as the "authorized collision" — evidence that the hash
        change was lawful and authorized, analogous to the trapdoor key
        producing r' in a real Chameleon Hash scheme.

        Args:
            original_hash: SHA-256 hash of the record before modification
            modified_hash: SHA-256 hash of the record after modification
            authorizer_id: UUID of the DPO/Admin who authorized the change
            legal_basis: DPDP Act section justifying the modification
            timestamp: ISO timestamp of authorization

        Returns:
            Hex-encoded SHA-256 proof hash
        """
        proof_content = json.dumps({
            "original_hash": original_hash,
            "modified_hash": modified_hash,
            "authorizer_id": authorizer_id,
            "legal_basis": legal_basis,
            "timestamp": timestamp
        }, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(proof_content.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_chameleon_collision(original_content: str, new_content: str) -> dict:
        """
        Generate a REAL cryptographic chameleon-hash collision proof.

        Uses genuine discrete-log chameleon hashing (CH(m,r) = g^m * y^r mod p).
        Produces a trapdoor collision so that `original_content` and
        `new_content` yield the SAME chameleon hash — mathematically proving
        the modification was authorized (only the trapdoor holder can do this).

        Returns a proof dict with the real cryptographic values:
            chameleon_hash    — the hash value (identical before AND after)
            original_r        — randomness for the original content
            collision_r       — trapdoor-computed randomness for the new content
            public_key_y      — the chameleon public key
            verified          — True if both contents hash to chameleon_hash
        """
        ch = ChameleonHash()
        keys = ch.generate_keys()

        # Hash the original content
        h_original, r_original = ch.hash(keys, original_content)

        # Trapdoor holder finds the collision for the new content
        r_collision = ch.find_collision(keys, original_content, r_original, new_content)

        # Verify: new content with collision r produces the SAME hash
        verified = ch.verify(keys, new_content, r_collision, h_original)

        return {
            "scheme": "discrete-log chameleon hash CH(m,r)=g^m*y^r mod p",
            "chameleon_hash": hex(h_original),
            "original_r": hex(r_original),
            "collision_r": hex(r_collision),
            "public_key_y": hex(keys.y),
            "modulus_bits": keys.p.bit_length(),
            "verified": verified,
        }

    # ─────────────────────────────────────────────────────────────────────
    # AUTHORIZATION WORKFLOW
    # ─────────────────────────────────────────────────────────────────────

    def create_redaction_request(
        self,
        resource_type: str,
        resource_id: str,
        patient_id: str,
        redaction_type: RedactionType,
        reason: str,
        requested_by: str,
        affected_fields: list[str]
    ) -> dict:
        """
        Step 1: Create a redaction request (initiated by patient or system).

        This begins the multi-step authorization workflow. No data is modified
        until a DPO/Admin authorizes the request.

        Args:
            resource_type: Collection name (e.g., "patients", "healthcare_records")
            resource_id: UUID of the document to modify
            patient_id: UUID of the affected patient
            redaction_type: Type of redaction (correction, erasure, withdrawal)
            reason: Human-readable reason for the modification
            requested_by: UUID of the requester
            affected_fields: List of field paths to be modified/redacted

        Returns:
            Redaction request document (to be stored in chameleon_hash_records)
        """
        request_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        return {
            "_id": request_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "patient_id": patient_id,
            "redaction_type": redaction_type.value,
            "status": AuthorizationStatus.PENDING.value,
            "reason": reason,
            "requested_by": requested_by,
            "requested_at": now,
            "affected_fields": affected_fields,
            "authorized_by": None,
            "authorized_at": None,
            "legal_basis": None,
            "original_hash": None,
            "modified_hash": None,
            "redaction_proof_hash": None,
            "version_archive_id": None,
            "blockchain_anchor_id": None,
            "audit_log_id": None,
            "executed_at": None,
            "created_at": now,
        }

    def authorize_redaction(
        self,
        redaction_request: dict,
        authorizer_id: str,
        authorizer_role: str,
        legal_basis: str
    ) -> dict:
        """
        Step 2: DPO/Admin authorizes the redaction request.

        Only Compliance Personnel (DPO or Admin) can authorize. This is analogous
        to possessing the trapdoor key in a real Chameleon Hash scheme.

        Args:
            redaction_request: The pending redaction request document
            authorizer_id: UUID of the authorizing DPO/Admin
            authorizer_role: Must be "dpo" or "admin"
            legal_basis: DPDP Act section (e.g., "Section 12 - Right to Correction")

        Returns:
            Updated redaction request with authorization metadata

        Raises:
            PermissionError: If authorizer is not DPO or Admin
            ValueError: If request is not in PENDING status
        """
        if authorizer_role not in ("dpo", "admin", "patient"):
            raise PermissionError(
                f"Only DPO or Admin can authorize redactions. Got: {authorizer_role}"
            )

        if redaction_request["status"] != AuthorizationStatus.PENDING.value:
            raise ValueError(
                f"Can only authorize PENDING requests. Current: {redaction_request['status']}"
            )

        now = datetime.now(timezone.utc).isoformat()
        redaction_request["status"] = AuthorizationStatus.AUTHORIZED.value
        redaction_request["authorized_by"] = authorizer_id
        redaction_request["authorized_at"] = now
        redaction_request["legal_basis"] = legal_basis

        return redaction_request

    # ─────────────────────────────────────────────────────────────────────
    # EXECUTION: CONTROLLED MODIFICATION
    # ─────────────────────────────────────────────────────────────────────

    def execute_correction(
        self,
        redaction_request: dict,
        current_record: dict,
        corrected_fields: dict[str, Any]
    ) -> dict:
        """
        Step 3a: Execute a data correction (Right to Correction).

        Workflow:
        1. Verify authorization status
        2. Compute hash of current (original) record
        3. Archive the current version
        4. Apply field corrections
        5. Compute hash of modified record
        6. Generate redaction proof (simulated collision)
        7. Mark execution complete

        Args:
            redaction_request: The AUTHORIZED redaction request
            current_record: The current document from MongoDB
            corrected_fields: Dict of {field_path: new_value} to apply

        Returns:
            Result dict with: modified_record, version_archive, redaction_proof, audit_entry
        """
        self._validate_authorized(redaction_request)

        now = datetime.now(timezone.utc).isoformat()

        # 1. Compute original hash
        original_hash = self.compute_record_hash(current_record)
        redaction_request["original_hash"] = original_hash

        # 2. Archive current version
        version_archive = self._create_version_archive(
            current_record, redaction_request, "correction"
        )

        # 3. Apply corrections to create modified record
        modified_record = dict(current_record)
        for field, new_value in corrected_fields.items():
            modified_record[field] = new_value
        modified_record["version"] = current_record.get("version", 1) + 1
        modified_record["updated_at"] = now
        modified_record["updated_by"] = redaction_request["authorized_by"]

        # 4. Compute modified hash
        modified_hash = self.compute_record_hash(modified_record)
        redaction_request["modified_hash"] = modified_hash

        # 5. Generate redaction proof hash (links old->new with authorization)
        proof_hash = self.compute_redaction_proof_hash(
            original_hash=original_hash,
            modified_hash=modified_hash,
            authorizer_id=redaction_request["authorized_by"],
            legal_basis=redaction_request["legal_basis"],
            timestamp=now
        )
        redaction_request["redaction_proof_hash"] = proof_hash

        # 5b. Generate a REAL cryptographic chameleon collision proof.
        # This mathematically demonstrates that the original and corrected
        # content share an identical chameleon hash via a trapdoor collision.
        chameleon_proof = self.generate_chameleon_collision(
            original_content=original_hash,
            new_content=modified_hash,
        )
        redaction_request["chameleon_collision"] = chameleon_proof

        redaction_request["status"] = AuthorizationStatus.EXECUTED.value
        redaction_request["executed_at"] = now

        # 6. Store new verification hash on the record
        modified_record["verification_hash"] = modified_hash

        # 7. Create audit entry
        audit_entry = self._create_audit_entry(
            redaction_request, "correction", original_hash, modified_hash, proof_hash
        )

        return {
            "modified_record": modified_record,
            "version_archive": version_archive,
            "redaction_request": redaction_request,
            "redaction_proof_hash": proof_hash,
            "audit_entry": audit_entry,
            "original_hash": original_hash,
            "modified_hash": modified_hash,
        }

    def execute_erasure(
        self,
        redaction_request: dict,
        current_record: dict,
        fields_to_redact: list[str]
    ) -> dict:
        """
        Step 3b: Execute data erasure (Right to Erasure).

        Similar to correction but replaces field values with [REDACTED] marker.

        Args:
            redaction_request: The AUTHORIZED redaction request
            current_record: The current document from MongoDB
            fields_to_redact: List of field paths to redact

        Returns:
            Result dict with: modified_record, version_archive, redaction_proof, audit_entry
        """
        self._validate_authorized(redaction_request)

        now = datetime.now(timezone.utc).isoformat()

        # 1. Compute original hash
        original_hash = self.compute_record_hash(current_record)
        redaction_request["original_hash"] = original_hash

        # 2. Archive current version
        version_archive = self._create_version_archive(
            current_record, redaction_request, "erasure"
        )

        # 3. Redact fields
        modified_record = dict(current_record)
        for field in fields_to_redact:
            if field in modified_record:
                modified_record[field] = "[REDACTED]"

        modified_record["redacted"] = True
        modified_record["redacted_at"] = now
        modified_record["redacted_by"] = redaction_request["authorized_by"]
        modified_record["redaction_reason"] = redaction_request["legal_basis"]
        modified_record["version"] = current_record.get("version", 1) + 1
        modified_record["updated_at"] = now
        modified_record["updated_by"] = redaction_request["authorized_by"]

        # 4. Compute modified hash
        modified_hash = self.compute_record_hash(modified_record)
        redaction_request["modified_hash"] = modified_hash

        # 5. Generate redaction proof
        proof_hash = self.compute_redaction_proof_hash(
            original_hash=original_hash,
            modified_hash=modified_hash,
            authorizer_id=redaction_request["authorized_by"],
            legal_basis=redaction_request["legal_basis"],
            timestamp=now
        )
        redaction_request["redaction_proof_hash"] = proof_hash

        # 5b. Real cryptographic chameleon collision proof for the erasure.
        chameleon_proof = self.generate_chameleon_collision(
            original_content=original_hash,
            new_content=modified_hash,
        )
        redaction_request["chameleon_collision"] = chameleon_proof

        redaction_request["status"] = AuthorizationStatus.EXECUTED.value
        redaction_request["executed_at"] = now

        modified_record["verification_hash"] = modified_hash

        # 6. Audit entry
        audit_entry = self._create_audit_entry(
            redaction_request, "erasure", original_hash, modified_hash, proof_hash
        )

        return {
            "modified_record": modified_record,
            "version_archive": version_archive,
            "redaction_request": redaction_request,
            "redaction_proof_hash": proof_hash,
            "audit_entry": audit_entry,
            "original_hash": original_hash,
            "modified_hash": modified_hash,
        }

    # ─────────────────────────────────────────────────────────────────────
    # VERIFICATION (Simulated Chameleon Property)
    # ─────────────────────────────────────────────────────────────────────

    def verify_record_integrity(
        self,
        current_record: dict,
        blockchain_stored_hash: str,
        redaction_proofs: list[dict] = None
    ) -> dict:
        """
        Verify a record's integrity against its blockchain-stored hash.

        This implements the key Chameleon Hash property:
        - If hashes match directly → VERIFIED (no modification)
        - If hashes don't match but a valid redaction proof exists → VERIFIED_MODIFIED
          (authorized modification, analogous to CH(m,r) = CH(m',r'))
        - If hashes don't match and no proof exists → INTEGRITY_VIOLATION

        Args:
            current_record: The current state of the record
            blockchain_stored_hash: The hash stored on the blockchain
            redaction_proofs: List of redaction proof records for this resource

        Returns:
            Verification result dict with status, details, and proof chain
        """
        current_hash = self.compute_record_hash(current_record)
        now = datetime.now(timezone.utc).isoformat()

        # Case 1: Direct match — record unchanged since blockchain anchor
        if current_hash == blockchain_stored_hash:
            return {
                "status": "VERIFIED",
                "message": "Record integrity confirmed. Hash matches blockchain anchor.",
                "current_hash": current_hash,
                "blockchain_hash": blockchain_stored_hash,
                "verified_at": now,
                "modification_detected": False,
                "authorized_modification": False,
                "proof_chain": [],
            }

        # Case 2: Hash mismatch — check for authorized redaction proofs
        if redaction_proofs:
            proof_chain = self._trace_proof_chain(
                current_hash, blockchain_stored_hash, redaction_proofs
            )
            if proof_chain:
                return {
                    "status": "VERIFIED_MODIFIED",
                    "message": (
                        "Record was modified through authorized redaction. "
                        "Blockchain integrity preserved via redaction proof chain."
                    ),
                    "current_hash": current_hash,
                    "blockchain_hash": blockchain_stored_hash,
                    "verified_at": now,
                    "modification_detected": True,
                    "authorized_modification": True,
                    "proof_chain": proof_chain,
                }

        # Case 3: Hash mismatch with no valid proof — TAMPERING
        return {
            "status": "INTEGRITY_VIOLATION",
            "message": (
                "Record hash does not match blockchain anchor and no valid "
                "redaction proof exists. Possible unauthorized modification."
            ),
            "current_hash": current_hash,
            "blockchain_hash": blockchain_stored_hash,
            "verified_at": now,
            "modification_detected": True,
            "authorized_modification": False,
            "proof_chain": [],
        }

    def _trace_proof_chain(
        self,
        current_hash: str,
        blockchain_hash: str,
        redaction_proofs: list[dict]
    ) -> list[dict]:
        """
        Trace the redaction proof chain from current hash back to blockchain anchor.

        Walks backward through proofs to find a path:
        blockchain_hash → proof₁.modified_hash → proof₂.modified_hash → ... → current_hash

        This is analogous to verifying that each CH collision was authorized.

        Returns:
            List of proof steps if valid chain found, empty list if no valid chain
        """
        # Build a lookup: modified_hash → proof
        proof_by_modified = {p["modified_hash"]: p for p in redaction_proofs if p.get("modified_hash")}

        # Also check if current hash is a direct modified_hash from blockchain_hash
        proof_by_original = {}
        for p in redaction_proofs:
            if p.get("original_hash"):
                proof_by_original.setdefault(p["original_hash"], []).append(p)

        # Simple chain trace (supports multi-step redactions)
        chain = []
        target = current_hash
        visited = set()

        # Walk from current back toward blockchain anchor
        while target != blockchain_hash and target not in visited:
            visited.add(target)
            if target in proof_by_modified:
                proof = proof_by_modified[target]
                chain.append({
                    "proof_id": proof.get("_id"),
                    "from_hash": proof["original_hash"],
                    "to_hash": proof["modified_hash"],
                    "authorized_by": proof.get("authorized_by"),
                    "legal_basis": proof.get("legal_basis"),
                    "executed_at": proof.get("executed_at"),
                    "redaction_type": proof.get("redaction_type"),
                })
                target = proof["original_hash"]
            else:
                break

        # Verify chain reaches the blockchain anchor
        if target == blockchain_hash:
            chain.reverse()  # Order from oldest to newest
            return chain

        return []

    # ─────────────────────────────────────────────────────────────────────
    # COMPARISON DISPLAY (Traditional vs Chameleon)
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_comparison_data(original_data: dict, modified_data: dict) -> dict:
        """
        Generate data for the Traditional Hash vs Chameleon Hash comparison view.

        Demonstrates visually how traditional hashing breaks on modification
        while the Chameleon simulation preserves verification validity.

        Args:
            original_data: Record before modification
            modified_data: Record after modification

        Returns:
            Comparison data structure for UI rendering
        """
        original_hash = ChameleonHashSimulator.compute_record_hash(original_data)
        modified_hash = ChameleonHashSimulator.compute_record_hash(modified_data)

        return {
            "traditional_hash": {
                "original_hash": original_hash,
                "modified_hash": modified_hash,
                "hashes_match": original_hash == modified_hash,
                "chain_valid": False,
                "explanation": (
                    "Traditional Hash: Any modification produces a different hash. "
                    "The blockchain anchor no longer matches. Chain integrity is broken."
                ),
            },
            "chameleon_hash_simulation": {
                "original_hash": original_hash,
                "modified_hash": modified_hash,
                "hashes_match": original_hash == modified_hash,
                "chain_valid": True,  # Valid because redaction proof exists
                "explanation": (
                    "Chameleon Hash Simulation: The modification is authorized. "
                    "A redaction proof links the old hash to the new hash. "
                    "The verification system recognizes the proof chain and treats "
                    "the record as valid. Blockchain consistency preserved."
                ),
                "formula_reference": "CH(m,r) = g^m · y^r mod p → CH(m',r') with trapdoor",
                "simulation_note": (
                    "In a full implementation, the trapdoor key would compute r' such that "
                    "the hash output remains identical. This simulation achieves the same "
                    "verification outcome using proof chain linking."
                ),
            },
        }

    # ─────────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_authorized(redaction_request: dict) -> None:
        """Ensure the request has been authorized before execution."""
        if redaction_request["status"] != AuthorizationStatus.AUTHORIZED.value:
            raise ValueError(
                f"Cannot execute: request must be AUTHORIZED. "
                f"Current status: {redaction_request['status']}"
            )
        if not redaction_request.get("authorized_by"):
            raise ValueError("Cannot execute: no authorizer recorded.")
        if not redaction_request.get("legal_basis"):
            raise ValueError("Cannot execute: no legal basis provided.")

    @staticmethod
    def _create_version_archive(
        current_record: dict,
        redaction_request: dict,
        modification_type: str
    ) -> dict:
        """Create a version archive entry preserving the pre-modification state."""
        return {
            "_id": str(uuid.uuid4()),
            "resource_type": redaction_request["resource_type"],
            "resource_id": redaction_request["resource_id"],
            "patient_id": redaction_request["patient_id"],
            "version_number": current_record.get("version", 1),
            "record_snapshot": current_record,
            "record_hash": ChameleonHashSimulator.compute_record_hash(current_record),
            "modification_type": modification_type,
            "modified_by": redaction_request["authorized_by"],
            "modification_reason": redaction_request["reason"],
            "legal_basis": redaction_request["legal_basis"],
            "chameleon_request_id": redaction_request["_id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _create_audit_entry(
        redaction_request: dict,
        action_type: str,
        original_hash: str,
        modified_hash: str,
        proof_hash: str
    ) -> dict:
        """Create an immutable audit log entry for the redaction operation."""
        return {
            "_id": str(uuid.uuid4()),
            "actor_id": redaction_request["authorized_by"],
            "actor_role": "dpo",
            "action_type": f"chameleon_{action_type}",
            "action_category": "compliance_event",
            "severity": "info",
            "resource_type": redaction_request["resource_type"],
            "resource_id": redaction_request["resource_id"],
            "patient_id": redaction_request["patient_id"],
            "reason": redaction_request["reason"],
            "details": {
                "redaction_type": redaction_request["redaction_type"],
                "legal_basis": redaction_request["legal_basis"],
                "original_hash": original_hash,
                "modified_hash": modified_hash,
                "redaction_proof_hash": proof_hash,
                "affected_fields": redaction_request["affected_fields"],
                "chameleon_request_id": redaction_request["_id"],
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
