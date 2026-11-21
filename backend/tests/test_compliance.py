"""
Tests for DPDP Compliance Dashboard (Day 9).

Tests cover:
- Dashboard endpoint (aggregated data)
- Stats endpoint (concise counts)
- Rights requests (corrections + erasures from version_history)
- Compliance score (0-100, breakdown by category)
- Admin-only access enforcement
"""

import pytest
from tests.accounts import create_test_account
from app import create_app
from app.extensions import get_db


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
        for col in ["users", "patients", "healthcare_records", "consents",
                    "consent_receipts", "audit_logs", "blockchain_anchors",
                    "version_history", "chameleon_hash_records"]:
            if col in db.list_collection_names():
                db[col].delete_many({})
    yield
    with app.app_context():
        db = get_db()
        for col in ["users", "patients", "healthcare_records", "consents",
                    "consent_receipts", "audit_logs", "blockchain_anchors",
                    "version_history", "chameleon_hash_records"]:
            if col in db.list_collection_names():
                db[col].delete_many({})


def register_and_login(client, email, role="patient"):
    create_test_account(
        client, email=email, password="TestPass123", role=role, full_name=f"User {role}",
    )
    resp = client.post("/api/v1/auth/login", json={
        "email": email, "password": "TestPass123",
    })
    return resp.get_json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def seed_data(client, patient_token, admin_token):
    """Create some test data for dashboard."""
    # Create records
    client.post("/api/v1/patients/me/records", json={
        "record_type": "consultation",
        "title": "Test Record",
        "description": "A test healthcare record for compliance testing.",
    }, headers=auth(patient_token))

    # Grant consent
    client.post("/api/v1/consents/grant", json={
        "consent_type": "healthcare_treatment",
        "recipient": {"kind": "hospital", "hospital_id": "citycare"},
        "expiry_days": 365,
    }, headers=auth(patient_token))


class TestDashboard:
    """Test compliance dashboard endpoint."""

    def test_admin_gets_dashboard(self, client):
        patient_token = register_and_login(client, "p@test.com", "patient")
        admin_token = register_and_login(client, "a@test.com", "admin")
        seed_data(client, patient_token, admin_token)

        resp = client.get("/api/v1/compliance/dashboard", headers=auth(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()["dashboard"]

        assert "users" in data
        assert "patients" in data
        assert "healthcare_records" in data
        assert "consents" in data
        assert "audit" in data
        assert "blockchain" in data
        assert "rights_requests" in data
        assert "timestamp" in data

    def test_dashboard_user_counts(self, client):
        register_and_login(client, "p1@test.com", "patient")
        register_and_login(client, "p2@test.com", "patient")
        admin_token = register_and_login(client, "a@test.com", "admin")

        resp = client.get("/api/v1/compliance/dashboard", headers=auth(admin_token))
        users = resp.get_json()["dashboard"]["users"]
        assert users["total"] >= 3
        assert users["by_role"]["patient"] >= 2
        assert users["by_role"]["admin"] >= 1

    def test_patient_cannot_access_dashboard(self, client):
        token = register_and_login(client, "p@test.com", "patient")
        resp = client.get("/api/v1/compliance/dashboard", headers=auth(token))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access(self, client):
        resp = client.get("/api/v1/compliance/dashboard")
        assert resp.status_code == 401


class TestStats:
    """Test compliance stats endpoint."""

    def test_stats_returns_all_counts(self, client):
        patient_token = register_and_login(client, "p@test.com", "patient")
        admin_token = register_and_login(client, "a@test.com", "admin")
        seed_data(client, patient_token, admin_token)

        resp = client.get("/api/v1/compliance/stats", headers=auth(admin_token))
        assert resp.status_code == 200
        stats = resp.get_json()["stats"]

        assert stats["total_users"] >= 2
        assert stats["total_patients"] >= 1
        assert stats["total_records"] >= 1
        assert stats["total_consents"] >= 1
        assert stats["active_consents"] >= 1
        assert stats["total_audit_events"] >= 1

    def test_stats_counts_redacted_records(self, client, app):
        admin_token = register_and_login(client, "a@test.com", "admin")

        with app.app_context():
            db = get_db()
            db["healthcare_records"].insert_one({
                "_id": "redacted-1", "redacted": True, "record_type": "consultation",
            })

        resp = client.get("/api/v1/compliance/stats", headers=auth(admin_token))
        stats = resp.get_json()["stats"]
        assert stats["redacted_records"] >= 1


class TestRightsRequests:
    """Test DPDP rights requests endpoint."""

    def test_returns_corrections_and_erasures(self, client, app):
        admin_token = register_and_login(client, "a@test.com", "admin")

        with app.app_context():
            db = get_db()
            db["version_history"].insert_one({
                "_id": "v1", "resource_id": "r1", "modification_type": "correction",
                "modification_reason": "Title fix", "created_at": "2025-01-01",
            })
            db["version_history"].insert_one({
                "_id": "v2", "resource_id": "r2", "modification_type": "erasure",
                "modification_reason": "Right to erasure", "created_at": "2025-01-02",
            })

        resp = client.get("/api/v1/compliance/rights-requests", headers=auth(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()["rights_requests"]
        assert data["total_corrections"] == 1
        assert data["total_erasures"] == 1
        assert len(data["correction_requests"]) == 1
        assert len(data["erasure_requests"]) == 1

    def test_empty_when_no_requests(self, client):
        admin_token = register_and_login(client, "a@test.com", "admin")
        resp = client.get("/api/v1/compliance/rights-requests", headers=auth(admin_token))
        data = resp.get_json()["rights_requests"]
        assert data["total_corrections"] == 0
        assert data["total_erasures"] == 0


class TestComplianceScore:
    """Test compliance scoring."""

    def test_score_returns_breakdown(self, client):
        patient_token = register_and_login(client, "p@test.com", "patient")
        admin_token = register_and_login(client, "a@test.com", "admin")
        seed_data(client, patient_token, admin_token)

        resp = client.get("/api/v1/compliance/compliance-score", headers=auth(admin_token))
        assert resp.status_code == 200
        score = resp.get_json()["compliance_score"]

        assert "overall_score" in score
        assert "max_score" in score
        assert score["max_score"] == 100
        assert "grade" in score
        assert "breakdown" in score
        assert "encryption" in score["breakdown"]
        assert "consent_management" in score["breakdown"]
        assert "audit_logging" in score["breakdown"]
        assert "blockchain_anchoring" in score["breakdown"]
        assert "dpdp_rights" in score["breakdown"]

    def test_score_is_in_valid_range(self, client):
        admin_token = register_and_login(client, "a@test.com", "admin")
        resp = client.get("/api/v1/compliance/compliance-score", headers=auth(admin_token))
        score = resp.get_json()["compliance_score"]
        assert 0 <= score["overall_score"] <= 100

    def test_score_improves_with_data(self, client):
        admin_token = register_and_login(client, "a@test.com", "admin")

        # Score with no patient data
        resp1 = client.get("/api/v1/compliance/compliance-score", headers=auth(admin_token))
        score_before = resp1.get_json()["compliance_score"]["overall_score"]

        # Add patient + consent + records
        patient_token = register_and_login(client, "p@test.com", "patient")
        seed_data(client, patient_token, admin_token)

        resp2 = client.get("/api/v1/compliance/compliance-score", headers=auth(admin_token))
        score_after = resp2.get_json()["compliance_score"]["overall_score"]

        assert score_after >= score_before

    def test_grade_assigned_correctly(self, client):
        admin_token = register_and_login(client, "a@test.com", "admin")
        resp = client.get("/api/v1/compliance/compliance-score", headers=auth(admin_token))
        grade = resp.get_json()["compliance_score"]["grade"]
        assert grade in ("A", "B", "C", "D", "F")
