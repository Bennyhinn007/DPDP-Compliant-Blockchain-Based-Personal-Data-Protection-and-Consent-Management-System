"""
DID Blueprint Routes — SIH 26125 Identity Extension (ADDITIVE).

New endpoints under /api/v1/did. These are NEW and do not modify the existing
`auth/` blueprint. DID authentication (`/challenge` + `/verify`) issues the SAME
JWT pair as the existing password/OAuth login by reusing AuthService.

Feature-flagged by SIH_FEATURES_ENABLED — when disabled, endpoints return 404-like
"feature disabled" so the platform behaves as the pure healthcare product.
"""

import os
from flask import request, jsonify, g

from app.blueprints.did import did_bp
from app.extensions import get_db
from app.config import get_config
from app.services.did_service import DIDService
from app.services.auth_service import AuthService
from app.middleware.auth_middleware import jwt_required, roles_required
from app.services.physical_presence_service import check_optional_physical_presence
from app.utils.errors import ValidationError, AuthenticationError, NotFoundError


def _config():
    return get_config(os.environ.get("FLASK_ENV", "development"))


def _sih_enabled() -> bool:
    return bool(getattr(_config(), "SIH_FEATURES_ENABLED", True))


def _did_service():
    return DIDService(get_db(), _config())


def _feature_guard():
    """Return a 403 response if the SIH layer is disabled, else None."""
    if not _sih_enabled():
        return jsonify({
            "error": True,
            "message": "SIH identity features are disabled",
            "sih_enabled": False,
        }), 403
    return None


@did_bp.route("/health", methods=["GET"])
def did_health():
    """Health check for the DID service."""
    return jsonify({"status": "did service ready", "sih_enabled": _sih_enabled()}), 200


@did_bp.route("", methods=["POST"])
@did_bp.route("/", methods=["POST"])
@jwt_required
def create_did():
    """
    Create a DID for the current authenticated user (additional identity layer).

    Body: { "public_key": "0x04..." }  (client-generated; private key stays client-side)
    """
    guard = _feature_guard()
    if guard:
        return guard

    data = request.get_json() or {}
    public_key = (data.get("public_key") or "").strip()
    if not public_key:
        raise ValidationError("public_key required")

    svc = _did_service()
    try:
        doc = svc.register_did(g.current_user_id, public_key)
    except ValueError as e:
        raise ValidationError(str(e))

    # Best-effort on-chain registration. DID creation is valid off-chain even if
    # the chain is unavailable (graceful degradation) — this never blocks.
    on_chain = {"attempted": False}
    try:
        from app.services.contract_service import ContractService
        from app.extensions import get_web3
        cs = ContractService(get_web3(), _config())
        if cs.available:
            on_chain = {"attempted": True, **cs.register_identity(doc["_id"], doc["pub_key_hash"])}
            if on_chain.get("ok") and on_chain.get("tx_hash"):
                get_db()["dids"].update_one(
                    {"_id": doc["_id"]}, {"$set": {"register_tx": on_chain["tx_hash"]}}
                )
    except Exception:
        on_chain = {"attempted": True, "ok": False, "reason": "chain_error"}

    return jsonify({
        "did": doc["_id"],
        "did_hash": doc["did_hash"],
        "pub_key_hash": doc["pub_key_hash"],
        "address": doc["address"],
        "status": doc["status"],
        "did_document": doc["did_document"],
        "on_chain": on_chain,
    }), 201


@did_bp.route("/me", methods=["GET"])
@jwt_required
def my_did():
    """Return the current user's DID (if any)."""
    guard = _feature_guard()
    if guard:
        return guard
    svc = _did_service()
    doc = svc.get_did_for_user(g.current_user_id)
    if not doc:
        return jsonify({"did": None}), 200
    return jsonify({
        "did": doc["_id"],
        "did_hash": doc["did_hash"],
        "address": doc["address"],
        "status": doc["status"],
        "sih_role": doc.get("sih_role"),
    }), 200


@did_bp.route("/<path:did>", methods=["GET"])
@jwt_required
def resolve_did(did):
    """Resolve a DID document."""
    guard = _feature_guard()
    if guard:
        return guard
    svc = _did_service()
    doc = svc.resolve_did(did)
    if not doc:
        raise NotFoundError("DID not found")
    return jsonify({
        "did": doc["_id"],
        "status": doc["status"],
        "did_document": doc["did_document"],
        "verified": svc.is_verified(did),
    }), 200


@did_bp.route("/<path:did>/revoke", methods=["POST"])
@jwt_required
@roles_required("admin", "dpo")
def revoke_did(did):
    """Admin/DPO: revoke a DID (subsequent DID auth fails)."""
    guard = _feature_guard()
    if guard:
        return guard
    # Optional high-risk gate (OFF by default; never affects healthcare).
    gate = check_optional_physical_presence(get_db(), g.current_user_id, _config().SIH_RFID_GATE_ENABLED)
    if gate:
        return gate
    svc = _did_service()
    if not svc.resolve_did(did):
        raise NotFoundError("DID not found")
    svc.revoke_did(did)
    return jsonify({"did": did, "status": "revoked"}), 200


@did_bp.route("/challenge", methods=["POST"])
def did_challenge():
    """
    Public: issue a single-use challenge nonce for DID login.
    Body: { "did": "did:rakshaid:..." }
    """
    guard = _feature_guard()
    if guard:
        return guard
    data = request.get_json() or {}
    did = (data.get("did") or "").strip()
    if not did:
        raise ValidationError("did required")
    svc = _did_service()
    try:
        challenge = svc.create_challenge(did)
    except ValueError as e:
        raise ValidationError(str(e))
    return jsonify(challenge), 200


@did_bp.route("/verify", methods=["POST"])
def did_verify():
    """
    Public: verify an EIP-191 signature over the challenge and, on success,
    issue the SAME JWT pair as the existing login (reusing AuthService).

    Body: { "did": ..., "nonce": ..., "signature": "0x..." }

    Requires the DID to be linked to an existing user_id (per spec R3.7).
    """
    guard = _feature_guard()
    if guard:
        return guard

    data = request.get_json() or {}
    did = (data.get("did") or "").strip()
    nonce = (data.get("nonce") or "").strip()
    signature = (data.get("signature") or "").strip()
    if not (did and nonce and signature):
        raise ValidationError("did, nonce, and signature are required")

    svc = _did_service()
    try:
        did_doc = svc.verify_signature(did, nonce, signature)
    except ValueError as e:
        raise AuthenticationError(str(e))

    user_id = did_doc.get("user_id")
    if not user_id:
        raise AuthenticationError("DID is not linked to a user account")

    # Optional second factor: require a recent RFID physical-presence tap.
    # The DID signature above proves possession of the private key (factor 1);
    # the RFID tap proves physical presence (factor 2). OFF by default so DID
    # login works without hardware; when SIH_DID_LOGIN_REQUIRE_RFID is enabled,
    # a remote attacker holding a stolen key still cannot log in without the card.
    if getattr(_config(), "SIH_DID_LOGIN_REQUIRE_RFID", False):
        from app.services.physical_presence_service import PhysicalPresenceService
        presence = PhysicalPresenceService(get_db()).is_physically_present(user_id)
        if not presence.get("present"):
            return jsonify({
                "error": True,
                "message": "Second factor required. Tap your RFID card, then sign in with your DID again.",
                "requires_physical_verification": True,
                "reason": presence.get("reason", "No physical verification on record"),
            }), 403

    # Reuse the existing auth pipeline to mint the SAME JWT pair as login.
    auth_service = AuthService(get_db(), _config())
    user = auth_service.users.find_one({"_id": user_id})
    if not user:
        raise AuthenticationError("Linked user account not found")
    if user.get("status") not in ("active", None):
        raise AuthenticationError("Account is not active")

    access_token = auth_service._generate_access_token(user)
    refresh_token = auth_service._generate_refresh_token(user)

    # Audit: DID login (reuse existing audit service).
    try:
        from app.services.audit_service import AuditService
        AuditService(get_db()).log_event(
            actor_id=user["_id"],
            actor_role=user["role"],
            action_type="login",
            resource_type="auth",
            resource_id=user["_id"],
            reason="User login via DID cryptographic identity",
            details={"provider": "did", "did": did},
            source_ip=request.remote_addr,
        )
    except Exception:
        pass  # audit is best-effort; never blocks login

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(_config().JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
        "user": auth_service._sanitize_user(user),
        "did": did,
    }), 200
