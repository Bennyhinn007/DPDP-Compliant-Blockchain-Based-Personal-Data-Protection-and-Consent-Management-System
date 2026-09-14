"""
Assets Blueprint — SIH 26125 Phase 3 (ADDITIVE).

Digital-asset registration (encrypted metadata off-chain). Registration itself
does not touch the chain (it only stores encrypted metadata + a keccak256 hash),
so it is available even when the chain is down. Minting an NFT for an asset is a
separate chain operation under /api/v1/nft.

Existing healthcare functionality is unaffected.
"""

import os
from flask import request, jsonify, g

from app.blueprints.assets import assets_bp
from app.extensions import get_db
from app.config import get_config
from app.services.asset_nft_service import AssetNFTService, ASSET_TYPES
from app.middleware.auth_middleware import jwt_required, roles_required
from app.utils.errors import ValidationError, NotFoundError


def _config():
    return get_config(os.environ.get("FLASK_ENV", "development"))


def _sih_enabled() -> bool:
    return bool(getattr(_config(), "SIH_FEATURES_ENABLED", True))


def _feature_guard():
    if not _sih_enabled():
        return jsonify({"error": True, "message": "SIH features are disabled", "sih_enabled": False}), 403
    return None


def _service():
    return AssetNFTService(get_db(), contract_service=None)


@assets_bp.route("/types", methods=["GET"])
@jwt_required
def asset_types():
    guard = _feature_guard()
    if guard:
        return guard
    return jsonify({"asset_types": ASSET_TYPES}), 200


@assets_bp.route("", methods=["POST"])
@assets_bp.route("/", methods=["POST"])
@jwt_required
@roles_required("admin", "doctor")  # admin (SIH ADMIN) / manager-equivalent
def register_asset():
    """
    Register a digital asset (encrypted metadata off-chain). Does NOT mint.
    Body: { "asset_type": "medical_device", "metadata": {name, description, spec, document} }
    """
    guard = _feature_guard()
    if guard:
        return guard
    data = request.get_json() or {}
    asset_type = (data.get("asset_type") or "").strip()
    metadata = data.get("metadata") or {}
    if not asset_type:
        raise ValidationError("asset_type required")
    if not isinstance(metadata, dict) or not metadata.get("name"):
        raise ValidationError("metadata.name required")

    svc = _service()
    asset = svc.register_asset(g.current_user_id, asset_type, metadata)
    return jsonify({"asset": asset}), 201


@assets_bp.route("", methods=["GET"])
@assets_bp.route("/", methods=["GET"])
@jwt_required
def list_assets():
    guard = _feature_guard()
    if guard:
        return guard
    return jsonify({"assets": _service().list_assets()}), 200


@assets_bp.route("/<asset_id>", methods=["GET"])
@jwt_required
def get_asset(asset_id):
    guard = _feature_guard()
    if guard:
        return guard
    asset = _service().get_asset(asset_id)
    if not asset:
        raise NotFoundError("Asset not found")
    return jsonify({"asset": asset}), 200
