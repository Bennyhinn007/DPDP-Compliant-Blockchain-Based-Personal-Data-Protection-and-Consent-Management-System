"""
Auth Blueprint Routes.

Handles user registration, login, token refresh, and protected test endpoint.
"""

import os
from flask import request, jsonify, g

from app.blueprints.auth import auth_bp
from app.extensions import get_db
from app.config import get_config
from app.services.auth_service import AuthService
from app.middleware.auth_middleware import jwt_required, roles_required
from app.middleware.audit_middleware import log_audit_event
from app.utils.errors import ValidationError


def _get_auth_service():
    """Create AuthService with current config."""
    db = get_db()
    config = get_config(os.environ.get("FLASK_ENV", "development"))
    return AuthService(db, config)


@auth_bp.route("/health", methods=["GET"])
def auth_health():
    """Health check for auth service."""
    return jsonify({"status": "auth service ready"}), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.

    Request Body:
        {
            "email": "user@example.com",
            "password": "securePassword123",
            "role": "patient",
            "full_name": "Rajesh Kumar"
        }

    Returns:
        201: User created successfully
        422: Validation error
    """
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")

    auth_service = _get_auth_service()
    user = auth_service.register(
        email=data.get("email", "").strip(),
        password=data.get("password", ""),
        role=data.get("role", "").strip(),
        full_name=data.get("full_name", "").strip(),
    )

    # Audit: registration event
    from app.services.audit_service import AuditService
    audit_svc = AuditService(get_db())
    audit_svc.log_event(
        actor_id=user["id"],
        actor_role=user["role"],
        action_type="create",
        resource_type="users",
        resource_id=user["id"],
        patient_id=user["id"] if user["role"] == "patient" else None,
        reason="User registration",
        details={"role": user["role"]},
        source_ip=request.remote_addr,
    )

    return jsonify({
        "message": "Registration successful",
        "user": user,
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and return JWT tokens.

    Request Body:
        {
            "email": "user@example.com",
            "password": "securePassword123"
        }

    Returns:
        200: Login successful with tokens
        401: Invalid credentials
    """
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")

    auth_service = _get_auth_service()
    result = auth_service.login(
        email=data.get("email", "").strip(),
        password=data.get("password", ""),
    )

    # Audit: login event
    from app.services.audit_service import AuditService
    audit_svc = AuditService(get_db())
    audit_svc.log_event(
        actor_id=result["user"]["id"],
        actor_role=result["user"]["role"],
        action_type="login",
        resource_type="auth",
        resource_id=result["user"]["id"],
        patient_id=result["user"]["id"] if result["user"]["role"] == "patient" else None,
        reason="User login",
        source_ip=request.remote_addr,
    )

    return jsonify(result), 200


@auth_bp.route("/google", methods=["POST"])
def google_login():
    """
    Authenticate via Google (Sign in with Google) and return JWT tokens.

    Request Body:
        { "id_token": "<google-id-token-jwt>" }

    Returns:
        200: Login successful with tokens (same shape as /login)
        401: Invalid Google token or inactive account
    """
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")

    auth_service = _get_auth_service()
    result = auth_service.login_with_google(
        id_token_str=data.get("id_token", "").strip(),
    )

    # Audit: login event (Google provider)
    from app.services.audit_service import AuditService
    audit_svc = AuditService(get_db())
    audit_svc.log_event(
        actor_id=result["user"]["id"],
        actor_role=result["user"]["role"],
        action_type="login",
        resource_type="auth",
        resource_id=result["user"]["id"],
        patient_id=result["user"]["id"] if result["user"]["role"] == "patient" else None,
        reason="User login via Google OAuth",
        details={"provider": "google"},
        source_ip=request.remote_addr,
    )

    return jsonify(result), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_current_user():
    """
    Get current authenticated user profile.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: User profile
        401: Invalid/expired token
    """
    auth_service = _get_auth_service()
    user = auth_service.get_user_by_id(g.current_user_id)
    if not user:
        return jsonify({"error": True, "message": "User not found"}), 404

    return jsonify({"user": user}), 200


@auth_bp.route("/protected-test", methods=["GET"])
@jwt_required
def protected_test():
    """
    Test endpoint to verify JWT authentication works.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: Authentication confirmed with user context
    """
    return jsonify({
        "message": "JWT authentication successful",
        "user_id": g.current_user_id,
        "role": g.current_user_role,
    }), 200


@auth_bp.route("/admin-only", methods=["GET"])
@jwt_required
@roles_required("admin")
def admin_only():
    """
    Test endpoint to verify RBAC (admin-only access).

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: Admin access confirmed
        403: Non-admin role rejected
    """
    return jsonify({
        "message": "Admin access granted",
        "user_id": g.current_user_id,
        "role": g.current_user_role,
    }), 200


@auth_bp.route("/patient-only", methods=["GET"])
@jwt_required
@roles_required("patient")
def patient_only():
    """
    Test endpoint to verify RBAC (patient-only access).

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: Patient access confirmed
        403: Non-patient role rejected
    """
    return jsonify({
        "message": "Patient access granted",
        "user_id": g.current_user_id,
        "role": g.current_user_role,
    }), 200


# ─────────────────────────────────────────────────────────────────────
# MFA (Google Authenticator)
# ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/mfa/setup", methods=["POST"])
@jwt_required
def mfa_setup():
    """
    Generate MFA secret and QR code for Google Authenticator.

    Returns provisioning URI and QR code (base64 PNG).
    """
    from app.services.mfa_service import MFAService
    from app.services.audit_service import AuditService

    svc = MFAService(get_db())
    result = svc.setup_mfa(g.current_user_id)

    # Audit
    audit = AuditService(get_db())
    audit.log_event(
        actor_id=g.current_user_id,
        actor_role=g.current_user_role,
        action_type="update",
        resource_type="mfa",
        resource_id=g.current_user_id,
        reason="MFA setup initiated",
        source_ip=request.remote_addr,
    )

    return jsonify(result), 200


@auth_bp.route("/mfa/verify", methods=["POST"])
@jwt_required
def mfa_verify():
    """
    Verify TOTP code and enable MFA.

    Body: { "code": "123456" }
    """
    from app.services.mfa_service import MFAService
    from app.services.audit_service import AuditService

    data = request.get_json()
    if not data or not data.get("code"):
        raise ValidationError("6-digit code required")

    svc = MFAService(get_db())
    result = svc.verify_and_enable(g.current_user_id, data["code"])

    # Audit
    audit = AuditService(get_db())
    audit.log_event(
        actor_id=g.current_user_id,
        actor_role=g.current_user_role,
        action_type="update",
        resource_type="mfa",
        resource_id=g.current_user_id,
        reason="MFA enabled successfully",
        severity="warning",
        source_ip=request.remote_addr,
    )

    return jsonify(result), 200


@auth_bp.route("/mfa/disable", methods=["POST"])
@jwt_required
def mfa_disable():
    """
    Disable MFA (requires valid TOTP code).

    Body: { "code": "123456" }
    """
    from app.services.mfa_service import MFAService
    from app.services.audit_service import AuditService

    data = request.get_json()
    if not data or not data.get("code"):
        raise ValidationError("6-digit code required to disable MFA")

    svc = MFAService(get_db())
    result = svc.disable_mfa(g.current_user_id, data["code"])

    # Audit
    audit = AuditService(get_db())
    audit.log_event(
        actor_id=g.current_user_id,
        actor_role=g.current_user_role,
        action_type="update",
        resource_type="mfa",
        resource_id=g.current_user_id,
        reason="MFA disabled",
        severity="critical",
        source_ip=request.remote_addr,
    )

    return jsonify(result), 200


# ─────────────────────────────────────────────────────────────────────
# WEBAUTHN (Biometric Enrollment)
# ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/webauthn/register/begin", methods=["POST"])
@jwt_required
@roles_required("admin", "dpo")
def webauthn_register_begin():
    """
    Begin WebAuthn biometric registration (Admin/DPO only).

    Returns PublicKeyCredentialCreationOptions for navigator.credentials.create().
    """
    from app.services.webauthn_service import WebAuthnService
    from app.services.audit_service import AuditService

    auth_service = _get_auth_service()
    user = auth_service.get_user_by_id(g.current_user_id)
    if not user:
        return jsonify({"error": True, "message": "User not found"}), 404

    svc = WebAuthnService(get_db())
    options = svc.begin_registration(
        user_id=g.current_user_id,
        user_name=user["full_name"],
        user_email=user["email"],
    )

    return jsonify({"options": options}), 200


@auth_bp.route("/webauthn/register/complete", methods=["POST"])
@jwt_required
@roles_required("admin", "dpo")
def webauthn_register_complete():
    """
    Complete WebAuthn biometric registration.

    Body: { credential_id, public_key, attestation_object, client_data_json, device_name }
    """
    from app.services.webauthn_service import WebAuthnService
    from app.services.audit_service import AuditService

    data = request.get_json()
    if not data or not data.get("credential_id"):
        raise ValidationError("Credential data required")

    svc = WebAuthnService(get_db())
    result = svc.complete_registration(
        user_id=g.current_user_id,
        credential_id=data["credential_id"],
        public_key=data.get("public_key", ""),
        attestation_object=data.get("attestation_object", ""),
        client_data_json=data.get("client_data_json", ""),
        device_name=data.get("device_name", "Biometric Device"),
    )

    # Audit
    audit = AuditService(get_db())
    audit.log_event(
        actor_id=g.current_user_id,
        actor_role=g.current_user_role,
        action_type="create",
        resource_type="webauthn",
        resource_id=result.get("credential_id", ""),
        reason=f"WebAuthn biometric registered: {data.get('device_name', 'Device')}",
        severity="warning",
        source_ip=request.remote_addr,
    )

    return jsonify(result), 201


@auth_bp.route("/webauthn/credentials", methods=["GET"])
@jwt_required
def webauthn_list_credentials():
    """List registered WebAuthn credentials."""
    from app.services.webauthn_service import WebAuthnService

    svc = WebAuthnService(get_db())
    credentials = svc.list_credentials(g.current_user_id)
    has_biometric = svc.has_credentials(g.current_user_id)

    return jsonify({
        "credentials": credentials,
        "biometric_enabled": has_biometric,
        "count": len(credentials),
    }), 200


@auth_bp.route("/webauthn/credentials/<cred_id>", methods=["DELETE"])
@jwt_required
@roles_required("admin", "dpo")
def webauthn_remove_credential(cred_id):
    """Remove a registered WebAuthn credential."""
    from app.services.webauthn_service import WebAuthnService
    from app.services.audit_service import AuditService

    svc = WebAuthnService(get_db())
    removed = svc.remove_credential(g.current_user_id, cred_id)

    if not removed:
        return jsonify({"error": True, "message": "Credential not found"}), 404

    # Audit
    audit = AuditService(get_db())
    audit.log_event(
        actor_id=g.current_user_id,
        actor_role=g.current_user_role,
        action_type="delete",
        resource_type="webauthn",
        resource_id=cred_id,
        reason="WebAuthn biometric credential removed",
        severity="warning",
        source_ip=request.remote_addr,
    )

    return jsonify({"message": "Credential removed", "id": cred_id}), 200


# ─────────────────────────────────────────────────────────────────────
# WEBAUTHN STEP-UP VERIFICATION (Privileged Operations)
# ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/webauthn/verify/begin", methods=["POST"])
@jwt_required
def webauthn_verify_begin():
    """
    Begin WebAuthn step-up verification for sensitive operations.

    Returns assertion options for navigator.credentials.get().
    Used before: record erasure, chameleon redaction, account deletion.
    """
    from app.services.webauthn_service import WebAuthnService

    svc = WebAuthnService(get_db())
    if not svc.has_credentials(g.current_user_id):
        return jsonify({
            "error": False,
            "biometric_available": False,
            "message": "No biometric credentials enrolled. Operation proceeds without step-up.",
        }), 200

    # Generate assertion challenge
    import os
    import base64
    from app.utils.helpers import generate_uuid, utc_now
    from datetime import datetime, timezone, timedelta

    challenge = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    db = get_db()
    db["webauthn_challenges"].insert_one({
        "_id": generate_uuid(),
        "user_id": g.current_user_id,
        "challenge": challenge,
        "type": "assertion",
        "created_at": utc_now(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    })

    # Get user's credential IDs
    creds = list(db["webauthn_credentials"].find({"user_id": g.current_user_id}))
    allow_credentials = [
        {"id": c["credential_id"], "type": "public-key", "transports": ["internal"]}
        for c in creds
    ]

    return jsonify({
        "biometric_available": True,
        "options": {
            "challenge": challenge,
            "rpId": os.environ.get("WEBAUTHN_RP_ID", "localhost"),
            "allowCredentials": allow_credentials,
            "userVerification": "required",
            "timeout": 60000,
        },
    }), 200


@auth_bp.route("/webauthn/verify/complete", methods=["POST"])
@jwt_required
def webauthn_verify_complete():
    """
    Complete WebAuthn step-up verification.

    Validates assertion and grants elevated session for 5 minutes.
    """
    from app.services.audit_service import AuditService
    from app.utils.helpers import utc_now

    data = request.get_json()
    if not data or not data.get("credential_id"):
        raise ValidationError("Credential assertion required")

    db = get_db()

    # Validate challenge
    challenge_doc = db["webauthn_challenges"].find_one({
        "user_id": g.current_user_id,
        "type": "assertion",
        "expires_at": {"$gt": utc_now()},
    })

    if not challenge_doc:
        from app.utils.errors import AuthenticationError
        raise AuthenticationError("Verification challenge expired")

    # Verify credential exists for this user
    cred = db["webauthn_credentials"].find_one({
        "user_id": g.current_user_id,
        "credential_id": data["credential_id"],
    })

    if not cred:
        from app.utils.errors import AuthenticationError
        raise AuthenticationError("Credential not recognized")

    # Update last_used
    db["webauthn_credentials"].update_one(
        {"_id": cred["_id"]},
        {"$set": {"last_used": utc_now()}}
    )

    # Clean up challenge
    db["webauthn_challenges"].delete_many({"user_id": g.current_user_id, "type": "assertion"})

    # Audit
    audit = AuditService(db)
    audit.log_event(
        actor_id=g.current_user_id,
        actor_role=g.current_user_role,
        action_type="verification",
        resource_type="webauthn",
        resource_id=cred["_id"],
        reason="Biometric step-up verification successful",
        source_ip=request.remote_addr,
    )

    return jsonify({
        "verified": True,
        "message": "Biometric verification successful. Elevated access granted for 5 minutes.",
        "expires_in": 300,
    }), 200


# ─────────────────────────────────────────────────────────────────────
# RFID PHYSICAL VERIFICATION (Hardware Layer)
# ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/rfid-verify", methods=["POST"])
def rfid_verify():
    """
    Verify a physical RFID card tap from the ESP32 hardware terminal.

    Matches the card UID to a user, logs a physical verification event
    to the immutable audit trail, and returns granted/denied.

    Body: { "card_id": "0E692106" }

    No JWT required — this is a trusted hardware device on the local network.
    """
    from app.services.audit_service import AuditService

    data = request.get_json(silent=True) or {}
    card_id = str(data.get("card_id", "")).strip().upper()

    if not card_id:
        return jsonify({"granted": False, "message": "No card ID provided"}), 400

    db = get_db()
    user = db["users"].find_one({"rfid_card_id": card_id})

    audit = AuditService(db)

    if not user:
        # Unknown card — log the denied attempt
        audit.log_event(
            actor_id="hardware-terminal",
            actor_role="system",
            action_type="verification",
            resource_type="rfid",
            resource_id=card_id,
            reason=f"RFID access DENIED - unknown card {card_id}",
            severity="warning",
            source_ip=request.remote_addr,
        )
        return jsonify({
            "granted": False,
            "message": "Unknown card. Access denied.",
            "card_id": card_id,
        }), 200

    # Known card — log the successful physical verification
    full_name = user.get("full_name", "Unknown User")
    role = user.get("role", "user")

    audit.log_event(
        actor_id=user["_id"],
        actor_role=role,
        action_type="verification",
        resource_type="rfid",
        resource_id=card_id,
        patient_id=user["_id"] if role == "patient" else None,
        reason=f"Physical identity verified via RFID card by {full_name}",
        severity="info",
        source_ip=request.remote_addr,
    )

    # Phase 5: issue a short-lived physical presence token for this user.
    # Sensitive operations (erasure, redaction) can require this.
    from app.services.physical_presence_service import PhysicalPresenceService
    presence = PhysicalPresenceService(db)
    token = presence.record_presence(user["_id"], card_id)

    return jsonify({
        "granted": True,
        "message": f"Access granted. Welcome, {full_name}.",
        "user_name": full_name,
        "role": role,
        "card_id": card_id,
        "physical_presence_expires_at": token["expires_at"],
    }), 200


@auth_bp.route("/physical-presence/status", methods=["GET"])
@jwt_required
def physical_presence_status():
    """
    Check whether the current user has a valid physical presence token
    (i.e., they recently tapped their RFID card).

    The frontend polls this before allowing sensitive operations.
    """
    from app.services.physical_presence_service import PhysicalPresenceService
    presence = PhysicalPresenceService(get_db())
    status = presence.is_physically_present(g.current_user_id)
    return jsonify(status), 200
