"""
Doctors Blueprint Routes.

Consent-gated access to patient healthcare records.
Every access attempt is audited for DPDP transparency.
"""

from flask import request, jsonify, g

from app.blueprints.doctors import doctors_bp
from app.extensions import get_db
from app.services.doctor_service import DoctorService
from app.middleware.auth_middleware import jwt_required, roles_required
from app.utils.errors import ConsentRequiredError


def _get_doctor_service():
    return DoctorService(get_db())


@doctors_bp.route("/health", methods=["GET"])
def doctors_health():
    return jsonify({"status": "doctor service ready"}), 200


@doctors_bp.route("/patients/search", methods=["GET"])
@jwt_required
@roles_required("doctor", "admin")
def search_patients():
    """
    Search patients by name.

    Query params:
        q: Search query (name substring)

    Returns list of matching patients with consent status.
    """
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"patients": [], "message": "Query must be at least 2 characters"}), 200

    svc = _get_doctor_service()
    results = svc.search_patients(query, g.current_user_id)
    return jsonify({"patients": results, "count": len(results)}), 200


@doctors_bp.route("/patients/<patient_id>/records", methods=["GET"])
@jwt_required
@roles_required("doctor", "admin")
def get_patient_records(patient_id):
    """
    Access patient's healthcare records (consent-gated).

    Requires active healthcare_treatment consent from patient.
    Returns 403 with detailed message if consent not granted.
    """
    svc = _get_doctor_service()

    # Get doctor name for audit
    db = get_db()
    user = db["users"].find_one({"_id": g.current_user_id})
    doctor_name = user.get("full_name", "Doctor") if user else "Doctor"

    try:
        result = svc.get_patient_records(patient_id, g.current_user_id, doctor_name)
        response = jsonify(result)
        response.headers["Cache-Control"] = "no-store"
        return response, 200
    except ConsentRequiredError as e:
        return jsonify({
            "error": True,
            "access_status": "denied",
            "message": str(e),
            "reason": {"expired": "CONSENT_EXPIRED", "scope_restricted": "CONSENT_SCOPE_RESTRICTED"}.get(
                e.consent_status, "CONSENT_NOT_GRANTED"
            ),
            "patient_id": patient_id,
            "required_consent": "healthcare_treatment",
        }), 403
