"""
Tests for Authentication & RBAC (Day 2).

Tests cover:
- User registration (validation, duplicate, success)
- Login (success, invalid credentials, lockout)
- JWT verification (valid, expired, missing)
- RBAC (admin-only, patient-only, unauthorized)
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
    yield
    with app.app_context():
        db = get_db()
        db["users"].delete_many({})


# ─────────────────────────────────────────────────────────────────────
# REGISTRATION TESTS
# ─────────────────────────────────────────────────────────────────────

class TestRegistration:
    """Test user registration endpoint."""

    def test_register_patient_success(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "patient@example.com",
            "password": "SecurePass123",
            "role": "patient",
            "full_name": "Rajesh Kumar",
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Registration successful"
        assert data["user"]["role"] == "patient"
        assert data["user"]["email"] == "patient@example.com"
        assert "id" in data["user"]  # UUID present

    @pytest.mark.parametrize("role", ["admin", "doctor", "registration_staff", "dpo", "pharmacy_staff"])
    def test_public_signup_rejects_staff_roles(self, client, role):
        response = client.post("/api/v1/auth/register", json={
            "email": "staff@example.invalid", "password": "ExamplePass123",
            "role": role, "full_name": "Hospital Staff",
        })
        assert response.status_code == 422
        assert get_db()["users"].count_documents({}) == 0

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass123",
            "role": "patient",
            "full_name": "Test User",
        })
        assert response.status_code == 422
        data = response.get_json()
        assert "email" in data.get("details", {})

    def test_register_short_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "user@example.com",
            "password": "short",
            "role": "patient",
            "full_name": "Test User",
        })
        assert response.status_code == 422
        data = response.get_json()
        assert "password" in data.get("details", {})

    def test_register_invalid_role(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "user@example.com",
            "password": "SecurePass123",
            "role": "superuser",  # Invalid role (not patient/admin/doctor)
            "full_name": "Test User",
        })
        assert response.status_code == 422
        data = response.get_json()
        assert "role" in data.get("details", {})

    def test_register_duplicate_email(self, client):
        # First registration
        client.post("/api/v1/auth/register", json={
            "email": "duplicate@example.com",
            "password": "SecurePass123",
            "role": "patient",
            "full_name": "First User",
        })
        # Second registration with same email
        response = client.post("/api/v1/auth/register", json={
            "email": "duplicate@example.com",
            "password": "AnotherPass456",
            "role": "patient",
            "full_name": "Second User",
        })
        assert response.status_code == 422
        assert "already registered" in response.get_json()["message"]

    def test_register_empty_body(self, client):
        response = client.post("/api/v1/auth/register",
                               data="", content_type="application/json")
        assert response.status_code in (400, 422)  # Flask returns 400 for malformed JSON


# ─────────────────────────────────────────────────────────────────────
# LOGIN TESTS
# ─────────────────────────────────────────────────────────────────────

class TestLogin:
    """Test login endpoint."""

    def _register_user(self, client):
        """Helper: register a test user."""
        client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "TestPass123",
            "role": "patient",
            "full_name": "Test Patient",
        })

    def test_login_success(self, client):
        self._register_user(client)
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["user"]["role"] == "patient"

    def test_login_wrong_password(self, client):
        self._register_user(client)
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword",
        })
        assert response.status_code == 401
        assert "Invalid" in response.get_json()["message"]

    def test_login_nonexistent_email(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "SomePass123",
        })
        assert response.status_code == 401

    def test_login_empty_credentials(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "",
            "password": "",
        })
        assert response.status_code == 401

    def test_account_lockout_after_5_failures(self, client, app):
        self._register_user(client)
        # 3 failed attempts (MAX_LOGIN_ATTEMPTS=3 in config)
        for _ in range(3):
            client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "WrongPassword",
            })
        # 6th attempt should report lockout
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123",  # Even correct password blocked
        })
        assert response.status_code == 401
        assert "locked" in response.get_json()["message"].lower()


# ─────────────────────────────────────────────────────────────────────
# JWT TESTS
# ─────────────────────────────────────────────────────────────────────

class TestHospitalRegistration:
    @pytest.mark.parametrize("role", ["doctor", "registration_staff", "admin", "dpo", "pharmacy_staff", "patient"])
    def test_admin_provisions_account(self, client, role):
        create_test_account(client, email="admin@example.invalid", password="ExamplePass123",
                            role="admin", full_name="Hospital Admin")
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@example.invalid", "password": "ExamplePass123",
        })
        admin = login.json
        account = {"email": "new@example.invalid", "password": "InitialPass123",
                   "full_name": "New User", "role": role}
        response = client.post("/api/v1/patients/register", json=account,
                               headers={"Authorization": "Bearer " + admin["access_token"]})
        assert response.status_code == 201
        assert response.json["role"] == role
        assert bool(response.json["patient_id"]) == (role == "patient")
        assert "password" not in response.json
        assert get_db().audit_logs.find_one({
            "actor_id": admin["user"]["id"], "resource_id": response.json["user_id"],
            "details.registered_role": role,
        })
        new_login = client.post("/api/v1/auth/login", json={
            "email": account["email"], "password": account["password"],
        })
        assert new_login.json["user"]["role"] == role

    def test_front_desk_registers_patients_only(self, client):
        create_test_account(client, email="desk@example.invalid", password="ExamplePass123",
                            role="registration_staff", full_name="Registration Desk")
        login = client.post("/api/v1/auth/login", json={
            "email": "desk@example.invalid", "password": "ExamplePass123",
        })
        headers = {"Authorization": "Bearer " + login.json["access_token"]}
        account = {"email": "new@example.invalid", "password": "InitialPass123", "full_name": "New User"}
        for role in ["doctor", "registration_staff", "admin", "dpo", "pharmacy_staff"]:
            response = client.post("/api/v1/patients/register", json={**account, "role": role}, headers=headers)
            assert response.status_code == 403
        response = client.post("/api/v1/patients/register", json=account, headers=headers)
        assert response.status_code == 201
        assert response.json["patient_id"]


class TestJWT:
    """Test JWT authentication."""

    def _get_token(self, client, role="patient"):
        """Helper: register + login, return access token."""
        email = f"{role}@example.com"
        create_test_account(
            client, email=email, password="TestPass123", role=role, full_name=f"Test {role.title()}",
        )
        resp = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "TestPass123",
        })
        return resp.get_json()["access_token"]

    def test_protected_endpoint_with_valid_token(self, client):
        token = self._get_token(client)
        response = client.get("/api/v1/auth/protected-test",
                              headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "JWT authentication successful"
        assert data["role"] == "patient"

    def test_protected_endpoint_no_token(self, client):
        response = client.get("/api/v1/auth/protected-test")
        assert response.status_code == 401

    def test_protected_endpoint_invalid_token(self, client):
        response = client.get("/api/v1/auth/protected-test",
                              headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401

    def test_get_current_user(self, client):
        token = self._get_token(client)
        response = client.get("/api/v1/auth/me",
                              headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["role"] == "patient"
        assert data["user"]["email"] == "patient@example.com"


# ─────────────────────────────────────────────────────────────────────
# RBAC TESTS
# ─────────────────────────────────────────────────────────────────────

class TestRBAC:
    """Test Role-Based Access Control."""

    def _get_token(self, client, role):
        """Helper: register + login, return access token."""
        email = f"{role}user@example.com"
        create_test_account(
            client, email=email, password="TestPass123", role=role, full_name=f"Test {role.title()}",
        )
        resp = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "TestPass123",
        })
        return resp.get_json()["access_token"]

    def test_admin_can_access_admin_endpoint(self, client):
        token = self._get_token(client, "admin")
        response = client.get("/api/v1/auth/admin-only",
                              headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.get_json()["message"] == "Admin access granted"

    def test_patient_cannot_access_admin_endpoint(self, client):
        token = self._get_token(client, "patient")
        response = client.get("/api/v1/auth/admin-only",
                              headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert "denied" in response.get_json()["message"].lower()

    def test_patient_can_access_patient_endpoint(self, client):
        token = self._get_token(client, "patient")
        response = client.get("/api/v1/auth/patient-only",
                              headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.get_json()["message"] == "Patient access granted"

    def test_admin_cannot_access_patient_endpoint(self, client):
        token = self._get_token(client, "admin")
        response = client.get("/api/v1/auth/patient-only",
                              headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
