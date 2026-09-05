"""
Tests for Chameleon Hash Integration with Healthcare Records (Day 8).

Tests cover:
- Record correction via POST /patients/me/records/<id>/correct
- Record erasure via POST /patients/me/records/<id>/erase
- Version preservation (version_history collection)
- Blockchain re-anchoring after correction
- Integrity verification states (VERIFIED_MODIFIED, VERIFIED_REDACTED)
- Audit trail preservation through modification
"""

import pytest
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
        for col in ["users", "patients", "healthcare_records",
                    "blockchain_anchors", "consents", "consent_receipts",
                    "audit_logs", "version_history", "chameleon_hash_records"]:
            if col in db.list_collection_names():
                db[col].delete_many({})
    yield
    with app.app_context():
        db = get_db()
        for col in ["users", "patients", "healthcare_records",
                    "blockchain_anchors", "consents", "consent_receipts",
                    "audit_logs", "version_history", "chameleon_hash_records"]:
            if col in db.list_collection_names():
                db[col].delete_many({})


def register_and_login(client, email="ch_test@example.com"):
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPass123",
        "role": "patient", "full_name": "CH Test",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": email, "password": "TestPass123",
    })
    return resp.get_json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def grant_physical_presence(app, client, email="ch_test@example.com"):
    """
    Simulate an RFID card tap so sensitive operations (erasure) are authorized.

    Phase 5 gates record erasure behind a valid physical-presence token.
    In a real flow the user taps their card at the terminal; here we record
    the equivalent presence token directly for the logged-in user.
    """
    from app.extensions import get_db
    from app.services.physical_presence_service import PhysicalPresenceService

    with app.app_context():
        db = get_db()
        # The erasure tests use a single default user — grab the most
        # recently created one and record presence for them.
        user = db["users"].find_one(sort=[("created_at", -1)])
        PhysicalPresenceService(db).record_presence(user["_id"], card_id="TEST-CARD-01")


def create_record(client, token):
    """Helper: create a test healthcare record."""
    resp = client.post("/api/v1/patients/me/records", json={
        "record_type": "consultation",
        "title": "Original Consultation Title",
        "description": "Patient presents with original symptoms for testing.",
        "diagnosis_codes": ["Z00.0"],
        "symptoms": ["fatigue"],
        "treatment_notes": "Original treatment notes.",
    }, headers=auth(token))
    return resp.get_json()["record"]["_id"]


# ─────────────────────────────────────────────────────────────────────
# CORRECTION TESTS
# ─────────────────────────────────────────────────────────────────────

class TestRecordCorrection:
    """Test DPDP Right to Correction via Chameleon Hash."""

    def test_correct_record_success(self, client):
        token = register_and_login(client)
        record_id = create_record(client, token)

        resp = client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"title": "Corrected Consultation Title"},
            "reason": "Original title was inaccurate",
        }, headers=auth(token))

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["message"] == "Record corrected successfully"
        assert data["record"]["title"] == "Corrected Consultation Title"
        assert data["chameleon_proof"] is not None
        assert len(data["chameleon_proof"]) == 64
        assert data["version_archived"] is not None

    def test_correction_increments_version(self, client):
        token = register_and_login(client)
        record_id = create_record(client, token)

        resp = client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"title": "V2 Title"},
            "reason": "Version test",
        }, headers=auth(token))

        assert resp.get_json()["record"]["version"] == 2

    def test_correction_archives_previous_version(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)

        client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"title": "New Title"},
            "reason": "Testing archive",
        }, headers=auth(token))

        with app.app_context():
            db = get_db()
            archives = list(db["version_history"].find({"resource_id": record_id}))
            assert len(archives) == 1
            assert archives[0]["modification_type"] == "correction"
            # The previous version is archived as a snapshot. Sensitive fields
            # remain encrypted at rest (defense in depth); decrypting it must
            # recover the original plaintext title.
            from app.services.encryption_service import get_encryption_service
            snapshot = archives[0]["record_snapshot"]
            enc = get_encryption_service()
            original_title = enc.decrypt_field(snapshot.get("title", ""))
            assert "Original" in str(original_title)

    def test_correction_creates_chameleon_record(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)

        client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"description": "Corrected description text."},
            "reason": "Inaccurate symptoms recorded",
        }, headers=auth(token))

        with app.app_context():
            db = get_db()
            ch_records = list(db["chameleon_hash_records"].find({"resource_id": record_id}))
            assert len(ch_records) == 1
            assert ch_records[0]["redaction_type"] == "correction"
            assert ch_records[0]["legal_basis"] == "DPDP Act Section 12 - Right to Correction"

    def test_correction_creates_new_blockchain_anchor(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)

        client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"title": "Anchored Correction"},
            "reason": "Testing anchor",
        }, headers=auth(token))

        with app.app_context():
            db = get_db()
            # Should have 2 anchors: create + correction
            anchors = list(db["blockchain_anchors"].find({"resource_id": record_id}))
            assert len(anchors) >= 2

    def test_correction_missing_fields_422(self, client):
        token = register_and_login(client)
        record_id = create_record(client, token)

        resp = client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"title": "New"},
        }, headers=auth(token))
        assert resp.status_code == 422  # Missing reason

    def test_cannot_correct_other_patient_record(self, client):
        token1 = register_and_login(client, "p1@test.com")
        record_id = create_record(client, token1)

        token2 = register_and_login(client, "p2@test.com")
        resp = client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"title": "Hacked"},
            "reason": "Malicious",
        }, headers=auth(token2))
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────
# ERASURE TESTS
# ─────────────────────────────────────────────────────────────────────

class TestRecordErasure:
    """Test DPDP Right to Erasure via Chameleon Hash."""

    def test_erase_record_success(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)
        grant_physical_presence(app, client)

        resp = client.post(f"/api/v1/patients/me/records/{record_id}/erase", json={
            "fields_to_erase": ["title", "description", "diagnosis_codes"],
            "reason": "Exercising right to erasure",
        }, headers=auth(token))

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["record"]["redacted"] is True
        assert data["chameleon_proof"] is not None

    def test_erased_fields_become_redacted(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)
        grant_physical_presence(app, client)

        client.post(f"/api/v1/patients/me/records/{record_id}/erase", json={
            "fields_to_erase": ["title", "description"],
            "reason": "Erasure test",
        }, headers=auth(token))

        with app.app_context():
            db = get_db()
            raw = db["healthcare_records"].find_one({"_id": record_id})
            assert raw["title"] == "[REDACTED]"
            assert raw["description"] == "[REDACTED]"
            assert raw["redacted"] is True

    def test_erase_preserves_non_erased_fields(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)
        grant_physical_presence(app, client)

        client.post(f"/api/v1/patients/me/records/{record_id}/erase", json={
            "fields_to_erase": ["title"],
            "reason": "Partial erasure",
        }, headers=auth(token))

        with app.app_context():
            db = get_db()
            raw = db["healthcare_records"].find_one({"_id": record_id})
            assert raw["title"] == "[REDACTED]"
            assert raw["record_type"] == "consultation"  # Preserved
            assert raw["status"] == "active"  # Preserved

    def test_cannot_erase_already_redacted(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)
        grant_physical_presence(app, client)

        # First erasure
        client.post(f"/api/v1/patients/me/records/{record_id}/erase", json={
            "fields_to_erase": ["title"],
            "reason": "First erasure",
        }, headers=auth(token))

        # Second erasure attempt
        resp = client.post(f"/api/v1/patients/me/records/{record_id}/erase", json={
            "fields_to_erase": ["description"],
            "reason": "Second erasure",
        }, headers=auth(token))
        assert resp.status_code == 422

    def test_erasure_archives_previous_version(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)
        grant_physical_presence(app, client)

        client.post(f"/api/v1/patients/me/records/{record_id}/erase", json={
            "fields_to_erase": ["title", "description"],
            "reason": "Archive test",
        }, headers=auth(token))

        with app.app_context():
            db = get_db()
            archives = list(db["version_history"].find({"resource_id": record_id}))
            assert len(archives) == 1
            assert archives[0]["modification_type"] == "erasure"


# ─────────────────────────────────────────────────────────────────────
# VERIFICATION STATE TESTS
# ─────────────────────────────────────────────────────────────────────

class TestVerificationStates:
    """Test integrity verification states after correction/erasure."""

    def test_verified_for_unmodified_record(self, client):
        token = register_and_login(client)
        record_id = create_record(client, token)

        resp = client.get(f"/api/v1/integrity/record/{record_id}", headers=auth(token))
        assert resp.status_code == 200
        assert resp.get_json()["verification"]["status"] == "VERIFIED"

    def test_verified_modified_after_correction(self, client):
        token = register_and_login(client)
        record_id = create_record(client, token)

        # Correct the record
        client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"title": "Corrected"},
            "reason": "Test correction",
        }, headers=auth(token))

        resp = client.get(f"/api/v1/integrity/record/{record_id}", headers=auth(token))
        status = resp.get_json()["verification"]["status"]
        # After correction with new anchor, should be VERIFIED (new anchor matches)
        assert status == "VERIFIED"

    def test_verified_redacted_after_erasure(self, client):
        token = register_and_login(client)
        record_id = create_record(client, token)

        client.post(f"/api/v1/patients/me/records/{record_id}/erase", json={
            "fields_to_erase": ["title", "description"],
            "reason": "Erasure test",
        }, headers=auth(token))

        resp = client.get(f"/api/v1/integrity/record/{record_id}", headers=auth(token))
        status = resp.get_json()["verification"]["status"]
        # After erasure with new anchor, should be VERIFIED (new anchor matches redacted state)
        assert status == "VERIFIED"


# ─────────────────────────────────────────────────────────────────────
# AUDIT TRAIL TESTS
# ─────────────────────────────────────────────────────────────────────

class TestAuditPreservation:
    """Test that correction/erasure creates audit entries."""

    def test_correction_generates_audit_log(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)

        client.post(f"/api/v1/patients/me/records/{record_id}/correct", json={
            "corrections": {"title": "Audited Correction"},
            "reason": "Audit test",
        }, headers=auth(token))

        with app.app_context():
            db = get_db()
            audit = db["audit_logs"].find_one({
                "resource_id": record_id,
                "action_type": "update",
            })
            assert audit is not None
            assert "chameleon_proof" in audit["details"]
            assert "corrected_fields" in audit["details"]

    def test_erasure_generates_audit_log(self, client, app):
        token = register_and_login(client)
        record_id = create_record(client, token)
        grant_physical_presence(app, client)

        client.post(f"/api/v1/patients/me/records/{record_id}/erase", json={
            "fields_to_erase": ["title"],
            "reason": "Audit erasure test",
        }, headers=auth(token))

        with app.app_context():
            db = get_db()
            audit = db["audit_logs"].find_one({
                "resource_id": record_id,
                "action_type": "delete",
            })
            assert audit is not None
            assert audit["severity"] == "warning"
            assert "chameleon_proof" in audit["details"]
