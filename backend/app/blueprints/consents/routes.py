"""
Consents Blueprint Routes.

Full DPDP consent lifecycle: grant, list, get, modify, withdraw, receipts.
"""

from flask import request, jsonify, g

from app.blueprints.consents import consents_bp
from app.extensions import get_db
from app.services.consent_service import ConsentService
from app.services.patient_service import PatientService
from app.services.audit_service import AuditService
from app.middleware.auth_middleware import jwt_required, roles_required
from app.utils.errors import ValidationError


def _get_consent_service():
    return ConsentService(get_db())


def _get_patient_id(user_id: str) -> str:
    """Resolve patient_id from user_id."""
    svc = PatientService(get_db())
    patient = svc.get_patient_by_user_id(user_id)
    return patient["_id"]


def _validate_optional_did(value, field_name: str):
    """
    Validate an OPTIONAL SIH DID reference on a consent.

    Returns None when absent/empty (the common case — consent works without any
    DID). When present it must be a non-empty `did:rakshaid:` string; otherwise a
    ValidationError is raised so malformed identifiers are rejected early.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if not value.startswith("did:rakshaid:"):
        raise ValidationError(f"{field_name} must be a valid 'did:rakshaid:' identifier")
    return value


# ─────────────────────────────────────────────────────────────────────
# GRANT
# ─────────────────────────────────────────────────────────────────────

@consents_bp.route("/grant", methods=["POST"])
@jwt_required
@roles_required("patient")
def grant_consent():
    """
    Grant consent for a data processing purpose.

    Body:
        {
            "consent_type": "healthcare_treatment",
            "processing_entity_name": "Apollo Healthcare",
            "expiry_days": 365,
            "custom_scope": null
        }
    """
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")

    patient_id = _get_patient_id(g.current_user_id)
    svc = _get_consent_service()

    # Optional SIH DID bridge (nullable, additive). If provided they must be
    # well-formed rakshaid DIDs; absence changes nothing (consent works as before).
    patient_did = _validate_optional_did(data.get("patient_did"), "patient_did")
    doctor_did = _validate_optional_did(data.get("doctor_did"), "doctor_did")

    result = svc.grant_consent(
        user_id=g.current_user_id,
        patient_id=patient_id,
        consent_type=data.get("consent_type", ""),
        processing_entity_name=data.get("processing_entity_name", ""),
        expiry_days=data.get("expiry_days", 365),
        custom_scope=data.get("custom_scope"),
        patient_did=patient_did,
        doctor_did=doctor_did,
    )

    # Audit: consent grant
    audit_svc = AuditService(get_db())
    audit_svc.log_event(
        actor_id=g.current_user_id,
        actor_role="patient",
        action_type="consent_grant",
        resource_type="consents",
        resource_id=result["consent"]["_id"],
        patient_id=patient_id,
        reason=f"Consent granted: {data.get('consent_type', '')}",
        details={"consent_type": data.get("consent_type"), "entity": data.get("processing_entity_name")},
        source_ip=request.remote_addr,
    )

    # Blockchain anchoring for consent
    try:
        from app.services.blockchain_service import BlockchainService
        from app.extensions import get_web3
        import hashlib, json
        bc = BlockchainService(get_db(), get_web3())
        consent_hash = hashlib.sha256(
            json.dumps(result["consent"], sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        anchor = bc.anchor_record(
            resource_type="consents",
            resource_id=result["consent"]["_id"],
            data_hash=consent_hash,
            patient_id=patient_id,
            anchor_type="consent",
        )
        # Update consent with blockchain reference
        get_db()["consents"].update_one(
            {"_id": result["consent"]["_id"]},
            {"$set": {
                "consent_hash": consent_hash,
                "blockchain_tx_ref": anchor.get("transaction_hash"),
                "blockchain_anchor_id": anchor["_id"],
            }}
        )
        result["consent"]["blockchain_tx_ref"] = anchor.get("transaction_hash")
    except Exception:
        pass  # Non-blocking

    return jsonify({
        "message": "Consent granted successfully",
        "consent": result["consent"],
        "receipt": result["receipt"],
    }), 201


# ─────────────────────────────────────────────────────────────────────
# LIST / GET
# ─────────────────────────────────────────────────────────────────────

@consents_bp.route("/", methods=["GET"])
@jwt_required
@roles_required("patient")
def list_consents():
    """
    List all consents for the current patient.

    Query params:
        status: Filter by status (active, withdrawn, expired)
        type: Filter by consent type
    """
    patient_id = _get_patient_id(g.current_user_id)
    svc = _get_consent_service()

    consents = svc.list_consents(
        patient_id=patient_id,
        status=request.args.get("status"),
        consent_type=request.args.get("type"),
    )

    return jsonify({"consents": consents, "count": len(consents)}), 200


@consents_bp.route("/<consent_id>", methods=["GET"])
@jwt_required
@roles_required("patient")
def get_consent(consent_id):
    """Get a single consent by ID."""
    svc = _get_consent_service()
    consent = svc.get_consent(consent_id, g.current_user_id)
    return jsonify({"consent": consent}), 200


@consents_bp.route("/active-sharing", methods=["GET"])
@jwt_required
@roles_required("patient")
def active_sharing():
    """Get all entities with active access to patient data."""
    patient_id = _get_patient_id(g.current_user_id)
    svc = _get_consent_service()
    sharing = svc.get_active_sharing(patient_id)
    return jsonify({"active_sharing": sharing, "count": len(sharing)}), 200


@consents_bp.route("/expiring-soon", methods=["GET"])
@jwt_required
@roles_required("patient")
def expiring_soon():
    """Get consents expiring within 7 days."""
    patient_id = _get_patient_id(g.current_user_id)
    svc = _get_consent_service()
    expiring = svc.get_expiring_soon(patient_id, days=7)
    return jsonify({"expiring": expiring, "count": len(expiring)}), 200


# ─────────────────────────────────────────────────────────────────────
# MODIFY
# ─────────────────────────────────────────────────────────────────────

@consents_bp.route("/<consent_id>/modify", methods=["PUT"])
@jwt_required
@roles_required("patient")
def modify_consent(consent_id):
    """
    Modify consent scope.

    Body:
        {
            "new_scope": ["medical_history", "allergies"],
            "reason": "Restricting access to fewer categories"
        }
    """
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")

    svc = _get_consent_service()
    result = svc.modify_consent(
        consent_id=consent_id,
        user_id=g.current_user_id,
        new_scope=data.get("new_scope", []),
        reason=data.get("reason", ""),
    )

    # Audit: consent modify
    patient_id = _get_patient_id(g.current_user_id)
    audit_svc = AuditService(get_db())
    audit_svc.log_event(
        actor_id=g.current_user_id,
        actor_role="patient",
        action_type="consent_modify",
        resource_type="consents",
        resource_id=consent_id,
        patient_id=patient_id,
        reason=f"Consent scope modified: {data.get('reason', '')}",
        details={"new_scope": data.get("new_scope")},
        source_ip=request.remote_addr,
    )

    return jsonify({
        "message": "Consent modified successfully",
        "consent": result["consent"],
        "receipt": result["receipt"],
    }), 200


# ─────────────────────────────────────────────────────────────────────
# WITHDRAW
# ─────────────────────────────────────────────────────────────────────

@consents_bp.route("/<consent_id>/withdraw", methods=["POST"])
@jwt_required
@roles_required("patient")
def withdraw_consent(consent_id):
    """
    Withdraw consent (immediate access revocation).

    Body (optional):
        {
            "reason": "No longer need this service"
        }
    """
    data = request.get_json(silent=True) or {}
    svc = _get_consent_service()

    result = svc.withdraw_consent(
        consent_id=consent_id,
        user_id=g.current_user_id,
        reason=data.get("reason"),
    )

    # Audit: consent withdraw
    patient_id = _get_patient_id(g.current_user_id)
    audit_svc = AuditService(get_db())
    audit_svc.log_event(
        actor_id=g.current_user_id,
        actor_role="patient",
        action_type="consent_withdraw",
        resource_type="consents",
        resource_id=consent_id,
        patient_id=patient_id,
        reason=f"Consent withdrawn: {data.get('reason', 'No reason given')}",
        details={"consent_type": result["consent"]["consent_type"]},
        severity="warning",
        source_ip=request.remote_addr,
    )

    # Blockchain anchoring for withdrawal
    try:
        from app.services.blockchain_service import BlockchainService
        from app.extensions import get_web3
        import hashlib, json
        bc = BlockchainService(get_db(), get_web3())
        withdrawal_hash = hashlib.sha256(
            json.dumps({"consent_id": consent_id, "action": "withdraw", "reason": data.get("reason")}, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        bc.anchor_record(
            resource_type="consents",
            resource_id=consent_id,
            data_hash=withdrawal_hash,
            patient_id=patient_id,
            anchor_type="consent",
        )
    except Exception:
        pass

    return jsonify({
        "message": "Consent withdrawn. Access revoked immediately.",
        "consent": result["consent"],
        "receipt": result["receipt"],
    }), 200


# ─────────────────────────────────────────────────────────────────────
# RECEIPTS
# ─────────────────────────────────────────────────────────────────────

@consents_bp.route("/receipts", methods=["GET"])
@jwt_required
@roles_required("patient")
def list_receipts():
    """List all consent receipts."""
    patient_id = _get_patient_id(g.current_user_id)
    svc = _get_consent_service()
    receipts = svc.list_receipts(patient_id)
    return jsonify({"receipts": receipts, "count": len(receipts)}), 200


@consents_bp.route("/receipts/<receipt_id>", methods=["GET"])
@jwt_required
@roles_required("patient")
def get_receipt(receipt_id):
    """Get a single consent receipt."""
    svc = _get_consent_service()
    receipt = svc.get_receipt(receipt_id, g.current_user_id)
    return jsonify({"receipt": receipt}), 200
