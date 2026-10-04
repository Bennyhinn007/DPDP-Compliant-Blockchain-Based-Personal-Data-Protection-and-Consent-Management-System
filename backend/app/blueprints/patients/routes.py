"""
Patients Blueprint Routes.

Patient profile management and healthcare record access.
"""

import os
from flask import request, jsonify, g

from app.blueprints.patients import patients_bp
from app.extensions import get_db
from app.config import get_config
from app.services.patient_service import PatientService
from app.services.healthcare_record_service import HealthcareRecordService
from app.middleware.auth_middleware import jwt_required, roles_required
from app.utils.errors import ValidationError, AuthorizationError


def _get_patient_service():
    return PatientService(get_db())


def _get_record_service():
    return HealthcareRecordService(get_db())


def _get_auth_service():
    from app.services.auth_service import AuthService
    return AuthService(get_db(), get_config(os.environ.get("FLASK_ENV", "development")))


def _audit_record_created(record: dict, actor_role: str, patient_id: str) -> None:
    """
    Log an audit event for a newly created healthcare record.

    Record creation was previously un-audited (only correction/erasure were).
    This surfaces the data-origin event in the audit trail so the DPO and the
    Record Lifecycle Story can show "record created by the provider". Reuses the
    existing AuditService hash-chained log — no new logging mechanism.
    """
    try:
        from app.services.audit_service import AuditService
        AuditService(get_db()).log_event(
            actor_id=g.current_user_id,
            actor_role=actor_role,
            action_type="create",
            resource_type="healthcare_records",
            resource_id=record["_id"],
            patient_id=patient_id,
            reason="Healthcare record created at point of care",
            details={
                "record_type": record.get("record_type"),
                "verification_hash": record.get("verification_hash"),
                "blockchain_tx_ref": record.get("blockchain_tx_ref"),
            },
            source_ip=request.remote_addr,
        )
    except Exception:
        pass  # audit is best-effort; never blocks record creation


# ─────────────────────────────────────────────────────────────────────
# PATIENT PROFILE
# ─────────────────────────────────────────────────────────────────────

@patients_bp.route("/me", methods=["GET"])
@jwt_required
@roles_required("patient")
def get_my_profile():
    """Get current patient's own profile."""
    svc = _get_patient_service()
    patient = svc.get_patient_by_user_id(g.current_user_id)
    return jsonify({"patient": patient}), 200


@patients_bp.route("/me", methods=["PUT"])
@jwt_required
@roles_required("patient")
def update_my_profile():
    """Update current patient's profile."""
    data = request.get_json() or {}
    svc = _get_patient_service()
    patient = svc.get_patient_by_user_id(g.current_user_id)
    updated = svc.update_patient_profile(patient["_id"], g.current_user_id, data)
    return jsonify({"patient": updated, "message": "Profile updated"}), 200


@patients_bp.route("/", methods=["GET"])
@jwt_required
@roles_required("admin")
def list_all_patients():
    """List all patients (admin only)."""
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 20, type=int)
    svc = _get_patient_service()
    patients = svc.list_all_patients(skip=skip, limit=limit)
    return jsonify({"patients": patients, "count": len(patients)}), 200


@patients_bp.route("/<patient_id>", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_patient_by_id(patient_id):
    """Get a specific patient by ID (admin only)."""
    svc = _get_patient_service()
    patient = svc.get_patient_by_id(patient_id)
    return jsonify({"patient": patient}), 200


# ─────────────────────────────────────────────────────────────────────
# HEALTHCARE RECORDS
# ─────────────────────────────────────────────────────────────────────

@patients_bp.route("/me/records", methods=["GET"])
@jwt_required
@roles_required("patient")
def list_my_records():
    """List current patient's healthcare records."""
    record_type = request.args.get("type")
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 20, type=int)

    svc = _get_record_service()
    records = svc.list_my_records(
        user_id=g.current_user_id,
        record_type=record_type,
        skip=skip,
        limit=limit,
    )
    return jsonify({"records": records, "count": len(records)}), 200


@patients_bp.route("/me/records/<record_id>", methods=["GET"])
@jwt_required
@roles_required("patient")
def get_my_record(record_id):
    """Get a specific healthcare record (own records only)."""
    svc = _get_record_service()
    record = svc.get_record(record_id, g.current_user_id, "patient")
    return jsonify({"record": record}), 200


@patients_bp.route("/me/records/<record_id>/lifecycle", methods=["GET"])
@jwt_required
@roles_required("patient")
def get_my_record_lifecycle(record_id):
    """
    Record Lifecycle Story.

    Aggregates every lifecycle event for one record into a single, ordered
    timeline: created -> blockchain-anchored -> corrected (chameleon collision)
    -> erased (redacted). Makes the invisible cryptography visible.

    Returns:
        { "lifecycle": { record_id, record_type, redacted, current_status,
                          events: [ ...sorted ascending by timestamp ] } }
    """
    svc = _get_record_service()
    # Reuse the service's ownership check + decryption (raises if not owner).
    record = svc.get_record(record_id, g.current_user_id, "patient")

    db = get_db()
    rid = record_id
    scoped = {"resource_id": rid, "resource_type": "healthcare_records"}

    anchors = list(db["blockchain_anchors"].find(scoped).sort("created_at", 1))
    chameleons = list(db["chameleon_hash_records"].find(scoped).sort("created_at", 1))
    audits = list(db["audit_logs"].find({"resource_id": rid}).sort("created_at", 1))

    events = []

    # 1. CREATE node — from the record itself.
    events.append({
        "type": "created",
        "timestamp": record.get("created_at"),
        "title": "Record created",
        "description": f"{record.get('record_type', 'record').title()} — \"{record.get('title', '')}\"",
        "severity": "info",
    })

    # 2. ANCHOR nodes — one per blockchain anchor.
    for a in anchors:
        events.append({
            "type": "anchored",
            "timestamp": a.get("created_at"),
            "title": "Anchored to blockchain",
            "description": (
                f"SHA-256 hash committed. "
                f"{'Tx ' + a['transaction_hash'][:14] + '…' if a.get('transaction_hash') else 'Local anchor (chain offline)'}"
            ),
            "data_hash": a.get("data_hash"),
            "transaction_hash": a.get("transaction_hash"),
            "block_number": a.get("block_number"),
            "anchor_type": a.get("anchor_type"),
            "network": a.get("network"),
            "explorer_url": a.get("explorer_url"),
            "severity": "info",
        })

    # 3. REDACTION nodes — corrections / erasures via chameleon hash.
    for c in chameleons:
        rtype = c.get("redaction_type", "correction")
        collision = c.get("chameleon_collision") or {}
        events.append({
            "type": "erased" if rtype == "erasure" else "corrected",
            "timestamp": c.get("executed_at") or c.get("created_at"),
            "title": "Record erased (Right to Erasure)" if rtype == "erasure"
                     else "Record corrected (Right to Correction)",
            "description": c.get("reason", ""),
            "redaction_type": rtype,
            "legal_basis": c.get("legal_basis"),
            "affected_fields": c.get("affected_fields", []),
            "chameleon_proof_hash": c.get("redaction_proof_hash"),
            "chameleon_collision": {
                "chameleon_hash": collision.get("chameleon_hash"),
                "original_r": collision.get("original_r"),
                "collision_r": collision.get("collision_r"),
                "public_key_y": collision.get("public_key_y"),
                "modulus_bits": collision.get("modulus_bits"),
                "verified": collision.get("verified"),
            } if collision else None,
            "severity": "warning" if rtype == "erasure" else "info",
        })

    # 4. AUDIT nodes — supporting trail entries not already represented above.
    #    (Skip the redaction audits since chameleon nodes already cover them.)
    for ev in audits:
        action = ev.get("action_type", "")
        if action in ("update", "delete") or str(action).startswith("chameleon_"):
            continue  # already surfaced as corrected/erased nodes
        events.append({
            "type": "audit",
            "timestamp": ev.get("created_at"),
            "title": (action or "event").replace("_", " ").title(),
            "description": ev.get("reason", ""),
            "severity": ev.get("severity", "info"),
        })

    # Chronological order; None timestamps sink to the end.
    events.sort(key=lambda e: e.get("timestamp") or "~")

    return jsonify({
        "lifecycle": {
            "record_id": rid,
            "record_type": record.get("record_type"),
            "redacted": bool(record.get("redacted")),
            "current_status": "redacted" if record.get("redacted") else "active",
            "anchor_count": len(anchors),
            "redaction_count": len(chameleons),
            "events": events,
        }
    }), 200


@patients_bp.route("/me/records", methods=["POST"])
@jwt_required
@roles_required("patient")
def create_my_record():
    """
    Create a healthcare record for the current patient.

    Body:
        {
            "record_type": "consultation",
            "title": "General Checkup",
            "description": "Annual health checkup...",
            "diagnosis_codes": ["Z00.0"],
            "symptoms": ["fatigue"],
            "treatment_notes": "Rest recommended"
        }
    """
    data = request.get_json() or {}
    patient_svc = _get_patient_service()
    patient = patient_svc.get_patient_by_user_id(g.current_user_id)

    svc = _get_record_service()
    record = svc.create_record(
        patient_id=patient["_id"],
        created_by=g.current_user_id,
        record_type=data.get("record_type", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        diagnosis_codes=data.get("diagnosis_codes"),
        symptoms=data.get("symptoms"),
        treatment_notes=data.get("treatment_notes"),
    )
    _audit_record_created(record, actor_role="patient", patient_id=patient["_id"])
    return jsonify({"record": record, "message": "Record created"}), 201


@patients_bp.route("/me/records/<record_id>", methods=["PUT"])
@jwt_required
@roles_required("patient")
def update_my_record(record_id):
    """Update a healthcare record (own records only)."""
    data = request.get_json() or {}
    svc = _get_record_service()
    record = svc.update_record(record_id, g.current_user_id, "patient", data)
    return jsonify({"record": record, "message": "Record updated"}), 200


# ─────────────────────────────────────────────────────────────────────
# HOSPITAL REGISTRATION STAFF — REGISTER A NEW PATIENT
# ─────────────────────────────────────────────────────────────────────

# Roles that registration_staff is allowed to create. Admin can create ANY role;
# registration_staff can create any role EXCEPT privileged ones (admin/dpo) to
# prevent self-escalation (a staff account minting an admin and taking over).
_STAFF_ASSIGNABLE_ROLES = ("patient", "doctor", "registration_staff")
_PRIVILEGED_ROLES = ("admin", "dpo")


@patients_bp.route("/register", methods=["POST"])
@jwt_required
@roles_required("admin", "registration_staff")
def register_patient():
    """
    Register a NEW user account. Used by Hospital Registration Staff and Admin.

    - Admin may create ANY role.
    - Registration Staff may create any role EXCEPT admin/dpo (no self-escalation).
    - When role == "patient", demographic profile fields are stored too (reusing
      the existing encrypted patient profile model).

    Reuses the existing AuthService.register (same password hashing) — NOT a new
    auth system. Clinical records are still authored only by a doctor elsewhere.

    Body:
        {
          "full_name": "...", "email": "...", "password": "...",   # required
          "role": "patient|doctor|registration_staff|admin|dpo",   # optional, default patient
          # patient-only demographics (ignored for non-patient roles):
          "phone_number": "...", "address": "...", "blood_group": "...",
          "allergies": ["..."], "chronic_conditions": ["..."]
        }
    """
    data = request.get_json() or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "patient").strip().lower()
    if not full_name or not email or not password:
        raise ValidationError("full_name, email and password are required")

    # Role-assignment authorization (backend-enforced; never trust the client).
    actor_role = g.current_user_role
    if actor_role == "registration_staff" and role in _PRIVILEGED_ROLES:
        raise AuthorizationError("Registration staff cannot create admin or DPO accounts")
    if actor_role == "registration_staff" and role not in _STAFF_ASSIGNABLE_ROLES:
        raise ValidationError(f"role must be one of: {list(_STAFF_ASSIGNABLE_ROLES)}")

    auth_svc = _get_auth_service()
    # Create the account using the EXISTING registration path. allow_privileged_roles
    # is safe here: this is an authenticated admin/staff endpoint and the role the
    # caller may assign is already gated above (staff cannot assign admin/dpo).
    user = auth_svc.register(
        email=email, password=password, role=role, full_name=full_name,
        allow_privileged_roles=True,
    )
    user_id = user["id"]

    # For patients, fill the demographic profile (reuse encrypted profile model).
    patient_id = None
    if role == "patient":
        patient_svc = _get_patient_service()
        profile = patient_svc.get_patient_by_user_id(user_id)
        profile_updates = {
            k: data.get(k)
            for k in ("phone_number", "address", "blood_group", "allergies", "chronic_conditions")
            if data.get(k) is not None
        }
        if profile_updates:
            profile = patient_svc.update_patient_profile(profile["_id"], user_id, profile_updates)
        patient_id = profile["_id"]

    # Audit: staff/admin-driven account creation (reuse existing AuditService).
    try:
        from app.services.audit_service import AuditService
        AuditService(get_db()).log_event(
            actor_id=g.current_user_id,
            actor_role=actor_role,
            action_type="create",
            resource_type="users",
            resource_id=user_id,
            patient_id=user_id if role == "patient" else None,
            reason=f"{role} account created by {actor_role}",
            details={"registered_role": role, "patient_id": patient_id},
            source_ip=request.remote_addr,
        )
    except Exception:
        pass  # audit is best-effort; never blocks registration

    # Never echo the password back. Return only identifiers + status.
    return jsonify({
        "message": f"{role} account created",
        "role": role,
        "patient_id": patient_id,   # null for non-patient roles
        "user_id": user_id,
        "email": email,
        "full_name": full_name,
        "status": "active",
    }), 201


# ─────────────────────────────────────────────────────────────────────
# ADMIN ACCESS TO RECORDS
# ─────────────────────────────────────────────────────────────────────

@patients_bp.route("/<patient_id>/records", methods=["GET"])
@jwt_required
@roles_required("admin")
def list_patient_records(patient_id):
    """List records for a specific patient (admin only)."""
    record_type = request.args.get("type")
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 20, type=int)

    svc = _get_record_service()
    records = svc.list_records_for_patient(
        patient_id=patient_id,
        requesting_user_id=g.current_user_id,
        user_role="admin",
        record_type=record_type,
        skip=skip,
        limit=limit,
    )
    return jsonify({"records": records, "count": len(records)}), 200


@patients_bp.route("/<patient_id>/records", methods=["POST"])
@jwt_required
@roles_required("admin", "doctor")
def create_record_for_patient(patient_id):
    """
    Create a record for a specific patient — the Healthcare Provider (doctor or
    admin) authoring data at the point of care. Reuses the same create_record
    service (encryption + blockchain anchor), so protection is identical to all
    other record creation. This is provider-side authoring and does NOT bypass
    the consent gate that protects READING existing records.
    """
    data = request.get_json() or {}
    svc = _get_record_service()
    record = svc.create_record(
        patient_id=patient_id,
        created_by=g.current_user_id,
        record_type=data.get("record_type", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        diagnosis_codes=data.get("diagnosis_codes"),
        symptoms=data.get("symptoms"),
        treatment_notes=data.get("treatment_notes"),
    )
    _audit_record_created(record, actor_role=g.current_user_role, patient_id=patient_id)
    return jsonify({"record": record, "message": "Record created"}), 201


# ─────────────────────────────────────────────────────────────────────
# DATA EXPORT (PDF + JSON)
# ─────────────────────────────────────────────────────────────────────

@patients_bp.route("/me/export/pdf", methods=["GET"])
@jwt_required
@roles_required("patient")
def export_pdf_report():
    """
    Generate and download a patient-friendly PDF health report.

    Strips all internal fields. DPDP Section 11 compliant portable export.
    """
    from flask import send_file
    import io
    from app.services.pdf_export_service import PDFExportService

    patient_svc = _get_patient_service()
    patient = patient_svc.get_patient_by_user_id(g.current_user_id)

    record_svc = _get_record_service()
    records = record_svc.list_my_records(user_id=g.current_user_id)

    pdf_svc = PDFExportService()
    pdf_bytes = pdf_svc.generate_report(patient, records)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"health-report-{g.current_user_id[:8]}.pdf",
    )


@patients_bp.route("/me/export/json", methods=["GET"])
@jwt_required
@roles_required("patient")
def export_json_clean():
    """
    Export patient data as clean JSON (no internal fields).

    DPDP Section 11 compliant portable export.
    """
    patient_svc = _get_patient_service()
    patient = patient_svc.get_patient_by_user_id(g.current_user_id)

    record_svc = _get_record_service()
    records = record_svc.list_my_records(user_id=g.current_user_id)

    # Strip internal fields
    internal_fields = {"_id", "patient_id", "user_id", "created_by", "updated_by",
                       "version", "verification_hash", "blockchain_tx_ref",
                       "blockchain_anchor_id", "redacted_at", "redacted_by",
                       "redaction_reason"}

    clean_patient = {k: v for k, v in patient.items() if k not in internal_fields}
    clean_records = [{k: v for k, v in r.items() if k not in internal_fields} for r in records]

    export = {
        "report_type": "DPDP Data Portability Export",
        "generated_at": __import__("app.utils.helpers", fromlist=["utc_now"]).utc_now(),
        "patient": clean_patient,
        "health_records": clean_records,
        "compliance": {
            "encryption": "AES-256-GCM",
            "audit_trail": "Blockchain-anchored hash chain",
            "dpdp_section": "Section 11 — Right to Access",
        },
    }

    return jsonify(export), 200


# ─────────────────────────────────────────────────────────────────────
# CHAMELEON HASH: CORRECTION & ERASURE (DPDP Rights)
# ─────────────────────────────────────────────────────────────────────

@patients_bp.route("/me/records/<record_id>/correct", methods=["POST"])
@jwt_required
@roles_required("patient")
def correct_record(record_id):
    """
    Correct a healthcare record (Right to Correction, DPDP Section 12).

    Uses Chameleon Hash Simulation: archives previous version, applies
    correction, generates redaction proof, creates new blockchain anchor.

    Body:
        {
            "corrections": {"title": "Corrected Title", "description": "..."},
            "reason": "Original diagnosis was inaccurate"
        }
    """
    from app.services.chameleon_hash_service import ChameleonHashSimulator, RedactionType
    from app.services.blockchain_service import BlockchainService
    from app.services.audit_service import AuditService
    from app.extensions import get_web3

    data = request.get_json()
    if not data or not data.get("corrections") or not data.get("reason"):
        return jsonify({"error": True, "message": "corrections and reason required"}), 422

    db = get_db()
    records_col = db["healthcare_records"]
    patient_svc = _get_patient_service()
    patient = patient_svc.get_patient_by_user_id(g.current_user_id)

    # Fetch raw encrypted record from DB
    raw_record = records_col.find_one({"_id": record_id})
    if not raw_record:
        return jsonify({"error": True, "message": "Record not found"}), 404

    # Ownership check
    if raw_record["patient_id"] != patient["_id"]:
        return jsonify({"error": True, "message": "You can only correct your own records"}), 403

    # Chameleon Hash workflow
    ch = ChameleonHashSimulator()

    # Step 1: Create redaction request
    redaction_request = ch.create_redaction_request(
        resource_type="healthcare_records",
        resource_id=record_id,
        patient_id=patient["_id"],
        redaction_type=RedactionType.CORRECTION,
        reason=data["reason"],
        requested_by=g.current_user_id,
        affected_fields=list(data["corrections"].keys()),
    )

    # Step 2: Auto-authorize (patient-initiated correction)
    ch.authorize_redaction(
        redaction_request,
        authorizer_id=g.current_user_id,
        authorizer_role="patient",
        legal_basis="DPDP Act Section 12 - Right to Correction",
    )
    # Override role check for patient self-correction
    redaction_request["status"] = "authorized"

    # Step 3: Execute correction (encrypt corrections first)
    from app.services.encryption_service import get_encryption_service
    enc = get_encryption_service()
    encrypted_corrections = {}
    for field, value in data["corrections"].items():
        from app.services.encryption_service import SENSITIVE_FIELDS
        if field in SENSITIVE_FIELDS:
            encrypted_corrections[field] = enc.encrypt_field(value)
        else:
            encrypted_corrections[field] = value

    result = ch.execute_correction(
        redaction_request, raw_record, encrypted_corrections
    )

    # Step 4: Write corrected record to MongoDB
    modified = result["modified_record"]
    records_col.replace_one({"_id": record_id}, modified)

    # Step 5: Create new blockchain anchor
    try:
        bc = BlockchainService(db, get_web3())
        data_hash = bc.compute_record_hash(modified)
        anchor = bc.anchor_record(
            resource_type="healthcare_records",
            resource_id=record_id,
            data_hash=data_hash,
            patient_id=patient["_id"],
            anchor_type="record_verification",
        )
        records_col.update_one({"_id": record_id}, {"$set": {
            "verification_hash": data_hash,
            "blockchain_tx_ref": anchor.get("transaction_hash"),
            "blockchain_anchor_id": anchor["_id"],
        }})
    except Exception:
        pass

    # Step 6: Store version archive + chameleon record
    db["version_history"].insert_one(result["version_archive"])
    db["chameleon_hash_records"].insert_one(redaction_request)

    # Step 7: Audit
    audit_svc = AuditService(db)
    audit_svc.log_event(
        actor_id=g.current_user_id,
        actor_role="patient",
        action_type="update",
        resource_type="healthcare_records",
        resource_id=record_id,
        patient_id=g.current_user_id,
        reason=f"Record corrected: {data['reason']}",
        details={"corrected_fields": list(data["corrections"].keys()), "chameleon_proof": result["redaction_proof_hash"]},
        source_ip=request.remote_addr,
    )

    # Decrypt for response
    decrypted = enc.decrypt_document(records_col.find_one({"_id": record_id}))

    return jsonify({
        "message": "Record corrected successfully",
        "record": decrypted,
        "chameleon_proof": result["redaction_proof_hash"],
        "version_archived": result["version_archive"]["_id"],
    }), 200


@patients_bp.route("/me/records/<record_id>/erase", methods=["POST"])
@jwt_required
@roles_required("patient")
def erase_record(record_id):
    """
    Erase a healthcare record (Right to Erasure, DPDP Section 12).

    Replaces sensitive fields with [REDACTED], preserves audit trail,
    archives previous version, generates chameleon hash proof.

    Body:
        {
            "fields_to_erase": ["title", "description", "diagnosis_codes"],
            "reason": "Exercising right to erasure under DPDP Act"
        }
    """
    from app.services.chameleon_hash_service import ChameleonHashSimulator, RedactionType
    from app.services.blockchain_service import BlockchainService
    from app.services.audit_service import AuditService
    from app.extensions import get_web3

    data = request.get_json()
    if not data or not data.get("fields_to_erase") or not data.get("reason"):
        return jsonify({"error": True, "message": "fields_to_erase and reason required"}), 422

    db = get_db()
    records_col = db["healthcare_records"]
    patient_svc = _get_patient_service()
    patient = patient_svc.get_patient_by_user_id(g.current_user_id)

    # Fetch raw record
    raw_record = records_col.find_one({"_id": record_id})
    if not raw_record:
        return jsonify({"error": True, "message": "Record not found"}), 404

    if raw_record["patient_id"] != patient["_id"]:
        return jsonify({"error": True, "message": "You can only erase your own records"}), 403

    if raw_record.get("redacted"):
        return jsonify({"error": True, "message": "Record already redacted"}), 422

    # Phase 5: Physical presence gate — erasure is a sensitive, irreversible
    # operation. Require a recent RFID tap (physical presence) before proceeding.
    from app.services.physical_presence_service import PhysicalPresenceService
    presence = PhysicalPresenceService(db)
    presence_status = presence.is_physically_present(g.current_user_id)
    if not presence_status.get("present"):
        return jsonify({
            "error": True,
            "message": "Physical verification required. Please tap your RFID card to authorize this erasure.",
            "requires_physical_verification": True,
        }), 403

    # Chameleon Hash workflow
    ch = ChameleonHashSimulator()

    redaction_request = ch.create_redaction_request(
        resource_type="healthcare_records",
        resource_id=record_id,
        patient_id=patient["_id"],
        redaction_type=RedactionType.ERASURE,
        reason=data["reason"],
        requested_by=g.current_user_id,
        affected_fields=data["fields_to_erase"],
    )

    ch.authorize_redaction(
        redaction_request,
        authorizer_id=g.current_user_id,
        authorizer_role="patient",
        legal_basis="DPDP Act Section 12 - Right to Erasure",
    )
    redaction_request["status"] = "authorized"

    result = ch.execute_erasure(
        redaction_request, raw_record, data["fields_to_erase"]
    )

    # Write redacted record
    modified = result["modified_record"]
    records_col.replace_one({"_id": record_id}, modified)

    # Blockchain anchor for redaction proof
    try:
        bc = BlockchainService(db, get_web3())
        data_hash = bc.compute_record_hash(modified)
        anchor = bc.anchor_record(
            resource_type="healthcare_records",
            resource_id=record_id,
            data_hash=data_hash,
            patient_id=patient["_id"],
            anchor_type="record_verification",
        )
        records_col.update_one({"_id": record_id}, {"$set": {
            "verification_hash": data_hash,
            "blockchain_tx_ref": anchor.get("transaction_hash"),
            "blockchain_anchor_id": anchor["_id"],
        }})
    except Exception:
        pass

    # Store archives
    db["version_history"].insert_one(result["version_archive"])
    db["chameleon_hash_records"].insert_one(redaction_request)

    # Audit
    audit_svc = AuditService(db)
    audit_svc.log_event(
        actor_id=g.current_user_id,
        actor_role="patient",
        action_type="delete",
        resource_type="healthcare_records",
        resource_id=record_id,
        patient_id=g.current_user_id,
        reason=f"Record erased: {data['reason']}",
        details={"erased_fields": data["fields_to_erase"], "chameleon_proof": result["redaction_proof_hash"]},
        severity="warning",
        source_ip=request.remote_addr,
    )

    return jsonify({
        "message": "Record erased. Sensitive data replaced with [REDACTED].",
        "record": {
            "_id": record_id,
            "redacted": True,
            "redacted_fields": data["fields_to_erase"],
        },
        "chameleon_proof": result["redaction_proof_hash"],
        "version_archived": result["version_archive"]["_id"],
    }), 200
