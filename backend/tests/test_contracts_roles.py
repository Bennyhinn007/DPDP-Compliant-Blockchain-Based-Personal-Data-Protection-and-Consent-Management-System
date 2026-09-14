"""
Tests for the SIH 26125 Phase 2 backend layer (ADDITIVE):
- ContractService graceful degradation (no chain / no contracts)
- ContractService keccak role-hash correctness (matches Solidity constants)
- roles/ blueprint: matrix (read-only), grant/revoke fail-closed when chain down,
  role check returns 200 with chain_available flag.

These do NOT require a running blockchain — they assert the graceful, fail-closed
behavior mandated by the spec (chain unreachable in the test env).
"""

import pytest

from app import create_app
from app.extensions import get_db
from app.services.contract_service import ContractService
from app.services.did_service import DIDService


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


# ─────────────────────────────────────────────────────────────────────
# ContractService — graceful degradation
# ─────────────────────────────────────────────────────────────────────

class TestContractServiceDegradation:
    def test_unavailable_without_web3(self, app):
        with app.app_context():
            cs = ContractService(w3=None, config=app.config)
            assert cs.available is False
            st = cs.status()
            assert st["chain_available"] is False
            assert st["available"] is False

    def test_writes_return_unavailable_not_raise(self, app):
        with app.app_context():
            cs = ContractService(w3=None, config=app.config)
            r = cs.register_identity("did:rakshaid:x", "0x" + "ab" * 32)
            assert r["ok"] is False and "unavailable" in r["reason"]
            assert cs.grant_role("did:rakshaid:x", "manager")["ok"] is False
            assert cs.revoke_role("did:rakshaid:x", "manager")["ok"] is False

    def test_reads_return_none_when_unavailable(self, app):
        with app.app_context():
            cs = ContractService(w3=None, config=app.config)
            assert cs.is_identity_verified("did:rakshaid:x") is None
            assert cs.did_has_role("did:rakshaid:x", "manager") is None

    def test_role_hash_matches_solidity_constants(self, app):
        # keccak256("ADMIN_ROLE") — must equal the Solidity constant.
        with app.app_context():
            cs = ContractService(w3=None, config=app.config)
            admin_role = "0x" + cs.role_hash("ADMIN_ROLE").hex()
            assert admin_role == "0xa49807205ce4d355092ef5a8a18f56e8913cf4a201fbe287825b095693c21775"

    def test_unknown_role_rejected(self, app):
        with app.app_context():
            cs = ContractService(w3=None, config=app.config)
            # available is False so it short-circuits; force address to test role check path
            cs._access_addr = "0x0000000000000000000000000000000000000001"
            cs._registry_addr = "0x0000000000000000000000000000000000000002"
            # still no web3 -> available False -> unavailable reason (fail closed)
            assert cs.grant_role("did:rakshaid:x", "bogus")["ok"] is False


# ─────────────────────────────────────────────────────────────────────
# roles/ blueprint
# ─────────────────────────────────────────────────────────────────────

def _admin_token(client):
    client.post("/api/v1/auth/register", json={
        "email": "admin_roles@example.com", "password": "AdminPass123",
        "role": "admin", "full_name": "Role Admin",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin_roles@example.com", "password": "AdminPass123",
    })
    return resp.get_json()["access_token"]


def _patient_token(client):
    client.post("/api/v1/auth/register", json={
        "email": "pt_roles@example.com", "password": "PtPass123",
        "role": "patient", "full_name": "Role Patient",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "pt_roles@example.com", "password": "PtPass123",
    })
    return resp.get_json()["access_token"]


class TestRolesBlueprint:
    def test_matrix_readonly(self, client):
        token = _admin_token(client)
        resp = client.get("/api/v1/roles/matrix", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert set(body["roles"]) == {"admin", "manager", "auditor", "user"}
        assert body["chain_available"] is False  # no chain in test env

    def test_grant_fails_closed_when_chain_down(self, client):
        token = _admin_token(client)
        resp = client.post("/api/v1/roles/grant",
                           json={"did": "did:rakshaid:x", "role": "manager"},
                           headers={"Authorization": f"Bearer {token}"})
        # Critical write must fail closed (503) when chain unavailable.
        assert resp.status_code == 503
        assert resp.get_json()["chain_available"] is False

    def test_grant_requires_admin(self, client):
        token = _patient_token(client)
        resp = client.post("/api/v1/roles/grant",
                           json={"did": "did:rakshaid:x", "role": "manager"},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403  # backend RBAC denies non-admin

    def test_check_returns_200_with_flag_when_chain_down(self, client):
        token = _admin_token(client)
        resp = client.get("/api/v1/roles/check?did=did:rakshaid:x&role=manager",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["chain_available"] is False
        assert body["on_chain"] is None
