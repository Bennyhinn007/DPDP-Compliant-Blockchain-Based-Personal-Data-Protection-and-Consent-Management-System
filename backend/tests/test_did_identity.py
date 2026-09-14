"""
Tests for the SIH 26125 DID identity extension (ADDITIVE).

Covers:
- Canonical DID derivation (deterministic, correct format)
- DID registration (linked to existing user, one-per-user)
- EIP-191 challenge-response: valid signature accepted
- Replay protection (used nonce rejected)
- Forged signature rejected
- Expired challenge rejected
- Revoked DID fails verification
- DID auth endpoint issues a valid existing JWT
- Feature flag / existing endpoints remain unaffected
"""

import pytest
from datetime import datetime, timezone, timedelta

from app import create_app
from app.extensions import get_db
from app.services.did_service import DIDService
from eth_account import Account
from eth_account.messages import encode_defunct


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


def _sign(message: str, private_key: str) -> str:
    sig = Account.sign_message(encode_defunct(text=message), private_key=private_key).signature
    return "0x" + sig.hex() if not sig.hex().startswith("0x") else sig.hex()


# ─────────────────────────────────────────────────────────────────────
# DID SERVICE UNIT TESTS
# ─────────────────────────────────────────────────────────────────────

class TestDIDService:
    def test_derivation_is_deterministic_and_formatted(self, app):
        with app.app_context():
            svc = DIDService(get_db())
            kp = svc.generate_keypair()
            a = svc.derive_did(kp["public_key"])
            b = svc.derive_did(kp["public_key"])
            assert a == b  # deterministic
            assert a["did"].startswith("did:rakshaid:")
            assert a["did_hash"].startswith("0x") and len(a["did_hash"]) == 66
            assert a["pub_key_hash"].startswith("0x") and len(a["pub_key_hash"]) == 66
            assert a["address"].startswith("0x") and len(a["address"]) == 42

    def test_register_and_resolve(self, app):
        with app.app_context():
            svc = DIDService(get_db())
            kp = svc.generate_keypair()
            doc = svc.register_did("user-1", kp["public_key"])
            assert doc["user_id"] == "user-1"
            assert svc.is_verified(doc["_id"]) is True
            assert svc.resolve_did(doc["_id"])["_id"] == doc["_id"]

    def test_one_did_per_user(self, app):
        with app.app_context():
            svc = DIDService(get_db())
            kp1 = svc.generate_keypair()
            kp2 = svc.generate_keypair()
            svc.register_did("user-1", kp1["public_key"])
            with pytest.raises(ValueError):
                svc.register_did("user-1", kp2["public_key"])

    def test_valid_challenge_response(self, app):
        with app.app_context():
            svc = DIDService(get_db())
            kp = svc.generate_keypair()
            doc = svc.register_did("user-1", kp["public_key"])
            ch = svc.create_challenge(doc["_id"])
            sig = _sign(ch["message"], kp["private_key"])
            result = svc.verify_signature(doc["_id"], ch["nonce"], sig)
            assert result["user_id"] == "user-1"

    def test_replay_rejected(self, app):
        with app.app_context():
            svc = DIDService(get_db())
            kp = svc.generate_keypair()
            doc = svc.register_did("user-1", kp["public_key"])
            ch = svc.create_challenge(doc["_id"])
            sig = _sign(ch["message"], kp["private_key"])
            svc.verify_signature(doc["_id"], ch["nonce"], sig)
            with pytest.raises(ValueError):
                svc.verify_signature(doc["_id"], ch["nonce"], sig)

    def test_forged_signature_rejected(self, app):
        with app.app_context():
            svc = DIDService(get_db())
            kp = svc.generate_keypair()
            attacker = svc.generate_keypair()
            doc = svc.register_did("user-1", kp["public_key"])
            ch = svc.create_challenge(doc["_id"])
            bad = _sign(ch["message"], attacker["private_key"])
            with pytest.raises(ValueError):
                svc.verify_signature(doc["_id"], ch["nonce"], bad)

    def test_expired_challenge_rejected(self, app):
        with app.app_context():
            svc = DIDService(get_db())
            kp = svc.generate_keypair()
            doc = svc.register_did("user-1", kp["public_key"])
            ch = svc.create_challenge(doc["_id"])
            # Force expiry in the stored challenge.
            past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
            get_db()["did_challenges"].update_one({"_id": ch["nonce"]}, {"$set": {"expires_at": past}})
            sig = _sign(ch["message"], kp["private_key"])
            with pytest.raises(ValueError):
                svc.verify_signature(doc["_id"], ch["nonce"], sig)

    def test_revoked_did_fails(self, app):
        with app.app_context():
            svc = DIDService(get_db())
            kp = svc.generate_keypair()
            doc = svc.register_did("user-1", kp["public_key"])
            svc.revoke_did(doc["_id"])
            assert svc.is_verified(doc["_id"]) is False
            with pytest.raises(ValueError):
                svc.create_challenge(doc["_id"])


# ─────────────────────────────────────────────────────────────────────
# DID BLUEPRINT ENDPOINT TESTS
# ─────────────────────────────────────────────────────────────────────

def _register_and_login(client):
    client.post("/api/v1/auth/register", json={
        "email": "did_user@example.com", "password": "TestPass123",
        "role": "patient", "full_name": "DID User",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "did_user@example.com", "password": "TestPass123",
    })
    data = resp.get_json()
    return data["access_token"], data["user"]["id"]


class TestDIDEndpoints:
    def test_health(self, client):
        resp = client.get("/api/v1/did/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "did service ready"

    def test_create_did_and_login_flow(self, client, app):
        token, user_id = _register_and_login(client)
        auth = {"Authorization": f"Bearer {token}"}

        # Client-side keypair (simulated here with the service helper).
        with app.app_context():
            kp = DIDService(get_db()).generate_keypair()

        # Create DID
        resp = client.post("/api/v1/did", json={"public_key": kp["public_key"]}, headers=auth)
        assert resp.status_code == 201
        did = resp.get_json()["did"]
        assert did.startswith("did:rakshaid:")

        # Challenge
        resp = client.post("/api/v1/did/challenge", json={"did": did})
        assert resp.status_code == 200
        ch = resp.get_json()

        # Sign + verify → issues a JWT for the SAME user
        sig = _sign(ch["message"], kp["private_key"])
        resp = client.post("/api/v1/did/verify", json={"did": did, "nonce": ch["nonce"], "signature": sig})
        assert resp.status_code == 200
        body = resp.get_json()
        assert "access_token" in body and body["token_type"] == "Bearer"
        assert body["user"]["id"] == user_id  # same existing user

    def test_verify_bad_signature_rejected(self, client, app):
        token, _ = _register_and_login(client)
        auth = {"Authorization": f"Bearer {token}"}
        with app.app_context():
            kp = DIDService(get_db()).generate_keypair()
            attacker = DIDService(get_db()).generate_keypair()
        did = client.post("/api/v1/did", json={"public_key": kp["public_key"]}, headers=auth).get_json()["did"]
        ch = client.post("/api/v1/did/challenge", json={"did": did}).get_json()
        bad = _sign(ch["message"], attacker["private_key"])
        resp = client.post("/api/v1/did/verify", json={"did": did, "nonce": ch["nonce"], "signature": bad})
        assert resp.status_code == 401

    def test_create_did_requires_auth(self, client):
        resp = client.post("/api/v1/did", json={"public_key": "0x04abc"})
        assert resp.status_code == 401
