"""
NFT Blueprint — SIH 26125 Phase 3 (ADDITIVE).

ERC-721 digital-asset lifecycle under /api/v1/nft. Dual authorization:
  - Application layer: @jwt_required + @roles_required (existing RBAC)
  - Blockchain layer:  AssetNFT contract (onlyAdmin / onlyAdminOrManager)

Chain-availability (per spec):
  - Critical writes (mint/assign/transfer): fail closed with HTTP 503 when chain down.
  - Reads (verify/list): HTTP 200 with chain_available flag; serve cached data.

Healthcare records are NOT NFTs and are unaffected.
"""

import os
from flask import request, jsonify, g

from app.blueprints.nft import nft_bp
from app.extensions import get_db, get_web3
from app.config import get_config
from app.services.contract_service import ContractService
from app.services.asset_nft_service import AssetNFTService
from app.services.chain_audit import record_chain_event
from app.middleware.auth_middleware import jwt_required, roles_required
from app.utils.errors import ValidationError


def _config():
    return get_config(os.environ.get("FLASK_ENV", "development"))


def _sih_enabled() -> bool:
    return bool(getattr(_config(), "SIH_FEATURES_ENABLED", True))


def _feature_guard():
    if not _sih_enabled():
        return jsonify({"error": True, "message": "SIH features are disabled", "sih_enabled": False}), 403
    return None


def _service():
    cs = ContractService(get_web3(), _config())
    return AssetNFTService(get_db(), contract_service=cs), cs


def _chain_down_response():
    return jsonify({
        "error": True,
        "message": "Blockchain unavailable — operation not committed (fail-closed).",
        "chain_available": False,
    }), 503


@nft_bp.route("/mint", methods=["POST"])
@jwt_required
@roles_required("admin")
def mint_nft():
    """Admin mints an NFT for a registered asset to a DID. Fail-closed if chain down."""
    guard = _feature_guard()
    if guard:
        return guard
    data = request.get_json() or {}
    asset_id = (data.get("asset_id") or "").strip()
    owner_did = (data.get("owner_did") or "").strip()
    if not asset_id or not owner_did:
        raise ValidationError("asset_id and owner_did are required")

    svc, cs = _service()
    if not cs.nft_available:
        return _chain_down_response()

    result = svc.mint(asset_id, owner_did)
    if not result.get("ok"):
        return jsonify({"error": True, "message": f"Mint failed: {result.get('reason')}"}), 502

    record_chain_event(
        get_db(), event_name="AssetMinted", contract="AssetNFT",
        tx_hash=result.get("tx_hash"),
        args={"token_id": result.get("token_id"), "owner_did": owner_did, "asset_id": asset_id},
        actor_id=g.current_user_id, actor_role="admin",
        reason="NFT minted", source_ip=request.remote_addr,
    )
    return jsonify({"token_id": result.get("token_id"), "tx_hash": result.get("tx_hash"), "chain_available": True}), 201


@nft_bp.route("/<int:token_id>/assign", methods=["POST"])
@jwt_required
@roles_required("admin", "doctor")  # admin or manager-equivalent
def assign_nft(token_id):
    guard = _feature_guard()
    if guard:
        return guard
    data = request.get_json() or {}
    to_did = (data.get("to_did") or "").strip()
    if not to_did:
        raise ValidationError("to_did required")

    svc, cs = _service()
    if not cs.nft_available:
        return _chain_down_response()

    result = svc.assign(token_id, to_did)
    if not result.get("ok"):
        return jsonify({"error": True, "message": f"Assign failed: {result.get('reason')}"}), 502

    record_chain_event(
        get_db(), event_name="AssetAssigned", contract="AssetNFT",
        tx_hash=result.get("tx_hash"), args={"token_id": token_id, "to_did": to_did},
        actor_id=g.current_user_id, actor_role="admin",
        reason="NFT assigned", source_ip=request.remote_addr,
    )
    return jsonify({"token_id": token_id, "tx_hash": result.get("tx_hash"), "chain_available": True}), 200


@nft_bp.route("/<int:token_id>/transfer", methods=["POST"])
@jwt_required
@roles_required("admin", "doctor")
def transfer_nft(token_id):
    guard = _feature_guard()
    if guard:
        return guard
    data = request.get_json() or {}
    to_did = (data.get("to_did") or "").strip()
    if not to_did:
        raise ValidationError("to_did required")

    svc, cs = _service()
    if not cs.nft_available:
        return _chain_down_response()

    result = svc.transfer(token_id, to_did)
    if not result.get("ok"):
        return jsonify({"error": True, "message": f"Transfer failed: {result.get('reason')}"}), 502

    record_chain_event(
        get_db(), event_name="AssetTransferred", contract="AssetNFT",
        tx_hash=result.get("tx_hash"), args={"token_id": token_id, "to_did": to_did},
        actor_id=g.current_user_id, actor_role="admin",
        reason="NFT transferred", source_ip=request.remote_addr,
    )
    return jsonify({"token_id": token_id, "tx_hash": result.get("tx_hash"), "chain_available": True}), 200


@nft_bp.route("/<int:token_id>/verify", methods=["GET"])
@jwt_required
def verify_nft(token_id):
    """Read-only ownership + metadata-hash verification. Degrades gracefully."""
    guard = _feature_guard()
    if guard:
        return guard
    svc, _ = _service()
    return jsonify(svc.verify_ownership(token_id)), 200


@nft_bp.route("", methods=["GET"])
@nft_bp.route("/", methods=["GET"])
@jwt_required
def list_nfts():
    """List NFTs, optionally by owner DID (?owner_did=...). Read-only."""
    guard = _feature_guard()
    if guard:
        return guard
    owner_did = request.args.get("owner_did")
    svc, _ = _service()
    return jsonify({"nfts": svc.list_nfts(owner_did)}), 200
