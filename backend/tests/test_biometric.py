"""Tests for the admin fingerprint (biometric) second factor."""

import base64
import pytest

from app import create_app
from app.extensions import get_db
from app.services.physical_presence_service import PhysicalPresenceService

TPL = base64.b64encode(b"FAKE-FINGERPRINT-TEMPLATE-0123456789").decode()


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, email, role="admin"):
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPass123", "role": role, "full_name": f"{role} user",
    })
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPass123"})
    body = r.get_json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


def _presence(app, uid):
    with app.app_context():
        PhysicalPresenceService(get_db()).record_presence(uid, card_id="test")


def _is_present(app, uid):
    with app.app_context():
        return PhysicalPresenceService(get_db()).is_physically_present(uid).get("present")


def _enroll(client, auth, provider="secugen"):
    return client.post("/api/v1/biometric/enroll", headers=auth,
                       json={"template": TPL, "provider": provider, "quality": 90})


def test_status_not_enrolled(client):
    auth, _ = _login(client, "bio_status@example.com")
    r = client.get("/api/v1/biometric/status", headers=auth)
    assert r.status_code == 200
    assert r.get_json()["enrolled"] is False


def test_non_admin_forbidden(client):
    auth, _ = _login(client, "bio_patient@example.com", "patient")
    assert client.get("/api/v1/biometric/status", headers=auth).status_code == 403


def test_enroll_encrypted_and_roundtrip(client, app):
    auth, uid = _login(client, "bio_enroll@example.com")
    assert _enroll(client, auth).status_code == 201
    with app.app_context():
        raw = get_db()["biometric_templates"].find_one({"_id": uid})
    assert raw["template_enc"] != TPL
    r = client.get("/api/v1/biometric/template", headers=auth)
    assert r.status_code == 200
    assert r.get_json()["template"] == TPL


def test_invalid_inputs(client):
    auth, _ = _login(client, "bio_invalid@example.com")
    r = client.post("/api/v1/biometric/enroll", headers=auth,
                    json={"template": TPL, "provider": "nope"})
    assert r.status_code == 422
    r = client.post("/api/v1/biometric/enroll", headers=auth,
                    json={"template": "!!!not-base64", "provider": "secugen"})
    assert r.status_code == 422


def test_reenroll_requires_presence(client, app):
    auth, uid = _login(client, "bio_reenroll@example.com")
    assert _enroll(client, auth).status_code == 201
    assert _enroll(client, auth).status_code == 403
    _presence(app, uid)
    assert _enroll(client, auth).status_code == 201


def test_verify_below_and_above_threshold(client, app):
    auth, uid = _login(client, "bio_verify@example.com")
    _enroll(client, auth)
    r = client.post("/api/v1/biometric/verify", headers=auth,
                    json={"score": 10, "provider": "secugen"})
    assert r.status_code == 403
    assert not _is_present(app, uid)
    r = client.post("/api/v1/biometric/verify", headers=auth,
                    json={"score": 150, "provider": "secugen"})
    assert r.status_code == 200
    assert r.get_json()["verified"] is True
    assert _is_present(app, uid)


def test_delete_requires_presence(client, app):
    auth, uid = _login(client, "bio_delete@example.com")
    _enroll(client, auth)
    assert client.delete("/api/v1/biometric/enroll", headers=auth).status_code == 403
    _presence(app, uid)
    r = client.delete("/api/v1/biometric/enroll", headers=auth)
    assert r.status_code == 200
    assert r.get_json()["removed"] is True
