"""
Tests for Healthcare Records CRUD (Day 3).

Tests cover:
- Create healthcare record (patient creates own)
- Get single record (ownership enforced)
- List records (patient sees own, admin sees all)
- Update record (ownership enforced)
- Input validation
- Admin access to all patient records
"""

import pytest
from tests.accounts import create_test_account
from app import create_app
from app.extensions import get_db


@pytest.fixture
def app():
    """Create test application."""
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean test database before each test."""
    with app.app_context():
        db = get_db()
        db["users"].delete_many({})
        db["patients"].delete_many({})
        db["healthcare_records"].delete_many({})
    yield
    with app.app_context():
        db = get_db()
        db["users"].delete_many({})
        db["patients"].delete_many({})
        db["healthcare_records"].delete_many({})


def register_and_login(client, email, role="patient", full_name="Test User"):
    """Helper: register + login, return access token."""
    create_test_account(
        client, email=email, password="TestPass123", role=role, full_name=full_name,
    )
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "TestPass123",
    })
    return resp.get_json()["access_token"]


def auth_header(token):
    """Helper: create Authorization header."""
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────
# PATIENT PROFILE TESTS
# ─────────────────────────────────────────────────────────────────────

class TestPatientProfile:
    """Test patient profile operations."""

    def test_patient_profile_created_on_registration(self, client):
        token = register_and_login(client, "patient1@example.com")
        resp = client.get("/api/v1/patients/me", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["patient"]["full_name"] == "Test User"
        assert data["patient"]["user_id"] is not None

    def test_patient_can_update_profile(self, client):
        token = register_and_login(client, "patient1@example.com")
        resp = client.put("/api/v1/patients/me", json={
            "phone_number": "+91-9876543210",
            "blood_group": "O+",
            "allergies": ["Penicillin"],
        }, headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["patient"]["phone_number"] == "+91-9876543210"
        assert data["patient"]["blood_group"] == "O+"
        assert data["patient"]["allergies"] == ["Penicillin"]

    def test_admin_can_list_all_patients(self, client):
        register_and_login(client, "p1@example.com", "patient", "Patient One")
        register_and_login(client, "p2@example.com", "patient", "Patient Two")
        admin_token = register_and_login(client, "admin@example.com", "admin", "Admin")

        resp = client.get("/api/v1/patients/", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 2

    def test_patient_cannot_list_all_patients(self, client):
        token = register_and_login(client, "patient1@example.com")
        resp = client.get("/api/v1/patients/", headers=auth_header(token))
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────
# CREATE RECORD TESTS
# ─────────────────────────────────────────────────────────────────────

class TestCreateRecord:
    """Test healthcare record creation."""

    def test_patient_creates_own_record(self, client):
        token = register_and_login(client, "patient1@example.com")
        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Annual Checkup 2025",
            "description": "Patient came for routine annual health examination.",
            "diagnosis_codes": ["Z00.0"],
            "symptoms": ["none"],
            "treatment_notes": "All vitals normal. No intervention needed.",
        }, headers=auth_header(token))

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["record"]["record_type"] == "consultation"
        assert data["record"]["title"] == "Annual Checkup 2025"
        assert data["record"]["_id"] is not None  # UUID assigned
        assert data["record"]["version"] == 1

    def test_create_record_invalid_type(self, client):
        token = register_and_login(client, "patient1@example.com")
        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "invalid_type",
            "title": "Test Record",
            "description": "This should fail validation.",
        }, headers=auth_header(token))
        assert resp.status_code == 422
        assert "record_type" in resp.get_json().get("details", {})

    def test_create_record_missing_title(self, client):
        token = register_and_login(client, "patient1@example.com")
        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "",
            "description": "Description is present but title is missing.",
        }, headers=auth_header(token))
        assert resp.status_code == 422
        assert "title" in resp.get_json().get("details", {})

    def test_create_record_short_description(self, client):
        token = register_and_login(client, "patient1@example.com")
        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Valid Title",
            "description": "Short",
        }, headers=auth_header(token))
        assert resp.status_code == 422
        assert "description" in resp.get_json().get("details", {})

    def test_admin_creates_record_for_patient(self, client):
        patient_token = register_and_login(client, "p1@example.com", "patient")
        admin_token = register_and_login(client, "admin@example.com", "admin")

        # Get patient ID
        resp = client.get("/api/v1/patients/me", headers=auth_header(patient_token))
        patient_id = resp.get_json()["patient"]["_id"]

        # Admin creates record for that patient
        resp = client.post(f"/api/v1/patients/{patient_id}/records", json={
            "record_type": "diagnosis",
            "title": "Admin-Created Diagnosis",
            "description": "This record was created by an admin on behalf of the patient.",
        }, headers=auth_header(admin_token))
        assert resp.status_code == 201
        assert resp.get_json()["record"]["patient_id"] == patient_id


# ─────────────────────────────────────────────────────────────────────
# READ RECORD TESTS
# ─────────────────────────────────────────────────────────────────────

class TestReadRecords:
    """Test reading healthcare records."""

    def _create_record(self, client, token):
        """Helper: create a record and return its ID."""
        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Test Consultation",
            "description": "Patient visited for a follow-up consultation.",
        }, headers=auth_header(token))
        return resp.get_json()["record"]["_id"]

    def test_patient_lists_own_records(self, client):
        token = register_and_login(client, "patient1@example.com")
        self._create_record(client, token)
        self._create_record(client, token)

        resp = client.get("/api/v1/patients/me/records", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 2

    def test_patient_gets_single_record(self, client):
        token = register_and_login(client, "patient1@example.com")
        record_id = self._create_record(client, token)

        resp = client.get(f"/api/v1/patients/me/records/{record_id}",
                          headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["record"]["_id"] == record_id

    def test_patient_cannot_access_other_patients_record(self, client, app):
        # Patient 1 creates a record
        token1 = register_and_login(client, "p1@example.com", "patient", "Patient One")
        record_id = self._create_record(client, token1)

        # Patient 2 tries to access it
        token2 = register_and_login(client, "p2@example.com", "patient", "Patient Two")
        resp = client.get(f"/api/v1/patients/me/records/{record_id}",
                          headers=auth_header(token2))
        assert resp.status_code == 403

    def test_filter_records_by_type(self, client):
        token = register_and_login(client, "patient1@example.com")
        # Create two different types
        client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Consultation Record",
            "description": "A consultation record for filtering test.",
        }, headers=auth_header(token))
        client.post("/api/v1/patients/me/records", json={
            "record_type": "diagnosis",
            "title": "Diagnosis Record",
            "description": "A diagnosis record for filtering test purposes.",
        }, headers=auth_header(token))

        # Filter by consultation only
        resp = client.get("/api/v1/patients/me/records?type=consultation",
                          headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 1
        assert data["records"][0]["record_type"] == "consultation"

    def test_admin_lists_any_patient_records(self, client):
        patient_token = register_and_login(client, "p1@example.com", "patient")
        self._create_record(client, patient_token)

        # Get patient ID
        resp = client.get("/api/v1/patients/me", headers=auth_header(patient_token))
        patient_id = resp.get_json()["patient"]["_id"]

        # Admin lists that patient's records
        admin_token = register_and_login(client, "admin@example.com", "admin")
        resp = client.get(f"/api/v1/patients/{patient_id}/records",
                          headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 1

    def test_get_nonexistent_record_returns_404(self, client):
        token = register_and_login(client, "patient1@example.com")
        resp = client.get("/api/v1/patients/me/records/nonexistent-uuid",
                          headers=auth_header(token))
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────
# UPDATE RECORD TESTS
# ─────────────────────────────────────────────────────────────────────

class TestUpdateRecord:
    """Test healthcare record updates."""

    def _create_record(self, client, token):
        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Original Title",
            "description": "Original description for the consultation record.",
        }, headers=auth_header(token))
        return resp.get_json()["record"]["_id"]

    def test_patient_updates_own_record(self, client):
        token = register_and_login(client, "patient1@example.com")
        record_id = self._create_record(client, token)

        resp = client.put(f"/api/v1/patients/me/records/{record_id}", json={
            "title": "Updated Title",
            "treatment_notes": "Added treatment notes after update.",
        }, headers=auth_header(token))

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["record"]["title"] == "Updated Title"
        assert data["record"]["treatment_notes"] == "Added treatment notes after update."
        assert data["record"]["version"] == 2

    def test_patient_cannot_update_other_patients_record(self, client):
        token1 = register_and_login(client, "p1@example.com", "patient", "Patient One")
        record_id = self._create_record(client, token1)

        token2 = register_and_login(client, "p2@example.com", "patient", "Patient Two")
        resp = client.put(f"/api/v1/patients/me/records/{record_id}", json={
            "title": "Hacked Title",
        }, headers=auth_header(token2))
        assert resp.status_code == 403

    def test_update_with_no_valid_fields(self, client):
        token = register_and_login(client, "patient1@example.com")
        record_id = self._create_record(client, token)

        resp = client.put(f"/api/v1/patients/me/records/{record_id}", json={
            "_id": "attempted-id-change",
            "patient_id": "attempted-patient-change",
        }, headers=auth_header(token))
        assert resp.status_code == 422

    def test_version_increments_on_update(self, client):
        token = register_and_login(client, "patient1@example.com")
        record_id = self._create_record(client, token)

        # First update
        client.put(f"/api/v1/patients/me/records/{record_id}", json={
            "title": "V2 Title",
        }, headers=auth_header(token))

        # Second update
        resp = client.put(f"/api/v1/patients/me/records/{record_id}", json={
            "title": "V3 Title",
        }, headers=auth_header(token))
        assert resp.get_json()["record"]["version"] == 3
