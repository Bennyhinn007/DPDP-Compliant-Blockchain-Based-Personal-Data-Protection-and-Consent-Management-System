"""
Tests for SIH 26125 Phase 3 backend (ADDITIVE):
- AssetNFTService: metadata hashing, encryption round-trip, mint degradation
- assets/ blueprint: register (encrypted), list, get, RBAC
- nft/ blueprint: mint/assign/transfer fail closed (503) when chain unavailable,
  verify + list read-only (200), dual-auth (admin-only mint)
- blockchain/events endpoint (cached, chain-independent)

No running chain required — asserts the fail-closed / graceful behavior.
"""

import pytest

from app import create_app
from app.extensions import get_db
from app.services.asset_nft_service import AssetNFTService


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
    return resp.get_json()["access_token"]


# ─────────────────────────────────────────────────────────────────────
# AssetNFTService
# ─────────────────────────────────────────────────────────────────────

class TestAssetNFTService:
    def test_metadata_hash_deterministic_keccak(self, app):
        with app.app_context():
            m = {"name": "Radar", "spec": "X-band"}
            h1 = AssetNFTService.compute_metadata_hash(m)
            h2 = AssetNFTService.compute_metadata_hash({"spec": "X-band", "name": "Radar"})  # order-independent
            assert h1 == h2
            assert h1.startswith("0x") and len(h1) == 66

    def test_register_encrypts_metadata(self, app):
        with app.app_context():
            svc = AssetNFTService(get_db(), contract_service=None)
            asset = svc.register_asset("admin-1", "medical_device",
                                       {"name": "RX-9", "description": "secure", "spec": "v2"})
            # returned (decrypted) view is plaintext
            assert asset["name"] == "RX-9"
            # raw stored doc is ciphertext
            raw = get_db()["assets"].find_one({"_id": asset["_id"]})
            assert raw["name"] != "RX-9"
            assert raw["name"].startswith("gAAAAA")
            assert raw["metadata_hash"].startswith("0x")

    def test_mint_unavailable_without_chain(self, app):
        with app.app_context():
            svc = AssetNFTService(get_db(), contract_service=None)
            a = svc.register_asset("admin-1", "software_license", {"name": "Lic"})
            r = svc.mint(a["_id"], "did:rakshaid:x")
            assert r["ok"] is False and "unavailable" in r["reason"]

    def test_verify_missing_token(self, app):
        with app.app_context():
            svc = AssetNFTService(get_db(), contract_service=None)
            v = svc.verify_ownership(12345)
            assert v["found"] is False


# ─────────────────────────────────────────────────────────────────────
# assets/ blueprint
# ─────────────────────────────────────────────────────────────────────

class TestAssetsBlueprint:
    def test_register_and_list(self, client):
        token = _token(client, "assetadmin@example.com", "admin")
        auth = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/v1/assets", json={
            "asset_type": "medical_device", "metadata": {"name": "Radar RX-9", "spec": "X"},
        }, headers=auth)
        assert resp.status_code == 201
        asset = resp.get_json()["asset"]
        assert asset["name"] == "Radar RX-9"

        resp = client.get("/api/v1/assets", headers=auth)
        assert resp.status_code == 200
        assert len(resp.get_json()["assets"]) == 1

    def test_register_requires_privileged_role(self, client):
        token = _token(client, "assetpt@example.com", "patient")
        resp = client.post("/api/v1/assets", json={
            "asset_type": "medical_device", "metadata": {"name": "X"},
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403  # patient cannot register assets

    def test_register_validates_metadata(self, client):
        token = _token(client, "assetadmin2@example.com", "admin")
        resp = client.post("/api/v1/assets", json={"asset_type": "medical_device", "metadata": {}},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────
# nft/ blueprint — fail-closed writes, read-only reads
# ─────────────────────────────────────────────────────────────────────

class TestNftBlueprint:
    def test_mint_fails_closed_when_chain_down(self, client):
        token = _token(client, "nftadmin@example.com", "admin")
        auth = {"Authorization": f"Bearer {token}"}
        # register an asset first
        asset = client.post("/api/v1/assets", json={
            "asset_type": "medical_device", "metadata": {"name": "Dev"},
        }, headers=auth).get_json()["asset"]
        resp = client.post("/api/v1/nft/mint",
                           json={"asset_id": asset["_id"], "owner_did": "did:rakshaid:x"},
                           headers=auth)
        assert resp.status_code == 503
        assert resp.get_json()["chain_available"] is False

    def test_mint_requires_admin(self, client):
        token = _token(client, "nftpt@example.com", "patient")
        resp = client.post("/api/v1/nft/mint",
                           json={"asset_id": "x", "owner_did": "did:rakshaid:x"},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_verify_readonly_200_when_chain_down(self, client):
        token = _token(client, "nftadmin3@example.com", "admin")
        resp = client.get("/api/v1/nft/1/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["found"] is False
        assert body["chain_available"] is False

    def test_list_nfts_readonly(self, client):
        token = _token(client, "nftadmin4@example.com", "admin")
        resp = client.get("/api/v1/nft", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.get_json()["nfts"] == []


# ─────────────────────────────────────────────────────────────────────
# blockchain/events — cached, chain-independent
# ─────────────────────────────────────────────────────────────────────

class TestChainEvents:
    def test_events_endpoint_admin_only(self, client):
        admin = _token(client, "evtadmin@example.com", "admin")
        resp = client.get("/api/v1/blockchain/events", headers={"Authorization": f"Bearer {admin}"})
        assert resp.status_code == 200
        assert "events" in resp.get_json()

    def test_events_forbidden_for_patient(self, client):
        pt = _token(client, "evtpt@example.com", "patient")
        resp = client.get("/api/v1/blockchain/events", headers={"Authorization": f"Bearer {pt}"})
        assert resp.status_code == 403
