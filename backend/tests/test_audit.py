"""
Tests for Audit Logging (Day 5).

Tests cover:
- Audit event generation (various action types)
- Patient timeline retrieval
- Data access history
- DPO/Admin log overview
- Hash chain integrity
- Ownership enforcement
- Filtering and pagination
"""

import pytest
from tests.accounts import create_test_account
from app import create_app
from app.extensions import get_db
from app.services.audit_service import AuditService


@pytest.fixture
def app():
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        db = get_db()
        for col in ["users", "patients", "consents", "consent_receipts",
                    "audit_logs", "data_access_logs"]:
            db[col].delete_many({})
    yield
    with app.app_context():
        db = get_db()
        for col in ["users", "patients", "consents", "consent_receipts",
                    "audit_logs", "data_access_logs"]:
            db[col].delete_many({})


def register_and_login(client, email="patient@test.com", role="patient"):
    create_test_account(
        client, email=email, password="TestPass123", role=role, full_name="Test User",
    )
    resp = client.post("/api/v1/auth/login", json={
        "email": email, "password": "TestPass123",
    })
    return resp.get_json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestAuditEventGeneration:
    """Test audit log creation."""

    def test_create_audit_event(self, app):
        with app.app_context():
            db = get_db()
            svc = AuditService(db)

            log = svc.log_event(
                actor_id="user-001",
                actor_role="patient",
                action_type="login",
                resource_type="auth",
                resource_id=None,
                patient_id=None,
                reason="User authentication",
                severity="info",
            )

            assert log["_id"] is not None
            assert log["action_type"] == "login"
            assert log["action_category"] == "auth_event"
            assert log["log_hash"] is not None
            assert len(log["log_hash"]) == 64

    def test_hash_chain_links(self, app):
        with app.app_context():
            db = get_db()
            svc = AuditService(db)

            log1 = svc.log_event(
                actor_id="user-001", actor_role="patient",
                action_type="login", resource_type="auth",
            )
            log2 = svc.log_event(
                actor_id="user-001", actor_role="patient",
                action_type="read", resource_type="patients",
            )

            # Second log should reference first log's hash
            assert log2["previous_log_hash"] == log1["log_hash"]

    def test_genesis_log_has_genesis_previous(self, app):
        with app.app_context():
            db = get_db()
            svc = AuditService(db)

            log = svc.log_event(
                actor_id="user-001", actor_role="patient",
                action_type="login", resource_type="auth",
            )
            assert log["previous_log_hash"] == "genesis"

    def test_consent_event_categorized(self, app):
        with app.app_context():
            db = get_db()
            svc = AuditService(db)

            log = svc.log_event(
                actor_id="user-001", actor_role="patient",
                action_type="consent_grant", resource_type="consents",
            )
            assert log["action_category"] == "consent_event"

    def test_data_access_log_creation(self, app):
        with app.app_context():
            db = get_db()
            svc = AuditService(db)

            access = svc.log_data_access(
                patient_id="patient-001",
                accessor_id="doctor-001",
                accessor_role="doctor",
                accessor_name="Dr. Sharma",
                access_type="view",
                data_categories=["medical_history", "allergies"],
                purpose="Cardiology consultation",
                consent_id="consent-001",
            )

            assert access["_id"] is not None
            assert access["accessor_name"] == "Dr. Sharma"
            assert access["data_categories"] == ["medical_history", "allergies"]
            assert access["consent_id"] == "consent-001"


class TestPatientTimeline:
    """Test patient-facing timeline API."""

    def test_patient_sees_own_timeline(self, client, app):
        token = register_and_login(client)

        # Generate some events by accessing data
        client.get("/api/v1/patients/me", headers=auth(token))

        # Manually insert audit events using user_id as patient_id
        with app.app_context():
            db = get_db()
            user = db["users"].find_one({"role": "patient"})
            user_id = user["_id"]
            svc = AuditService(db)
            svc.log_event(
                actor_id="doctor-001", actor_role="doctor",
                action_type="read", resource_type="healthcare_records",
                patient_id=user_id, reason="Consultation access",
            )
            svc.log_event(
                actor_id="doctor-001", actor_role="doctor",
                action_type="create", resource_type="healthcare_records",
                patient_id=user_id, reason="Created consultation",
            )

        resp = client.get("/api/v1/audit/timeline", headers=auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        # At least 2 manual events + login/register events with patient_id
        assert data["count"] >= 2

    def test_timeline_filter_by_action_type(self, client, app):
        token = register_and_login(client)

        with app.app_context():
            db = get_db()
            user = db["users"].find_one({"role": "patient"})
            user_id = user["_id"]
            svc = AuditService(db)
            svc.log_event(
                actor_id="user-x", actor_role="doctor",
                action_type="read", resource_type="records",
                patient_id=user_id,
            )
            svc.log_event(
                actor_id="user-x", actor_role="doctor",
                action_type="create", resource_type="records",
                patient_id=user_id,
            )

        resp = client.get("/api/v1/audit/timeline?action_type=read", headers=auth(token))
        assert resp.get_json()["count"] >= 1

    def test_unauthenticated_cannot_access_timeline(self, client):
        resp = client.get("/api/v1/audit/timeline")
        assert resp.status_code == 401


class TestDataAccessHistory:
    """Test data access history API."""

    def test_patient_sees_access_history(self, client, app):
        token = register_and_login(client)

        with app.app_context():
            db = get_db()
            # Use user_id as patient_id (matches route behavior)
            user = db["users"].find_one({"role": "patient"})
            user_id = user["_id"]
            svc = AuditService(db)
            svc.log_data_access(
                patient_id=user_id,
                accessor_id="doc-001", accessor_role="doctor",
                accessor_name="Dr. Priya Sharma",
                access_type="view",
                data_categories=["medical_history"],
                purpose="Annual checkup review",
            )
            svc.log_data_access(
                patient_id=user_id,
                accessor_id="pharm-001", accessor_role="pharmacy_staff",
                accessor_name="Amit Patel",
                access_type="view",
                data_categories=["prescriptions"],
                purpose="Prescription dispensing",
            )

        resp = client.get("/api/v1/audit/access-history", headers=auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 2
        assert data["summary"]["total_access_events"] == 2

    def test_filter_access_history_by_role(self, client, app):
        token = register_and_login(client)

        with app.app_context():
            db = get_db()
            user = db["users"].find_one({"role": "patient"})
            user_id = user["_id"]
            svc = AuditService(db)
            svc.log_data_access(
                patient_id=user_id,
                accessor_id="doc-001", accessor_role="doctor",
                accessor_name="Dr. Sharma",
                access_type="view", data_categories=["medical_history"],
                purpose="Consultation",
            )
            svc.log_data_access(
                patient_id=user_id,
                accessor_id="pharm-001", accessor_role="pharmacy_staff",
                accessor_name="Pharmacist",
                access_type="view", data_categories=["prescriptions"],
                purpose="Dispensing",
            )

        resp = client.get("/api/v1/audit/access-history?accessor_role=doctor",
                          headers=auth(token))
        assert resp.get_json()["count"] == 1


class TestAdminAuditOverview:
    """Test DPO/Admin audit APIs."""

    def test_admin_can_view_all_logs(self, client, app):
        register_and_login(client, "p@test.com", "patient")
        admin_token = register_and_login(client, "admin@test.com", "admin")

        # Generate events
        with app.app_context():
            db = get_db()
            svc = AuditService(db)
            for i in range(5):
                svc.log_event(
                    actor_id=f"user-{i}", actor_role="patient",
                    action_type="read", resource_type="patients",
                )

        resp = client.get("/api/v1/audit/logs", headers=auth(admin_token))
        assert resp.status_code == 200
        # At least 5 manual + auth events from register/login
        assert resp.get_json()["count"] >= 5

    def test_patient_cannot_access_admin_logs(self, client):
        token = register_and_login(client)
        resp = client.get("/api/v1/audit/logs", headers=auth(token))
        assert resp.status_code == 403

    def test_admin_filter_by_severity(self, client, app):
        admin_token = register_and_login(client, "admin@test.com", "admin")

        with app.app_context():
            db = get_db()
            svc = AuditService(db)
            svc.log_event(
                actor_id="u1", actor_role="doctor",
                action_type="read", resource_type="records",
                severity="info",
            )
            svc.log_event(
                actor_id="u2", actor_role="doctor",
                action_type="break_glass", resource_type="records",
                severity="critical",
            )

        resp = client.get("/api/v1/audit/logs?severity=critical",
                          headers=auth(admin_token))
        assert resp.get_json()["count"] == 1
        assert resp.get_json()["logs"][0]["severity"] == "critical"

    def test_admin_get_single_log(self, client, app):
        admin_token = register_and_login(client, "admin@test.com", "admin")

        with app.app_context():
            db = get_db()
            svc = AuditService(db)
            log = svc.log_event(
                actor_id="u1", actor_role="patient",
                action_type="login", resource_type="auth",
            )
            log_id = log["_id"]

        resp = client.get(f"/api/v1/audit/logs/{log_id}", headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()["log"]["action_type"] == "login"

    def test_admin_get_stats(self, client, app):
        admin_token = register_and_login(client, "admin@test.com", "admin")

        with app.app_context():
            db = get_db()
            svc = AuditService(db)
            svc.log_event(actor_id="u1", actor_role="p", action_type="login",
                          resource_type="auth", severity="info")
            svc.log_event(actor_id="u1", actor_role="p", action_type="break_glass",
                          resource_type="records", severity="critical")

        resp = client.get("/api/v1/audit/stats", headers=auth(admin_token))
        assert resp.status_code == 200
        stats = resp.get_json()["stats"]
        assert stats["total_events"] >= 2
        assert stats["critical_events"] >= 1
