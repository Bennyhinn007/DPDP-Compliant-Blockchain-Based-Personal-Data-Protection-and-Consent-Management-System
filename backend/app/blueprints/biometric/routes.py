"""
Biometric Blueprint — fingerprint second factor for admins (PROTOTYPE).

Endpoints under /api/v1/biometric. All require an authenticated ADMIN session.
Fingerprint capture + matching happen in the browser via the vendor's local
service (SecuGen); this API stores the encrypted enrolled template and
turns a successful match into a short-lived physical-presence token.

NOTE: failures here return 403 (not 401) on purpose — the frontend's global 401
handler logs the user out, and a non-matching finger must not do that.
"""

import os
from flask import request, jsonify, g

from app.blueprints.biometric import biometric_bp
from app.extensions import get_db
from app.config import get_config
from app.middleware.auth_middleware import jwt_required, roles_required
from app.services.biometric_service import BiometricService
from app.services.physical_presence_service import PhysicalPresenceService
from app.utils.errors import ValidationError


def _config():
    return get_config(os.environ.get("FLASK_ENV", "development"))


def _svc() -> BiometricService:
    return BiometricService(get_db())


def _disabled():
    if not getattr(_config(), "BIOMETRIC_ENABLED", True):
        return jsonify({"error": True, "message": "Biometric features are disabled"}), 403
    return None


def _audit(action_type: str, reason: str, severity: str = "info", details: dict = None):
    try:
        from app.services.audit_service import AuditService
        AuditService(get_db()).log_event(
            actor_id=g.current_user_id,
            actor_role=g.current_user_role,
            action_type=action_type,
            resource_type="biometric",
            resource_id=g.current_user_id,
            reason=reason,
            severity=severity,
            details=details or {},
            source_ip=request.remote_addr,
        )
    except Exception:
        pass  # audit is best-effort; never blocks the operation


@biometric_bp.route("/status", methods=["GET"])
@jwt_required
@roles_required("admin")
def biometric_status():
    off = _disabled()
    if off:
        return off
    return jsonify(_svc().status(g.current_user_id)), 200


@biometric_bp.route("/enroll", methods=["POST"])
@jwt_required
@roles_required("admin")
def biometric_enroll():
    """
    Enroll (or replace) the admin's fingerprint template.
    Replacing an existing enrollment requires a recent physical-presence proof
    (fingerprint or RFID) so a hijacked session can't quietly swap in a new finger.
    """
    off = _disabled()
    if off:
        return off
    data = request.get_json() or {}
    svc = _svc()

    if svc.is_enrolled(g.current_user_id):
        presence = PhysicalPresenceService(get_db()).is_physically_present(g.current_user_id)
        if not presence.get("present"):
            return jsonify({
                "error": True,
                "message": "Verify your current fingerprint or tap your RFID card before replacing your enrollment.",
                "requires_physical_verification": True,
            }), 403

    status = svc.enroll(
        g.current_user_id,
        template_b64=data.get("template", ""),
        provider=data.get("provider", ""),
        quality=data.get("quality"),
    )
    _audit("create", "Fingerprint enrolled", details={"provider": status.get("provider")})
    return jsonify({"message": "Fingerprint enrolled", **status}), 201


@biometric_bp.route("/template", methods=["GET"])
@jwt_required
@roles_required("admin")
def biometric_template():
    """The admin's OWN enrolled template, so the browser can match locally."""
    off = _disabled()
    if off:
        return off
    tpl = _svc().get_template(g.current_user_id)
    if not tpl:
        return jsonify({"error": True, "message": "No fingerprint enrolled"}), 404
    return jsonify(tpl), 200


@biometric_bp.route("/verify", methods=["POST"])
@jwt_required
@roles_required("admin")
def biometric_verify():
    """
    Body: { "score": <number>, "provider": "secugen" }
    The browser matched a live scan against the enrolled template and reports the
    score. At/above the threshold a physical-presence token is recorded.
    """
    off = _disabled()
    if off:
        return off
    data = request.get_json() or {}
    if "score" not in data:
        raise ValidationError("score is required")

    min_score = int(getattr(_config(), "BIOMETRIC_MIN_SCORE", 80))
    result = _svc().record_verification(
        g.current_user_id, data.get("score"), (data.get("provider") or "").lower(), min_score
    )

    if result.get("verified"):
        _audit("verification", "Fingerprint verified (physical presence recorded)",
               details={"provider": data.get("provider")})
        return jsonify(result), 200

    _audit("verification", f"Fingerprint verification FAILED: {result.get('reason')}",
           severity="warning", details={"provider": data.get("provider")})
    return jsonify({"error": True, **result}), 403


@biometric_bp.route("/enroll", methods=["DELETE"])
@jwt_required
@roles_required("admin")
def biometric_remove():
    """Remove the enrolled template. Requires recent physical-presence proof."""
    off = _disabled()
    if off:
        return off
    presence = PhysicalPresenceService(get_db()).is_physically_present(g.current_user_id)
    if not presence.get("present"):
        return jsonify({
            "error": True,
            "message": "Verify your fingerprint or tap your RFID card to remove your enrollment.",
            "requires_physical_verification": True,
        }), 403
    removed = _svc().remove(g.current_user_id)
    if removed:
        _audit("delete", "Fingerprint enrollment removed", severity="warning")
    return jsonify({"removed": removed}), 200
