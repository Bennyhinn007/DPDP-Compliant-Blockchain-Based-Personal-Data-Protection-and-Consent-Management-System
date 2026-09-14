"""
Roles Blueprint — SIH 26125 (ADDITIVE).

Blockchain-enforced SIH role management (ADMIN/MANAGER/AUDITOR/USER) under
/api/v1/roles. Dual enforcement:
  - Application layer: @jwt_required + @roles_required("admin") (existing RBAC)
  - Blockchain layer:  PlatformAccessControl.grantSIHRole / revokeSIHRole

Chain-availability behavior (per spec):
  - Read-only (matrix, check): HTTP 200 with chain_available flag; never blocks.
  - Critical writes (grant/revoke): fail closed with HTTP 503 if chain unavailable.

Existing healthcare roles (patient/doctor/pharmacy_staff/dpo/admin) are NOT
renamed or affected. SIH roles are an additional, on-chain layer.
"""

import os
from flask import request, jsonify, g

from app.blueprints.roles import roles_bp
from app.extensions import get_db, get_web3
from app.config import get_config
from app.services.contract_service import ContractService
from app.services.did_service import DIDService
from app.middleware.auth_middleware import jwt_required, roles_required
from app.utils.constants import SIHRole
from app.utils.errors import ValidationError


def _config():
    return get_config(os.environ.get("FLASK_ENV", "development"))


def _sih_enabled() -> bool:
    return bool(getattr(_config(), "SIH_FEATURES_ENABLED", True))


def _contract_service():
    return ContractService(get_web3(), _config())


def _feature_guard():
    if not _sih_enabled():
        return jsonify({"error": True, "message": "SIH features are disabled", "sih_enabled": False}), 403
    return None


# Permission matrix (static reference for the UI / access checks).
PERMISSION_MATRIX = {
    "create_identity":   {"admin": True,  "manager": False, "auditor": False, "user": False},
    "assign_roles":      {"admin": True,  "manager": False, "auditor": False, "user": False},
    "mint_nft":          {"admin": True,  "manager": False, "auditor": False, "user": False},
    "assign_asset":      {"admin": True,  "manager": True,  "auditor": False, "user": False},
    "transfer_asset":    {"admin": True,  "manager": True,  "auditor": False, "user": True},
    "verify_ownership":  {"admin": True,  "manager": True,  "auditor": True,  "user": True},
    "view_audit":        {"admin": True,  "manager": True,  "auditor": True,  "user": False},
    "revoke_identity":   {"admin": True,  "manager": False, "auditor": False, "user": False},
}


@roles_bp.route("/matrix", methods=["GET"])
@jwt_required
def role_matrix():
    """Read-only: the SIH permission matrix + on-chain availability status."""
    guard = _feature_guard()
    if guard:
        return guard
    cs = _contract_service()
    return jsonify({
        "roles": [r.value for r in SIHRole],
        "matrix": PERMISSION_MATRIX,
        "chain_available": cs.status()["available"],
    }), 200


@roles_bp.route("/grant", methods=["POST"])
@jwt_required
@roles_required("admin")
def grant_role():
    """
    Admin grants a SIH role to a DID (dual-enforced). Critical write: fails closed
    (HTTP 503) if the chain/contracts are unavailable.
    Body: { "did": "did:rakshaid:...", "role": "manager" }
    """
    guard = _feature_guard()
    if guard:
        return guard

    data = request.get_json() or {}
    did = (data.get("did") or "").strip()
    role = (data.get("role") or "").strip().lower()
    if not did or not role:
        raise ValidationError("did and role are required")
    if role not in [r.value for r in SIHRole]:
        raise ValidationError(f"role must be one of {[r.value for r in SIHRole]}")

    # Application-layer check already passed (@roles_required admin). Now the
    # blockchain layer.
    cs = _contract_service()
    if not cs.available:
        return jsonify({
            "error": True,
            "message": "Blockchain unavailable — role change not committed (fail-closed).",
            "chain_available": False,
        }), 503

    # Verify the DID exists off-chain before granting.
    db = get_db()
    did_svc = DIDService(db, _config())
    if not did_svc.resolve_did(did):
        raise ValidationError("Unknown DID")

    result = cs.grant_role(did, role)
    if not result.get("ok"):
        return jsonify({"error": True, "message": f"On-chain grant failed: {result.get('reason')}"}), 502

    # Mirror the on-chain assignment off-chain (cache) additively.
    db["role_assignments"].insert_one({
        "did": did, "sih_role": role, "granted_by": g.current_user_id,
        "grant_tx": result.get("tx_hash"), "status": "active",
        "created_at": _now_iso(),
    })
    return jsonify({"did": did, "role": role, "tx_hash": result.get("tx_hash"), "chain_available": True}), 200


@roles_bp.route("/revoke", methods=["POST"])
@jwt_required
@roles_required("admin")
def revoke_role():
    """Admin revokes a SIH role from a DID (dual-enforced; fail-closed on chain-down)."""
    guard = _feature_guard()
    if guard:
        return guard

    data = request.get_json() or {}
    did = (data.get("did") or "").strip()
    role = (data.get("role") or "").strip().lower()
    if not did or not role:
        raise ValidationError("did and role are required")

    cs = _contract_service()
    if not cs.available:
        return jsonify({
            "error": True,
            "message": "Blockchain unavailable — role change not committed (fail-closed).",
            "chain_available": False,
        }), 503

    result = cs.revoke_role(did, role)
    if not result.get("ok"):
        return jsonify({"error": True, "message": f"On-chain revoke failed: {result.get('reason')}"}), 502

    get_db()["role_assignments"].update_many(
        {"did": did, "sih_role": role}, {"$set": {"status": "revoked"}}
    )
    return jsonify({"did": did, "role": role, "tx_hash": result.get("tx_hash"), "chain_available": True}), 200


@roles_bp.route("/check", methods=["GET"])
@jwt_required
def check_role():
    """
    Read-only dual-authorization check for a DID + role. Returns 200 even when
    chain is down (chain_available:false), serving the off-chain cache.
    Query: ?did=...&role=manager
    """
    guard = _feature_guard()
    if guard:
        return guard
    did = (request.args.get("did") or "").strip()
    role = (request.args.get("role") or "").strip().lower()
    if not did or not role:
        raise ValidationError("did and role query params are required")

    cs = _contract_service()
    on_chain = cs.did_has_role(did, role)  # None if chain unavailable
    # Off-chain cache fallback.
    cached = get_db()["role_assignments"].find_one({"did": did, "sih_role": role, "status": "active"})
    return jsonify({
        "did": did,
        "role": role,
        "on_chain": on_chain,
        "cached": bool(cached),
        "chain_available": on_chain is not None,
    }), 200


def _now_iso():
    from app.utils.helpers import utc_now
    return utc_now()
