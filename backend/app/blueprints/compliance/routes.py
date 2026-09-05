"""
Compliance Blueprint Routes.

DPDP Compliance Dashboard — admin-only access.
Provides aggregated metrics, rights request tracking, and compliance scoring.
"""

from flask import request, jsonify

from app.blueprints.compliance import compliance_bp
from app.extensions import get_db
from app.services.compliance_service import ComplianceService
from app.services.physical_presence_service import physical_presence_required
from app.middleware.auth_middleware import jwt_required, roles_required
from app.utils.helpers import utc_now


def _get_compliance_service():
    return ComplianceService(get_db())


@compliance_bp.route("/dashboard", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_dashboard():
    """
    Get full compliance dashboard.

    Returns aggregated data from all collections for DPO/Admin overview.
    """
    svc = _get_compliance_service()
    dashboard = svc.get_dashboard()
    return jsonify({"dashboard": dashboard}), 200


@compliance_bp.route("/stats", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_stats():
    """Get concise compliance statistics."""
    svc = _get_compliance_service()
    stats = svc.get_stats()
    return jsonify({"stats": stats}), 200


@compliance_bp.route("/rights-requests", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_rights_requests():
    """
    Get DPDP rights requests (corrections + erasures).

    Query params:
        skip: Pagination offset
        limit: Max results (default 20)
    """
    svc = _get_compliance_service()
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 20, type=int)
    data = svc.get_rights_requests(skip=skip, limit=limit)
    return jsonify({"rights_requests": data}), 200


@compliance_bp.route("/compliance-score", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_compliance_score():
    """
    Get DPDP compliance score (0-100).

    Evaluates encryption, consent, audit, blockchain, and rights coverage.
    """
    svc = _get_compliance_service()
    score = svc.get_compliance_score()
    return jsonify({"compliance_score": score}), 200


# ─────────────────────────────────────────────────────────────────────
# IDENTITY GOVERNANCE
# ─────────────────────────────────────────────────────────────────────

@compliance_bp.route("/governance", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_governance_data():
    """
    Get Identity & Access Governance data.

    Returns user directory, lifecycle metrics, access security,
    and healthcare relationships for the admin governance center.
    """
    from app.services.admin_service import AdminService
    svc = AdminService(get_db())
    data = svc.get_governance_data()
    return jsonify({"governance": data}), 200


@compliance_bp.route("/unlock-user/<user_id>", methods=["POST"])
@jwt_required
@roles_required("admin")
@physical_presence_required
def unlock_user(user_id):
    """Admin: Manually unlock a locked user account."""
    from flask import g
    from app.services.admin_service import AdminService
    svc = AdminService(get_db())
    result = svc.unlock_user(user_id, g.current_user_id)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result), 200


@compliance_bp.route("/lock-user/<user_id>", methods=["POST"])
@jwt_required
@roles_required("admin")
@physical_presence_required
def lock_user(user_id):
    """Admin: Lock a user account."""
    from flask import g
    from app.services.admin_service import AdminService
    data = request.get_json() or {}
    svc = AdminService(get_db())
    result = svc.lock_user(
        user_id, g.current_user_id,
        reason=data.get("reason", "Admin action"),
        duration_hours=data.get("duration_hours", 24)
    )
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result), 200


@compliance_bp.route("/suspend-user/<user_id>", methods=["POST"])
@jwt_required
@roles_required("admin")
@physical_presence_required
def suspend_user(user_id):
    """Admin: Suspend a user account indefinitely."""
    from flask import g
    from app.services.admin_service import AdminService
    data = request.get_json() or {}
    svc = AdminService(get_db())
    result = svc.suspend_user(user_id, g.current_user_id, reason=data.get("reason", "Admin action"))
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result), 200


@compliance_bp.route("/activate-user/<user_id>", methods=["POST"])
@jwt_required
@roles_required("admin")
@physical_presence_required
def activate_user(user_id):
    """Admin: Reactivate a suspended user account."""
    from flask import g
    from app.services.admin_service import AdminService
    svc = AdminService(get_db())
    result = svc.activate_user(user_id, g.current_user_id)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result), 200


@compliance_bp.route("/reset-mfa/<user_id>", methods=["POST"])
@jwt_required
@roles_required("admin")
@physical_presence_required
def reset_mfa(user_id):
    """Admin: Reset MFA for a user."""
    from flask import g
    from app.services.admin_service import AdminService
    svc = AdminService(get_db())
    result = svc.reset_mfa(user_id, g.current_user_id)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result), 200


@compliance_bp.route("/delete-user/<user_id>", methods=["DELETE"])
@jwt_required
@roles_required("admin")
@physical_presence_required
def delete_user(user_id):
    """Admin: Delete a user and archive their data."""
    from flask import g
    from app.services.admin_service import AdminService
    data = request.get_json() or {}
    svc = AdminService(get_db())
    result = svc.delete_user(user_id, g.current_user_id, reason=data.get("reason", "Admin action"))
    if result.get("error"):
        return jsonify(result), 400 if "own account" in result.get("message", "") else 404
    return jsonify(result), 200


@compliance_bp.route("/user/<user_id>", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_user_detail(user_id):
    """Admin: Get comprehensive user details."""
    from app.services.admin_service import AdminService
    svc = AdminService(get_db())
    result = svc.get_user_detail(user_id)
    if not result:
        return jsonify({"error": True, "message": "User not found"}), 404
    return jsonify(result), 200


@compliance_bp.route("/user/<user_id>/audit", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_user_audit(user_id):
    """Admin: Get audit history for a specific user."""
    from app.services.admin_service import AdminService
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 50, type=int)
    svc = AdminService(get_db())
    history = svc.get_user_audit_history(user_id, skip=skip, limit=limit)
    return jsonify({"audit_history": history, "count": len(history)}), 200


@compliance_bp.route("/user/<user_id>/consents", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_user_consents(user_id):
    """Admin: Get all consents for a user."""
    from app.services.admin_service import AdminService
    svc = AdminService(get_db())
    consents = svc.get_user_consents(user_id)
    return jsonify({"consents": consents, "count": len(consents)}), 200


@compliance_bp.route("/user/<user_id>/records", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_user_records(user_id):
    """Admin: Get all healthcare records for a user."""
    from app.services.admin_service import AdminService
    svc = AdminService(get_db())
    records = svc.get_user_records(user_id)
    return jsonify({"records": records, "count": len(records)}), 200


# ─────────────────────────────────────────────────────────────────────
# DPDP OPERATIONS CENTER
# ─────────────────────────────────────────────────────────────────────

@compliance_bp.route("/operations/pending-requests", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_pending_requests():
    """Get all pending correction and erasure requests needing DPO approval."""
    db = get_db()
    pending_corrections = list(db["chameleon_hash_records"].find(
        {"redaction_type": "correction", "status": {"$in": ["pending", "authorized"]}}
    ).sort("created_at", -1))
    pending_erasures = list(db["chameleon_hash_records"].find(
        {"redaction_type": "erasure", "status": {"$in": ["pending", "authorized"]}}
    ).sort("created_at", -1))
    executed_corrections = list(db["chameleon_hash_records"].find(
        {"redaction_type": "correction", "status": "executed"}
    ).sort("created_at", -1).limit(20))
    executed_erasures = list(db["chameleon_hash_records"].find(
        {"redaction_type": "erasure", "status": "executed"}
    ).sort("created_at", -1).limit(20))
    return jsonify({
        "pending_corrections": pending_corrections,
        "pending_erasures": pending_erasures,
        "executed_corrections": executed_corrections,
        "executed_erasures": executed_erasures,
        "totals": {
            "pending": len(pending_corrections) + len(pending_erasures),
            "executed": len(executed_corrections) + len(executed_erasures),
        }
    }), 200


@compliance_bp.route("/operations/request/<request_id>", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_request_detail(request_id):
    """Get full details of a specific correction/erasure request."""
    db = get_db()
    request_doc = db["chameleon_hash_records"].find_one({"_id": request_id})
    if not request_doc:
        return jsonify({"error": True, "message": "Request not found"}), 404

    # Get related blockchain anchors
    anchors = list(db["blockchain_anchors"].find(
        {"resource_id": request_doc.get("resource_id")}
    ).sort("created_at", -1))

    # Get version history
    versions = list(db["version_history"].find(
        {"record_id": request_doc.get("resource_id")}
    ).sort("created_at", -1))

    # Get audit trail
    audit = list(db["audit_logs"].find(
        {"resource_id": request_doc.get("resource_id")}
    ).sort("created_at", -1).limit(20))

    return jsonify({
        "request": request_doc,
        "blockchain_anchors": anchors,
        "version_history": versions,
        "audit_trail": audit,
    }), 200


# ─────────────────────────────────────────────────────────────────────
# BLOCKCHAIN EXPLORER (ADMIN)
# ─────────────────────────────────────────────────────────────────────

@compliance_bp.route("/blockchain/explorer", methods=["GET"])
@jwt_required
@roles_required("admin")
def blockchain_explorer():
    """Full blockchain explorer: list all anchors with search/filter."""
    db = get_db()
    search = request.args.get("search", "")
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 50, type=int)

    query = {}
    if search:
        query = {"$or": [
            {"resource_id": {"$regex": search, "$options": "i"}},
            {"transaction_hash": {"$regex": search, "$options": "i"}},
            {"data_hash": {"$regex": search, "$options": "i"}},
        ]}

    anchors = list(db["blockchain_anchors"].find(query).sort("created_at", -1).skip(skip).limit(limit))
    total = db["blockchain_anchors"].count_documents(query)

    return jsonify({
        "anchors": anchors,
        "total": total,
        "skip": skip,
        "limit": limit,
    }), 200


@compliance_bp.route("/blockchain/anchor/<anchor_id>", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_anchor_detail(anchor_id):
    """Get details of a specific blockchain anchor."""
    db = get_db()
    anchor = db["blockchain_anchors"].find_one({"_id": anchor_id})
    if not anchor:
        return jsonify({"error": True, "message": "Anchor not found"}), 404

    # Get related record
    record = None
    if anchor.get("resource_id"):
        record = db["healthcare_records"].find_one({"_id": anchor["resource_id"]})
        if record:
            from app.services.encryption_service import get_encryption_service
            enc = get_encryption_service()
            record = enc.decrypt_document(record)

    return jsonify({"anchor": anchor, "record": record}), 200


# ─────────────────────────────────────────────────────────────────────
# SYSTEM HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────

@compliance_bp.route("/system-health", methods=["GET"])
@jwt_required
@roles_required("admin")
def system_health():
    """Get real-time health status of all system components."""
    from app.extensions import get_web3
    db = get_db()

    # MongoDB health
    try:
        db.command("ping")
        mongo_status = "operational"
    except Exception:
        mongo_status = "error"

    # Blockchain health
    try:
        w3 = get_web3()
        if w3 and w3.is_connected():
            block = w3.eth.block_number
            blockchain_status = "operational"
            blockchain_block = block
        else:
            blockchain_status = "disconnected"
            blockchain_block = None
    except Exception:
        blockchain_status = "error"
        blockchain_block = None

    # Encryption health
    try:
        from app.services.encryption_service import get_encryption_service
        enc = get_encryption_service()
        test = enc.encrypt_field("health_check_test")
        decrypted = enc.decrypt_field(test)
        encryption_status = "operational" if decrypted == "health_check_test" else "error"
    except Exception:
        encryption_status = "error"

    # Audit chain health
    try:
        last_audit = db["audit_logs"].find_one(sort=[("created_at", -1)])
        audit_status = "operational" if last_audit and last_audit.get("log_hash") else "warning"
    except Exception:
        audit_status = "error"

    # Consent system health
    consent_status = "operational" if db["consents"].count_documents({}) >= 0 else "error"

    # Chameleon hash engine
    chameleon_status = "operational" if "chameleon_hash_records" in db.list_collection_names() else "warning"

    return jsonify({
        "subsystems": {
            "mongodb": {"status": mongo_status, "description": "Primary data store"},
            "blockchain": {"status": blockchain_status, "description": f"Ganache (Block #{blockchain_block})" if blockchain_block else "Ganache node"},
            "encryption": {"status": encryption_status, "description": "AES-256-GCM field-level"},
            "audit_logger": {"status": audit_status, "description": "Hash-chained, append-only"},
            "consent_manager": {"status": consent_status, "description": "6 consent types"},
            "chameleon_hash": {"status": chameleon_status, "description": "Redaction proof generation"},
        },
        "checked_at": utc_now(),
    }), 200


# ─────────────────────────────────────────────────────────────────────
# COMPLIANCE EXPORT
# ─────────────────────────────────────────────────────────────────────

@compliance_bp.route("/export/json", methods=["GET"])
@jwt_required
@roles_required("admin")
def export_compliance_json():
    """Export full compliance report as JSON."""
    svc = _get_compliance_service()
    dashboard = svc.get_dashboard()
    score = svc.get_compliance_score()
    rights = svc.get_rights_requests(skip=0, limit=100)

    from app.utils.helpers import utc_now
    report = {
        "report_type": "DPDP Compliance Report",
        "generated_at": utc_now(),
        "compliance_score": score,
        "dashboard": dashboard,
        "rights_requests": rights,
    }
    return jsonify(report), 200


@compliance_bp.route("/audit/all", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_all_audit_logs():
    """Get all audit logs with filtering and pagination."""
    db = get_db()
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 50, type=int)
    action_type = request.args.get("action_type", "")
    severity = request.args.get("severity", "")
    actor_id = request.args.get("actor_id", "")

    query = {}
    if action_type:
        query["action_type"] = action_type
    if severity:
        query["severity"] = severity
    if actor_id:
        query["actor_id"] = actor_id

    logs = list(db["audit_logs"].find(query).sort("created_at", -1).skip(skip).limit(limit))
    total = db["audit_logs"].count_documents(query)

    return jsonify({"logs": logs, "total": total, "skip": skip, "limit": limit}), 200


# ─────────────────────────────────────────────────────────────────────
# PHYSICAL ACCESS LOG (RFID Hardware Terminal)
# ─────────────────────────────────────────────────────────────────────

@compliance_bp.route("/physical-access/log", methods=["GET"])
@jwt_required
@roles_required("admin")
def physical_access_log():
    """
    Live feed of physical RFID verification events from the hardware terminal.

    Reads RFID events (resource_type='rfid') from the immutable audit trail
    and returns them for the admin Physical Access Log panel.

    Query params:
        limit: max events (default 30)
    """
    db = get_db()
    limit = request.args.get("limit", 30, type=int)

    events = list(
        db["audit_logs"]
        .find({"resource_type": "rfid"})
        .sort("created_at", -1)
        .limit(limit)
    )

    # Shape the response for the frontend
    feed = []
    granted = 0
    denied = 0
    for e in events:
        is_granted = e.get("severity") == "info"  # info = granted, warning = denied
        if is_granted:
            granted += 1
        else:
            denied += 1
        feed.append({
            "_id": e["_id"],
            "card_id": e.get("resource_id", ""),
            "actor_role": e.get("actor_role", "unknown"),
            "reason": e.get("reason", ""),
            "granted": is_granted,
            "created_at": e.get("created_at"),
        })

    return jsonify({
        "events": feed,
        "stats": {
            "total": len(feed),
            "granted": granted,
            "denied": denied,
        },
    }), 200
