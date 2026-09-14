"""
Blockchain Blueprint Routes.

Provides blockchain status and anchor lookup endpoints.
"""

from flask import jsonify, g

from app.blueprints.blockchain import blockchain_bp
from app.extensions import get_db, get_web3
from app.services.blockchain_service import BlockchainService
from app.middleware.auth_middleware import jwt_required, roles_required


@blockchain_bp.route("/health", methods=["GET"])
def blockchain_health():
    return jsonify({"status": "blockchain service ready"}), 200


@blockchain_bp.route("/status", methods=["GET"])
@jwt_required
@roles_required("admin")
def blockchain_status():
    """Get Ganache connection status (admin only)."""
    bc = BlockchainService(get_db(), get_web3())
    return jsonify({"blockchain": bc.get_status()}), 200


@blockchain_bp.route("/anchors/patient", methods=["GET"])
@jwt_required
@roles_required("patient")
def my_anchors():
    """Get all blockchain anchors for current patient."""
    bc = BlockchainService(get_db(), get_web3())
    anchors = bc.get_anchors_for_patient(g.current_user_id)
    return jsonify({"anchors": anchors, "count": len(anchors)}), 200


# ─────────────────────────────────────────────────────────────────────
# LIVE CHAMELEON HASH COLLISION DEMO
# ─────────────────────────────────────────────────────────────────────

@blockchain_bp.route("/chameleon/demo", methods=["POST"])
@jwt_required
def chameleon_collision_demo():
    """
    Run a REAL chameleon hash collision on demand for demonstration.

    Takes original + new content, generates a genuine discrete-log
    chameleon-hash trapdoor collision, and returns the cryptographic
    values proving both contents share an identical hash.

    Body:
        {
          "original": "some original text",
          "modified": "some corrected text"
        }
    """
    from flask import request
    from app.services.chameleon_hash_service import ChameleonHashSimulator

    data = request.get_json(silent=True) or {}
    original = str(data.get("original", "")).strip()
    modified = str(data.get("modified", "")).strip()

    if not original or not modified:
        return jsonify({
            "error": True,
            "message": "Both 'original' and 'modified' content are required.",
        }), 400

    proof = ChameleonHashSimulator.generate_chameleon_collision(original, modified)

    return jsonify({
        "original_content": original,
        "modified_content": modified,
        "content_changed": original != modified,
        "hash_identical": proof["verified"],
        "proof": proof,
    }), 200


# ─────────────────────────────────────────────────────────────────────
# SIH 26125: ON-CHAIN CONTRACT EVENT CACHE (ADDITIVE)
# ─────────────────────────────────────────────────────────────────────

@blockchain_bp.route("/events", methods=["GET"])
@jwt_required
@roles_required("admin", "dpo")
def chain_events():
    """
    List cached SIH smart-contract events (identity/role/NFT/ownership) for the
    Blockchain Explorer + on-chain audit view. Read-only; served from the
    chain_events cache, so it works regardless of live chain availability.

    Query: ?limit=100
    """
    db = get_db()
    try:
        limit = min(int(__import__("flask").request.args.get("limit", 100)), 500)
    except (ValueError, TypeError):
        limit = 100
    events = list(db["chain_events"].find().sort("indexed_at", -1).limit(limit))
    return jsonify({"events": events, "count": len(events)}), 200
