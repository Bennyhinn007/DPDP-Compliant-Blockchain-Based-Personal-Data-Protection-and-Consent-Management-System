"""Tests for the admin fingerprint (SecuGen) login unlock.

Matching happens client-side in the SecuGen local service and the server trusts the
reported score (prototype limitation), so these tests submit scores directly.
"""
import base64
from datetime import datetime, timezone, timedelta

import pyotp
import pytest

from app import create_app
from app.config import BaseConfig
from app.extensions import get_db
from app.services.pending_login_service import PendingLoginService, _hash
from app.services.physical_presence_service import PhysicalPresenceService

TPL = base64.b64encode(b"FAKE-FINGERPRINT-TEMPLATE-0123456789").decode()
PW = "TestPass123"
TPL_URL = "/api/v1/auth/login/fingerprint/template"
VER_URL = "/api/v1/auth/login/fingerprint/verify"


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


def _make_admin(client, email, role="admin"):
    """Register and log in (a fresh account without MFA/fingerprint gets tokens)."""
    client.post("/api/v1/auth/register", json={
        "email": email, "password": PW, "role": role, "full_name": f"{role} user",
    })
    body = client.post("/api/v1/auth/login", json={"email": email, "password": PW}).get_json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


def _enroll(client, auth):
    r = client.post("/api/v1/biometric/enroll", headers=auth,
                    json={"template": TPL, "provider": "secugen", "quality": 90})
    assert r.status_code in (200, 201), r.get_json()


def _enable_totp(client, auth, app, uid):
    assert client.post("/api/v1/auth/mfa/setup", headers=auth).status_code == 200
    with app.app_context():
        secret = get_db()["users"].find_one({"_id": uid})["mfa_secret_pending"]
    r = client.post("/api/v1/auth/mfa/verify", headers=auth, json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200
    return secret


def _password_login(client, email, **extra):
    return client.post("/api/v1/auth/login", json={"email": email, "password": PW, **extra})


def _challenge(client, email):
    r = _password_login(client, email)
    assert r.status_code == 200
    return r.get_json()


def _fp_admin(client, email):
    auth, uid = _make_admin(client, email)
    _enroll(client, auth)
    return auth, uid


def test_fingerprint_only_challenge(client):
    _fp_admin(client, "bl_only@example.com")
    body = _challenge(client, "bl_only@example.com")
    assert "access_token" not in body and "refresh_token" not in body
    assert body["mfa_required"] is True
    assert body["mfa_methods"] == ["fingerprint"]
    assert body["pending_token"]


def test_fingerprint_and_totp_methods(client, app):
    auth, uid = _fp_admin(client, "bl_both@example.com")
    _enable_totp(client, auth, app, uid)
    body = _challenge(client, "bl_both@example.com")
    assert body["mfa_methods"] == ["totp", "fingerprint"]
    assert "access_token" not in body


def test_template_endpoint(client, app):
    _, uid = _fp_admin(client, "bl_tpl@example.com")
    token = _challenge(client, "bl_tpl@example.com")["pending_token"]
    r = client.post(TPL_URL, json={"pending_token": token})
    assert r.status_code == 200
    assert r.get_json()["template"] == TPL
    with app.app_context():
        doc = get_db()["biometric_templates"].find_one({"_id": uid})
    assert doc["template_enc"] != TPL
    assert client.post(TPL_URL, json={"pending_token": "nope"}).status_code == 401


def test_low_score_attempts_then_dead(client):
    _fp_admin(client, "bl_low@example.com")
    token = _challenge(client, "bl_low@example.com")["pending_token"]
    r = client.post(VER_URL, json={"pending_token": token, "score": 10, "provider": "secugen"})
    assert r.status_code == 403
    body = r.get_json()
    assert body["verified"] is False and body["attempts_left"] == 2
    assert "access_token" not in body
    for _ in range(2):
        client.post(VER_URL, json={"pending_token": token, "score": 10, "provider": "secugen"})
    r = client.post(VER_URL, json={"pending_token": token, "score": 10, "provider": "secugen"})
    assert r.status_code == 401
    r = client.post(VER_URL, json={"pending_token": token, "score": 150, "provider": "secugen"})
    assert r.status_code == 401


def test_good_score_issues_tokens_once(client, app):
    _, uid = _fp_admin(client, "bl_ok@example.com")
    token = _challenge(client, "bl_ok@example.com")["pending_token"]
    r = client.post(VER_URL, json={"pending_token": token, "score": 150, "provider": "secugen"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["role"] == "admin"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    with app.app_context():
        assert PhysicalPresenceService(get_db()).is_physically_present(uid)["present"] is True
    r = client.post(VER_URL, json={"pending_token": token, "score": 150, "provider": "secugen"})
    assert r.status_code == 401


def test_score_boundary(client):
    min_score = BaseConfig.BIOMETRIC_MIN_SCORE
    _fp_admin(client, "bl_bound@example.com")
    token = _challenge(client, "bl_bound@example.com")["pending_token"]
    r = client.post(VER_URL, json={"pending_token": token, "score": min_score - 1, "provider": "secugen"})
    assert r.status_code == 403
    r = client.post(VER_URL, json={"pending_token": token, "score": min_score, "provider": "secugen"})
    assert r.status_code == 200


def test_invalid_expired_and_missing_tokens(client, app):
    _, uid = _fp_admin(client, "bl_exp@example.com")
    for url in (TPL_URL, VER_URL):
        assert client.post(url, json={"pending_token": "garbage", "score": 150}).status_code == 401
        assert client.post(url, json={"score": 150}).status_code == 401
    expired = "expired-token-value"
    with app.app_context():
        get_db()["mfa_pending_logins"].insert_one({
            "_id": _hash(expired), "user_id": uid,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat(),
            "attempts": 0, "max_attempts": 3,
        })
    assert client.post(TPL_URL, json={"pending_token": expired}).status_code == 401
    assert client.post(VER_URL, json={"pending_token": expired, "score": 150}).status_code == 401


def test_totp_still_works_with_fingerprint_enrolled(client, app):
    auth, uid = _fp_admin(client, "bl_totp@example.com")
    secret = _enable_totp(client, auth, app, uid)
    r = _password_login(client, "bl_totp@example.com", mfa_code=pyotp.TOTP(secret).now())
    assert r.status_code == 200 and r.get_json()["access_token"]
    r = _password_login(client, "bl_totp@example.com", mfa_code="000000")
    assert r.status_code == 401


def test_admins_without_fingerprint_unchanged(client, app):
    auth, uid = _make_admin(client, "bl_nofp_totp@example.com")
    _enable_totp(client, auth, app, uid)
    body = _challenge(client, "bl_nofp_totp@example.com")
    assert body["mfa_required"] is True
    assert "pending_token" not in body and "access_token" not in body

    _make_admin(client, "bl_nofp_none@example.com")
    body = _challenge(client, "bl_nofp_none@example.com")
    assert body["access_token"]
    assert body["mfa_setup_required"] is True


def test_flag_off_restores_old_behaviour(client, monkeypatch):
    _fp_admin(client, "bl_off@example.com")
    token = _challenge(client, "bl_off@example.com")["pending_token"]
    monkeypatch.setattr(BaseConfig, "BIOMETRIC_LOGIN_ENABLED", False)
    body = _challenge(client, "bl_off@example.com")
    assert body["access_token"] and "pending_token" not in body
    assert client.post(TPL_URL, json={"pending_token": token}).status_code == 403
    assert client.post(VER_URL, json={"pending_token": token, "score": 150}).status_code == 403


def test_non_admin_pending_rejected(client, app):
    _, pid = _make_admin(client, "bl_patient@example.com", role="patient")
    with app.app_context():
        token = PendingLoginService(get_db()).create(pid)
    r = client.post(VER_URL, json={"pending_token": token, "score": 150, "provider": "secugen"})
    assert r.status_code == 401


def test_audit_rows(client, app):
    _, uid = _fp_admin(client, "bl_audit@example.com")
    token = _challenge(client, "bl_audit@example.com")["pending_token"]
    client.post(VER_URL, json={"pending_token": token, "score": 5, "provider": "secugen"})
    client.post(VER_URL, json={"pending_token": token, "score": 150, "provider": "secugen"})
    with app.app_context():
        rows = list(get_db()["audit_logs"].find({"resource_type": "biometric"}))
    reasons = [(r.get("severity"), r.get("reason", "")) for r in rows]
    assert any(s == "warning" and "FAILED" in why for s, why in reasons)
    assert any("Fingerprint login verified" in why for _, why in reasons)


def test_non_finite_score_rejected(client):
    _fp_admin(client, "bl_nan@example.com")
    token = _challenge(client, "bl_nan@example.com")["pending_token"]
    # Python's json (and Flask) accepts bare NaN/Infinity literals.
    for literal in ("NaN", "Infinity"):
        body = '{"pending_token": "%s", "score": %s, "provider": "secugen"}' % (token, literal)
        r = client.post(VER_URL, data=body, content_type="application/json")
        assert r.status_code == 422
        assert "access_token" not in (r.get_json() or {})


def test_invalid_pending_token_is_audited(client, app):
    r = client.post(VER_URL, json={"pending_token": "garbage", "score": 150, "provider": "secugen"})
    assert r.status_code == 401
    with app.app_context():
        rows = list(get_db()["audit_logs"].find({"resource_type": "biometric", "severity": "warning"}))
    assert any("invalid or expired pending token" in r.get("reason", "") for r in rows)
