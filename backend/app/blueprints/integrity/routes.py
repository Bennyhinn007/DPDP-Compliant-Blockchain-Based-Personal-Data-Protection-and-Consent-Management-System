"""
Integrity Verification Blueprint.

Provides endpoints for patients to verify their healthcare records
against blockchain-stored hashes.
"""

from flask import request, jsonify, g

from app.blueprints.integrity import integrity_bp
from app.extensions import get_db, get_web3
from app.services.blockchain_service import BlockchainService
from app.services.patient_service import PatientService
from app.middleware.auth_middleware import jwt_required, roles_required
from app.utils.errors import NotFoundError, AuthorizationError


def _get_bc_service():
    return BlockchainService(get_db(), get_web3())


@integrity_bp.route("/health", methods=["GET"])
def integrity_health():
    """Health check."""
    return jsonify({"status": "integrity service ready"}), 200


@integrity_bp.route("/record/<record_id>", methods=["GET"])
@jwt_required
@roles_required("patient", "admin")
def verify_record(record_id):
    """
    Verify a single healthcare record against its blockchain anchor.

    States:
    - VERIFIED: Hash matches blockchain, no modification
    - VERIFIED_MODIFIED: Hash changed but chameleon proof exists (authorized correction)
    - VERIFIED_REDACTED: Record redacted with valid chameleon proof
    - INTEGRITY_VIOLATION: Hash mismatch with no valid proof
    - NO_ANCHOR: No blockchain anchor exists
    """
    db = get_db()
    records = db["healthcare_records"]

    record = records.find_one({"_id": record_id})
    if not record:
        raise NotFoundError("Healthcare record not found")

    # Ownership check for patients
    if g.current_user_role == "patient":
        patients = db["patients"]
        patient = patients.find_one({"user_id": g.current_user_id})
        if not patient or record["patient_id"] != patient["_id"]:
            raise AuthorizationError("You can only verify your own records")

    bc = _get_bc_service()
    result = bc.verify_record("healthcare_records", record_id, record)

    # Enhance with chameleon hash state
    if result["status"] == "INTEGRITY_VIOLATION":
        # Check for chameleon hash proofs
        chameleon_records = list(
            db["chameleon_hash_records"].find({"resource_id": record_id}).sort("created_at", -1)
        )
        if chameleon_records:
            latest = chameleon_records[0]
            if latest.get("status") == "executed":
                if latest.get("redaction_type") == "erasure":
                    result["status"] = "VERIFIED_REDACTED"
                    result["message"] = "Record was lawfully erased. Chameleon hash proof exists."
                else:
                    result["status"] = "VERIFIED_MODIFIED"
                    result["message"] = "Record was lawfully corrected. Chameleon hash proof exists."
                result["chameleon_proof"] = latest.get("redaction_proof_hash")
                result["modification_type"] = latest.get("redaction_type")
                result["legal_basis"] = latest.get("legal_basis")

    return jsonify({"verification": result}), 200


@integrity_bp.route("/tamper-demo", methods=["POST"])
@jwt_required
@roles_required("patient", "admin")
def tamper_demo():
    """
    Live Tamper-Attempt Demo (safe, self-contained — touches no real records).

    Given some original content and a modified version, this endpoint shows the
    project's central thesis side by side:

      A) UNAUTHORIZED TAMPER — an attacker edits the record directly in the DB.
         The SHA-256 anchor no longer matches -> INTEGRITY_VIOLATION (red).

      B) LAWFUL CORRECTION — the same edit performed through the chameleon-hash
         trapdoor. A real discrete-log collision keeps the chameleon hash
         identical, so the anchor still verifies -> VERIFIED_MODIFIED (green).

    Body:
        { "original": "<text>", "modified": "<text>" }
    """
    from app.services.chameleon_crypto import ChameleonHash

    data = request.get_json() or {}
    original = (data.get("original") or "Blood Pressure: 120/80, Diagnosis: Hypertension").strip()
    modified = (data.get("modified") or "Blood Pressure: 118/76, Diagnosis: Hypertension (corrected)").strip()

    # ── The blockchain anchor: a plain SHA-256 of the original content ──
    import hashlib
    anchor_sha = hashlib.sha256(original.encode("utf-8")).hexdigest()

    # ── Scenario A: unauthorized tamper (traditional SHA-256) ──────────
    tampered_sha = hashlib.sha256(modified.encode("utf-8")).hexdigest()
    scenario_tamper = {
        "scenario": "unauthorized_tamper",
        "title": "Unauthorized tamper (traditional hash)",
        "anchor_hash": anchor_sha,
        "current_hash": tampered_sha,
        "hashes_match": anchor_sha == tampered_sha,
        "status": "INTEGRITY_VIOLATION",
        "message": (
            "The record was changed directly. Its SHA-256 no longer matches the "
            "blockchain anchor and there is no authorization proof — tampering is detected."
        ),
    }

    # ── Scenario B: lawful correction via a REAL chameleon collision ───
    ch = ChameleonHash()
    keys = ch.generate_keys()
    ch_hash, r_original = ch.hash(keys, original)
    r_collision = ch.find_collision(keys, original, r_original, modified)
    # Prove the chameleon hash is unchanged after the authorized edit:
    verified = ch.verify(keys, modified, r_collision, ch_hash)

    scenario_lawful = {
        "scenario": "lawful_correction",
        "title": "Lawful correction (chameleon hash)",
        "chameleon_hash": format(ch_hash, "x"),
        "original_r": format(r_original, "x"),
        "collision_r": format(r_collision, "x"),
        "public_key_y": format(keys.y, "x"),
        "modulus_bits": keys.p.bit_length(),
        "hash_identical_after_edit": verified,
        "status": "VERIFIED_MODIFIED" if verified else "INTEGRITY_VIOLATION",
        "message": (
            "The same edit performed through the chameleon-hash trapdoor produces a "
            "collision: the chameleon hash is byte-for-byte identical, so the blockchain "
            "anchor still verifies. This is authorized redaction."
        ),
        "formula": "CH(m, r) = g^m · y^r mod p  →  CH(m', r') with trapdoor x",
    }

    return jsonify({
        "original_content": original,
        "modified_content": modified,
        "content_changed": original != modified,
        "tamper": scenario_tamper,
        "lawful": scenario_lawful,
    }), 200


@integrity_bp.route("/status", methods=["GET"])
@jwt_required
@roles_required("patient", "admin")
def blockchain_status():
    """Get blockchain connection status."""
    bc = _get_bc_service()
    status = bc.get_status()
    return jsonify({"blockchain": status}), 200


@integrity_bp.route("/anchors/<record_id>", methods=["GET"])
@jwt_required
@roles_required("patient", "admin")
def get_record_anchors(record_id):
    """Get all blockchain anchors for a specific record."""
    db = get_db()
    anchors = list(
        db["blockchain_anchors"].find({"resource_id": record_id}).sort("created_at", -1)
    )
    return jsonify({"anchors": anchors, "count": len(anchors)}), 200
