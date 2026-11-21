"""
Tests for Blockchain Anchoring (Day 7).

Tests cover:
- Hash computation (deterministic, changes on modification)
- Anchor creation (stored in blockchain_anchors collection)
- Verification (VERIFIED, INTEGRITY_VIOLATION, NO_ANCHOR)
- Integration with healthcare record CRUD
- API endpoint for verification

Note: Tests work with or without Ganache running.
If Ganache is not available, anchors are stored with transaction_status="failed"
but the verification logic still works against the stored hash.
"""

from unittest.mock import MagicMock

import pytest
from app import create_app
from app.extensions import get_db, get_web3
from app.services.blockchain_service import BlockchainService


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
        for col in ["users", "patients", "healthcare_records",
                    "blockchain_anchors", "consents", "consent_receipts",
                    "audit_logs"]:
            db[col].delete_many({})
    yield
    with app.app_context():
        db = get_db()
        for col in ["users", "patients", "healthcare_records",
                    "blockchain_anchors", "consents", "consent_receipts",
                    "audit_logs"]:
            db[col].delete_many({})


def register_and_login(client, email="bc_test@example.com"):
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPass123",
        "role": "patient", "full_name": "BC Test",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": email, "password": "TestPass123",
    })
    return resp.get_json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────
# HASH COMPUTATION TESTS
# ─────────────────────────────────────────────────────────────────────

class TestHashComputation:
    """Test SHA-256 hash computation for records."""

    def test_same_record_produces_same_hash(self):
        record = {"_id": "r1", "title": "Test", "description": "Desc", "version": 1}
        h1 = BlockchainService.compute_record_hash(record)
        h2 = BlockchainService.compute_record_hash(record)
        assert h1 == h2

    def test_different_record_produces_different_hash(self):
        r1 = {"_id": "r1", "title": "Test", "version": 1}
        r2 = {"_id": "r1", "title": "Modified", "version": 1}
        h1 = BlockchainService.compute_record_hash(r1)
        h2 = BlockchainService.compute_record_hash(r2)
        assert h1 != h2

    def test_verification_hash_field_excluded(self):
        r1 = {"_id": "r1", "title": "Test", "verification_hash": None}
        r2 = {"_id": "r1", "title": "Test", "verification_hash": "abc123"}
        h1 = BlockchainService.compute_record_hash(r1)
        h2 = BlockchainService.compute_record_hash(r2)
        assert h1 == h2

    def test_hash_is_valid_sha256(self):
        record = {"_id": "r1", "data": "test"}
        h = BlockchainService.compute_record_hash(record)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ─────────────────────────────────────────────────────────────────────
# ANCHOR CREATION TESTS
# ─────────────────────────────────────────────────────────────────────

class TestAnchorCreation:
    """Test blockchain anchor document creation."""

    def test_anchor_stored_in_collection(self, app):
        with app.app_context():
            db = get_db()
            bc = BlockchainService(db, get_web3())

            anchor = bc.anchor_record(
                resource_type="healthcare_records",
                resource_id="record-123",
                data_hash="a" * 64,
                patient_id="patient-456",
            )

            assert anchor["_id"] is not None
            assert anchor["resource_type"] == "healthcare_records"
            assert anchor["resource_id"] == "record-123"
            assert anchor["data_hash"] == "a" * 64
            assert anchor["patient_id"] == "patient-456"
            assert anchor["anchor_type"] == "record_verification"

            # Verify stored in DB
            stored = db["blockchain_anchors"].find_one({"_id": anchor["_id"]})
            assert stored is not None
            assert stored["data_hash"] == "a" * 64

    def test_anchor_includes_ganache_tx_info_when_connected(self, app):
        with app.app_context():
            db = get_db()
            w3 = get_web3()
            bc = BlockchainService(db, w3)

            if not bc.is_connected:
                pytest.skip("Ganache not running")

            anchor = bc.anchor_record(
                resource_type="healthcare_records",
                resource_id="record-789",
                data_hash="b" * 64,
            )

            assert anchor["transaction_hash"] is not None
            assert anchor["block_number"] is not None
            assert anchor["transaction_status"] == "success"


# ─────────────────────────────────────────────────────────────────────
# VERIFICATION TESTS
# ─────────────────────────────────────────────────────────────────────

class TestVerification:
    """Test integrity verification logic."""

    def test_local_match_when_chain_is_offline(self, app):
        with app.app_context():
            db = get_db()
            bc = BlockchainService(db, get_web3())

            record = {"_id": "r1", "title": "ciphertext_abc", "status": "active", "version": 1}
            data_hash = bc.compute_record_hash(record)

            # Anchor the hash
            bc.anchor_record("healthcare_records", "r1", data_hash)

            # Verify — should match
            result = bc.verify_record("healthcare_records", "r1", record)
            assert result["status"] == "LOCAL_MATCH"
            assert result["current_hash"] == result["stored_hash"]

    @pytest.mark.parametrize(("receipt_status", "use_record_payload", "expected"), [
        (1, True, "VERIFIED"),
        (0, True, "LOCAL_MATCH"),
        (1, False, "INTEGRITY_VIOLATION"),
    ])
    def test_checks_mined_payload(self, app, receipt_status, use_record_payload, expected):
        with app.app_context():
            db = get_db()
            record = {"_id": "r1", "title": "encrypted"}
            digest = BlockchainService.compute_record_hash(record)
            db.blockchain_anchors.insert_one({
                "resource_id": "r1", "resource_type": "healthcare_records",
                "data_hash": digest, "transaction_hash": "0x" + "12" * 32,
                "created_at": "2026-01-01", "network": "ganache",
            })
            node = MagicMock()
            node.eth.chain_id = app.config["GANACHE_CHAIN_ID"]
            node.eth.get_transaction_receipt.return_value = {"status": receipt_status, "blockNumber": 7}
            payload_id = "r1" if use_record_payload else "other-record"
            node.eth.get_transaction.return_value = {"input": f"{payload_id}|{digest}".encode()}
            result = BlockchainService(db, node).verify_record("healthcare_records", "r1", record)
            assert result["status"] == expected
            assert ("blockchain_hash" in result) == (expected == "VERIFIED")

    def test_violation_when_hash_differs(self, app):
        with app.app_context():
            db = get_db()
            bc = BlockchainService(db, get_web3())

            original = {"_id": "r1", "title": "original", "version": 1}
            data_hash = bc.compute_record_hash(original)
            bc.anchor_record("healthcare_records", "r1", data_hash)

            # Tamper with record
            tampered = {"_id": "r1", "title": "tampered", "version": 1}
            result = bc.verify_record("healthcare_records", "r1", tampered)
            assert result["status"] == "INTEGRITY_VIOLATION"
            assert result["current_hash"] != result["stored_hash"]

    def test_no_anchor_when_never_anchored(self, app):
        with app.app_context():
            db = get_db()
            bc = BlockchainService(db, get_web3())

            record = {"_id": "r-new", "title": "unanchored"}
            result = bc.verify_record("healthcare_records", "r-new", record)
            assert result["status"] == "NO_ANCHOR"


# ─────────────────────────────────────────────────────────────────────
# INTEGRATION WITH HEALTHCARE RECORDS
# ─────────────────────────────────────────────────────────────────────

class TestRecordIntegration:
    """Test that record creation/update triggers blockchain anchoring."""

    def test_record_creation_creates_anchor(self, client, app):
        token = register_and_login(client)

        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Blockchain Test Record",
            "description": "This record should be anchored on the blockchain.",
        }, headers=auth(token))

        assert resp.status_code == 201
        record = resp.get_json()["record"]

        # Check that blockchain anchor was created
        with app.app_context():
            db = get_db()
            anchor = db["blockchain_anchors"].find_one({"resource_id": record["_id"]})
            assert anchor is not None
            assert anchor["resource_type"] == "healthcare_records"
            assert anchor["data_hash"] is not None
            assert len(anchor["data_hash"]) == 64

    def test_record_has_verification_hash(self, client, app):
        token = register_and_login(client)

        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "diagnosis",
            "title": "Verification Hash Test",
            "description": "Record should have a verification_hash after creation.",
        }, headers=auth(token))

        record = resp.get_json()["record"]
        assert record["verification_hash"] is not None
        assert len(record["verification_hash"]) == 64

    def test_record_update_creates_new_anchor(self, client, app):
        token = register_and_login(client)

        # Create
        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Original Title",
            "description": "Original description for update test record.",
        }, headers=auth(token))
        record_id = resp.get_json()["record"]["_id"]

        # Update
        client.put(f"/api/v1/patients/me/records/{record_id}", json={
            "title": "Updated Title",
        }, headers=auth(token))

        # Should have 2 anchors now (create + update)
        with app.app_context():
            db = get_db()
            anchors = list(db["blockchain_anchors"].find({"resource_id": record_id}))
            assert len(anchors) == 2


# ─────────────────────────────────────────────────────────────────────
# API ENDPOINT TESTS
# ─────────────────────────────────────────────────────────────────────

class TestVerificationAPI:
    """Test the integrity verification API endpoint."""

    def test_verify_endpoint_reports_local_evidence_when_offline(self, client, app):
        token = register_and_login(client)

        # Create a record (auto-anchored)
        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Verify API Test",
            "description": "Testing the verification API endpoint works.",
        }, headers=auth(token))
        record_id = resp.get_json()["record"]["_id"]

        # Verify via API
        resp = client.get(f"/api/v1/integrity/record/{record_id}", headers=auth(token))
        assert resp.status_code == 200
        verification = resp.get_json()["verification"]
        assert verification["status"] == "LOCAL_MATCH"
        assert verification["current_hash"] == verification["stored_hash"]

    def test_verify_nonexistent_record_404(self, client):
        token = register_and_login(client)
        resp = client.get("/api/v1/integrity/record/nonexistent-id", headers=auth(token))
        assert resp.status_code == 404

    def test_blockchain_status_endpoint(self, client):
        token = register_and_login(client)
        resp = client.get("/api/v1/integrity/status", headers=auth(token))
        assert resp.status_code == 200
        data = resp.get_json()["blockchain"]
        assert "connected" in data
        assert "total_anchors" in data

    def test_get_record_anchors(self, client):
        token = register_and_login(client)

        resp = client.post("/api/v1/patients/me/records", json={
            "record_type": "consultation",
            "title": "Anchors Test",
            "description": "Testing anchor retrieval for a specific record.",
        }, headers=auth(token))
        record_id = resp.get_json()["record"]["_id"]

        resp = client.get(f"/api/v1/integrity/anchors/{record_id}", headers=auth(token))
        assert resp.status_code == 200
        assert resp.get_json()["count"] >= 1
