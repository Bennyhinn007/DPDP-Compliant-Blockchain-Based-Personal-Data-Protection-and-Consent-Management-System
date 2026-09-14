"""
Tests for SIH 26125 Phase 4 (ADDITIVE) — security hardening & optional gates.

Covers:
- Optional RFID physical-presence gate on high-risk SIH ops (NFT mint, DID revoke):
    * OFF by default → does NOT block (never affects healthcare/normal flow)
    * ON + no valid tap → 403 requires_physical_verification
    * ON + valid tap → passes the gate (proceeds to normal handling)
- No-PHI-on-chain guard on asset registration (service + endpoint)
- Optional consent<->DID bridge:
    * absent → consent works exactly as before (fields null)
    * valid DIDs → stored on the consent
    * malformed DID → rejected (422)
- Unauthorized paths remain protected (auth + role enforcement)

No running chain required — asserts fail-closed / graceful behavior.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app import create_app
from app.extensions import get_db
from app.config import get_config
from app.services.asset_nft_service import AssetNFTService, PHINotAllowedError


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


def _token(client, email, role):
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPass123", "role": role, "full_name": f"{role} user",
    })
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPass123"})
    return resp.get_json()["access_token"], resp.get_json()["user"]["id"]


def _enable_rfid_gate(monkeypatch, enabled=True):
    """Toggle the SIH_RFID_GATE_ENABLED flag on the testing config class."""
    cfg = get_config("testing")
    monkeypatch.setattr(cfg, "SIH_RFID_GATE_ENABLED", enabled, raising=False)


def _grant_presence(app, user_id):
    """Insert a valid, unexpired physical-presence token for the user (RFID tap)."""
    from app.services.physical_presence_service import PhysicalPresenceService
    with app.app_context():
        PhysicalPresenceService(get_db()).record_presence(user_id, card_id="test-card")


# ─────────────────────────────────────────────────────────────────────
# RFID gate — default OFF (never blocks)
# ─────────────────────────────────────────────────────────────────────

class TestRfidGateDefaultOff:
    def test_gate_off_by_default_config(self):
        assert get_config("testing").SIH_RFID_GATE_ENABLED is False

    def test_helper_returns_none_when_disabled(self, app):
        from app.services.physical_presence_service import check_optional_physical_presence
        with app.app_context():
            assert check_optional_physical_presence(get_db(), "user-x", False) is None

    def test_mint_not_blocked_by_gate_when_disabled(self, client):
        """Gate off → mint reaches the normal chain-down fail-closed path (503, not 403)."""
        token, _ = _token(client, "p4_mint_off@example.com", "admin")
        auth = {"Authorization": f"Bearer {token}"}
        asset = client.post("/api/v1/assets", json={
            "asset_type": "medical_device", "metadata": {"name": "Dev"},
        }, headers=auth).get_json()["asset"]
        resp = client.post("/api/v1/nft/mint",
                           json={"asset_id": asset["_id"], "owner_did": "did:rakshaid:x"},
                           headers=auth)
        assert resp.status_code == 503  # chain-down, NOT gated
        assert resp.get_json()["chain_available"] is False


# ─────────────────────────────────────────────────────────────────────
# RFID gate — ON (blocks high-risk ops without a tap)
# ─────────────────────────────────────────────────────────────────────

class TestRfidGateEnabled:
    def test_mint_blocked_without_tap_when_enabled(self, client, monkeypatch):
        _enable_rfid_gate(monkeypatch, True)
        token, _ = _token(client, "p4_mint_on@example.com", "admin")
        auth = {"Authorization": f"Bearer {token}"}
        asset = client.post("/api/v1/assets", json={
            "asset_type": "medical_device", "metadata": {"name": "Dev"},
        }, headers=auth).get_json()["asset"]
        resp = client.post("/api/v1/nft/mint",
                           json={"asset_id": asset["_id"], "owner_did": "did:rakshaid:x"},
                           headers=auth)
        assert resp.status_code == 403
        body = resp.get_json()
        assert body.get("requires_physical_verification") is True

    def test_mint_passes_gate_with_valid_tap(self, client, app, monkeypatch):
        _enable_rfid_gate(monkeypatch, True)
        token, user_id = _token(client, "p4_mint_tap@example.com", "admin")
        auth = {"Authorization": f"Bearer {token}"}
        asset = client.post("/api/v1/assets", json={
            "asset_type": "medical_device", "metadata": {"name": "Dev"},
        }, headers=auth).get_json()["asset"]
        _grant_presence(app, user_id)  # simulate an RFID tap
        resp = client.post("/api/v1/nft/mint",
                           json={"asset_id": asset["_id"], "owner_did": "did:rakshaid:x"},
                           headers=auth)
        # Gate passed → proceeds to normal chain-down fail-closed (503), NOT 403.
        assert resp.status_code == 503
        assert resp.get_json()["chain_available"] is False

    def test_did_revoke_blocked_without_tap_when_enabled(self, client, app, monkeypatch):
        _enable_rfid_gate(monkeypatch, True)
        token, _ = _token(client, "p4_revoke_on@example.com", "admin")
        auth = {"Authorization": f"Bearer {token}"}
        # Create a DID to revoke.
        from app.services.did_service import DIDService
        with app.app_context():
            kp = DIDService(get_db()).generate_keypair()
        did = client.post("/api/v1/did", json={"public_key": kp["public_key"]}, headers=auth).get_json()["did"]
        resp = client.post(f"/api/v1/did/{did}/revoke", headers=auth)
        assert resp.status_code == 403
        assert resp.get_json().get("requires_physical_verification") is True


# ─────────────────────────────────────────────────────────────────────
# No-PHI-on-chain guard
# ─────────────────────────────────────────────────────────────────────

class TestNoPhiGuard:
    def test_service_rejects_phi_metadata(self, app):
        with app.app_context():
            svc = AssetNFTService(get_db(), contract_service=None)
            with pytest.raises(PHINotAllowedError):
                svc.register_asset("admin-1", "medical_device",
                                   {"name": "X", "diagnosis": "hypertension"})

    def test_service_allows_clean_metadata(self, app):
        with app.app_context():
            svc = AssetNFTService(get_db(), contract_service=None)
            asset = svc.register_asset("admin-1", "medical_device", {"name": "MRI", "spec": "1.5T"})
            assert asset["name"] == "MRI"

    def test_endpoint_rejects_phi(self, client):
        token, _ = _token(client, "p4_phi@example.com", "admin")
        resp = client.post("/api/v1/assets", json={
            "asset_type": "medical_device",
            "metadata": {"name": "Record", "patient_id": "p-123", "prescription": "drug"},
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422  # ValidationError → no-PHI guard


# ─────────────────────────────────────────────────────────────────────
# Optional consent<->DID bridge
# ─────────────────────────────────────────────────────────────────────

class TestConsentDidBridge:
    def _patient_auth(self, client, email):
        token, _ = _token(client, email, "patient")
        return {"Authorization": f"Bearer {token}"}

    def test_consent_works_without_dids(self, client):
        auth = self._patient_auth(client, "p4_c_nodid@example.com")
        resp = client.post("/api/v1/consents/grant", json={
            "consent_type": "healthcare_treatment",
            "processing_entity_name": "Apollo",
        }, headers=auth)
        assert resp.status_code == 201
        consent = resp.get_json()["consent"]
        assert consent.get("patient_did") is None
        assert consent.get("doctor_did") is None

    def test_consent_stores_valid_dids(self, client):
        auth = self._patient_auth(client, "p4_c_did@example.com")
        resp = client.post("/api/v1/consents/grant", json={
            "consent_type": "healthcare_treatment",
            "processing_entity_name": "Apollo",
            "patient_did": "did:rakshaid:abc123",
            "doctor_did": "did:rakshaid:doc456",
        }, headers=auth)
        assert resp.status_code == 201
        consent = resp.get_json()["consent"]
        assert consent["patient_did"] == "did:rakshaid:abc123"
        assert consent["doctor_did"] == "did:rakshaid:doc456"

    def test_consent_rejects_malformed_did(self, client):
        auth = self._patient_auth(client, "p4_c_bad@example.com")
        resp = client.post("/api/v1/consents/grant", json={
            "consent_type": "healthcare_treatment",
            "processing_entity_name": "Apollo",
            "patient_did": "not-a-did",
        }, headers=auth)
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────
# Unauthorized paths remain protected
# ─────────────────────────────────────────────────────────────────────

class TestUnauthorizedPaths:
    def test_mint_requires_auth(self, client):
        resp = client.post("/api/v1/nft/mint", json={"asset_id": "x", "owner_did": "did:rakshaid:x"})
        assert resp.status_code == 401

    def test_asset_register_requires_privileged_role(self, client):
        token, _ = _token(client, "p4_unauth_pt@example.com", "patient")
        resp = client.post("/api/v1/assets", json={
            "asset_type": "medical_device", "metadata": {"name": "X"},
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_did_revoke_requires_privileged_role(self, client, app):
        # A patient (non-admin/dpo) cannot revoke.
        token, _ = _token(client, "p4_unauth_revoke@example.com", "patient")
        resp = client.post("/api/v1/did/did:rakshaid:whatever/revoke",
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
