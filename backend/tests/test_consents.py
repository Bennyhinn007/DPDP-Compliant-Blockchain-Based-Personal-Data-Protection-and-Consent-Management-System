"""
Tests for Consent Management (Day 4).

Tests cover:
- Grant consent (all 6 types, validation, duplicates)
- List consents (all, by status, by type)
- Get single consent (ownership)
- Modify consent scope
- Withdraw consent (immediate revocation)
- Consent receipts
- Expiry tracking
"""

import pytest
from datetime import datetime, timedelta, timezone
from app import create_app
from app.extensions import get_db
from app.services import consent_service
from tests.accounts import create_test_account


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
        db["users"].delete_many({})
        db["patients"].delete_many({})
        db["consents"].delete_many({})
        db["consent_receipts"].delete_many({})
    yield
    with app.app_context():
        db = get_db()
        db["users"].delete_many({})
        db["patients"].delete_many({})
        db["consents"].delete_many({})
        db["consent_receipts"].delete_many({})


def register_and_login(client, email="patient@test.com", role="patient"):
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPass123",
        "role": role, "full_name": "Test Patient",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": email, "password": "TestPass123",
    })
    return resp.get_json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def grant(client, token, consent_type="healthcare_treatment", entity="Apollo Healthcare"):
    return client.post("/api/v1/consents/grant", json={
        "consent_type": consent_type,
        "processing_entity_name": entity,
        "recipient": {"kind": "hospital", "hospital_id": "citycare"},
        "expiry_days": 365,
    }, headers=auth(token))


class TestGrantConsent:
    """Test consent grant operations."""

    def test_grant_healthcare_treatment(self, client):
        token = register_and_login(client)
        resp = grant(client, token, "healthcare_treatment")
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["consent"]["consent_type"] == "healthcare_treatment"
        assert data["consent"]["status"] == "active"
        assert data["consent"]["processing_entity_name"] == "CityCare Hospital"
        assert "medical_history" in data["consent"]["data_categories_in_scope"]
        assert data["receipt"]["action_type"] == "grant"

    def test_grant_pharmacy_access(self, client):
        token = register_and_login(client)
        resp = grant(client, token, "pharmacy_access", "Central Pharmacy")
        assert resp.status_code == 201
        scope = resp.get_json()["consent"]["data_categories_in_scope"]
        assert "prescriptions" in scope
        assert "allergies" in scope
        assert "medical_history" not in scope  # Purpose limitation

    def test_grant_all_six_types(self, client):
        token = register_and_login(client)
        types = [
            "healthcare_treatment", "pharmacy_access", "research_access",
            "insurance_access", "analytics_access", "marketing_access",
        ]
        for ct in types:
            resp = grant(client, token, ct, f"Entity for {ct}")
            assert resp.status_code == 201, f"Failed for {ct}"

    def test_grant_duplicate_rejected(self, client):
        token = register_and_login(client)
        grant(client, token, "healthcare_treatment")
        resp = grant(client, token, "healthcare_treatment")
        assert resp.status_code == 422
        assert "already exists" in resp.get_json()["message"]

    def test_grant_invalid_type(self, client):
        token = register_and_login(client)
        resp = client.post("/api/v1/consents/grant", json={
            "consent_type": "invalid_type",
            "processing_entity_name": "Test",
            "expiry_days": 365,
        }, headers=auth(token))
        assert resp.status_code == 422

    def test_grant_missing_entity_name(self, client):
        token = register_and_login(client)
        resp = client.post("/api/v1/consents/grant", json={
            "consent_type": "healthcare_treatment",
            "processing_entity_name": "",
            "expiry_days": 365,
        }, headers=auth(token))
        assert resp.status_code == 422

    def test_grant_generates_receipt(self, client):
        token = register_and_login(client)
        resp = grant(client, token)
        data = resp.get_json()
        assert data["receipt"]["_id"] is not None
        assert data["receipt"]["action_type"] == "grant"
        assert data["receipt"]["consent_id"] == data["consent"]["_id"]

    def test_grant_with_custom_scope(self, client):
        token = register_and_login(client)
        resp = client.post("/api/v1/consents/grant", json={
            "consent_type": "healthcare_treatment",
            "recipient": {"kind": "hospital", "hospital_id": "citycare"},
            "expiry_days": 180,
            "custom_scope": ["allergies"],
        }, headers=auth(token))
        assert resp.status_code == 201
        assert resp.get_json()["consent"]["data_categories_in_scope"] == ["allergies"]


class TestListConsents:
    """Test consent listing."""

    def test_list_all_consents(self, client):
        token = register_and_login(client)
        grant(client, token, "healthcare_treatment")
        grant(client, token, "pharmacy_access", "Pharmacy")

        resp = client.get("/api/v1/consents/", headers=auth(token))
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 2

    def test_filter_by_status(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token, "healthcare_treatment")
        consent_id = grant_resp.get_json()["consent"]["_id"]

        # Withdraw one
        client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=auth(token))

        # Grant another
        grant(client, token, "pharmacy_access", "Pharmacy")

        # Filter active only
        resp = client.get("/api/v1/consents/?status=active", headers=auth(token))
        assert resp.get_json()["count"] == 1

        # Filter withdrawn
        resp = client.get("/api/v1/consents/?status=withdrawn", headers=auth(token))
        assert resp.get_json()["count"] == 1

    def test_filter_by_type(self, client):
        token = register_and_login(client)
        grant(client, token, "healthcare_treatment")
        grant(client, token, "pharmacy_access", "Pharmacy")

        resp = client.get("/api/v1/consents/?type=pharmacy_access", headers=auth(token))
        assert resp.get_json()["count"] == 1
        assert resp.get_json()["consents"][0]["consent_type"] == "pharmacy_access"


class TestGetConsent:
    """Test get single consent."""

    def test_get_own_consent(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        resp = client.get(f"/api/v1/consents/{consent_id}", headers=auth(token))
        assert resp.status_code == 200
        assert resp.get_json()["consent"]["_id"] == consent_id

    def test_cannot_get_other_patient_consent(self, client):
        token1 = register_and_login(client, "p1@test.com")
        grant_resp = grant(client, token1)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        token2 = register_and_login(client, "p2@test.com")
        resp = client.get(f"/api/v1/consents/{consent_id}", headers=auth(token2))
        assert resp.status_code == 403

    def test_get_nonexistent_consent(self, client):
        token = register_and_login(client)
        resp = client.get("/api/v1/consents/nonexistent-id", headers=auth(token))
        assert resp.status_code == 404


class TestModifyConsent:
    """Test consent modification."""

    def test_modify_scope(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        resp = client.put(f"/api/v1/consents/{consent_id}/modify", json={
            "new_scope": ["allergies"],
            "reason": "Restricting to allergies only",
        }, headers=auth(token))

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["consent"]["data_categories_in_scope"] == ["allergies"]
        assert data["consent"]["previous_scope"] is not None
        assert data["consent"]["version"] == 2
        assert data["receipt"]["action_type"] == "modify"

    def test_modify_without_reason_fails(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        resp = client.put(f"/api/v1/consents/{consent_id}/modify", json={
            "new_scope": ["allergies"],
            "reason": "",
        }, headers=auth(token))
        assert resp.status_code == 422

    def test_cannot_modify_withdrawn_consent(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        # Withdraw first
        client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=auth(token))

        # Try to modify
        resp = client.put(f"/api/v1/consents/{consent_id}/modify", json={
            "new_scope": ["allergies"],
            "reason": "Attempting modify after withdrawal",
        }, headers=auth(token))
        assert resp.status_code == 422


class TestWithdrawConsent:
    """Test consent withdrawal."""

    def test_withdraw_consent(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        resp = client.post(f"/api/v1/consents/{consent_id}/withdraw", json={
            "reason": "No longer need healthcare services",
        }, headers=auth(token))

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["consent"]["status"] == "withdrawn"
        assert data["consent"]["withdrawn_at"] is not None
        assert data["receipt"]["action_type"] == "withdraw"

    def test_withdraw_already_withdrawn_fails(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=auth(token))
        resp = client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=auth(token))
        assert resp.status_code == 422

    def test_can_regrant_after_withdrawal(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=auth(token))

        # Re-grant same type
        resp = grant(client, token, "healthcare_treatment")
        assert resp.status_code == 201


class TestReceipts:
    """Test consent receipts."""

    def test_list_receipts(self, client):
        token = register_and_login(client)
        grant(client, token, "healthcare_treatment")
        grant(client, token, "pharmacy_access", "Pharmacy")

        resp = client.get("/api/v1/consents/receipts", headers=auth(token))
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 2

    def test_get_single_receipt(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        receipt_id = grant_resp.get_json()["receipt"]["_id"]

        resp = client.get(f"/api/v1/consents/receipts/{receipt_id}", headers=auth(token))
        assert resp.status_code == 200
        assert resp.get_json()["receipt"]["action_type"] == "grant"

    def test_receipt_generated_on_withdraw(self, client):
        token = register_and_login(client)
        grant_resp = grant(client, token)
        consent_id = grant_resp.get_json()["consent"]["_id"]

        client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=auth(token))

        resp = client.get("/api/v1/consents/receipts", headers=auth(token))
        receipts = resp.get_json()["receipts"]
        actions = [r["action_type"] for r in receipts]
        assert "grant" in actions
        assert "withdraw" in actions


class TestActiveSharing:
    """Test active sharing view."""

    def test_active_sharing_shows_only_active(self, client):
        token = register_and_login(client)
        grant(client, token, "healthcare_treatment")
        grant_resp = grant(client, token, "pharmacy_access", "Pharmacy")
        consent_id = grant_resp.get_json()["consent"]["_id"]

        # Withdraw pharmacy
        client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=auth(token))

        resp = client.get("/api/v1/consents/active-sharing", headers=auth(token))
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 1
        assert resp.get_json()["active_sharing"][0]["consent_type"] == "healthcare_treatment"


def test_chart_access_at_exact_consent_deadline(client, monkeypatch):
    patient = register_and_login(client)
    create_test_account(client, role="doctor", full_name="Test Doctor",
                        email="doctor@example.invalid", password="ExamplePass123")
    get_db().users.update_one({"role": "doctor"}, {"$set": {"hospital_id": "citycare"}})
    doctor = client.post("/api/v1/auth/login", json={
        "email": "doctor@example.invalid", "password": "ExamplePass123",
    }).json["access_token"]
    consent = grant(client, patient).json["consent"]
    deadline = datetime.fromisoformat(consent["expires_at"])
    chart = f"/api/v1/doctors/patients/{consent['patient_id']}/records"
    record = client.post("/api/v1/patients/me/records", headers=auth(patient), json={
        "record_type": "consultation", "title": "Synthetic chart", "description": "Routine test consultation.",
    })
    assert record.status_code == 201

    monkeypatch.setattr(consent_service, "utc_now_datetime", lambda: deadline - timedelta(seconds=1))
    assert client.get(chart, headers=auth(doctor)).json["records"][0]["_id"] == record.json["record"]["_id"]
    monkeypatch.setattr(consent_service, "utc_now_datetime", lambda: deadline)
    denied = client.get(chart, headers=auth(doctor))
    assert denied.status_code == 403
    assert denied.json["reason"] == "CONSENT_EXPIRED"
    assert "records" not in denied.json
    timeline = client.get("/api/v1/audit/timeline", headers=auth(patient)).json["timeline"]
    attempts = [e for e in timeline if e["actor_role"] == "doctor" and e["action_type"] == "read"]
    assert [e["severity"] for e in attempts] == ["warning", "info"]
    assert attempts[0]["details"]["consent_status"] == "expired"
    assert all(e["details"]["consent_id"] == consent["_id"] for e in attempts)
    assert client.get("/api/v1/consents/active-sharing", headers=auth(patient)).json["count"] == 0
    assert client.get("/api/v1/consents/expiring-soon", headers=auth(patient)).json["count"] == 0
    assert client.get("/api/v1/consents/?status=expired", headers=auth(patient)).json["count"] == 1
    assert grant(client, patient).status_code == 201
    assert client.get(chart, headers=auth(doctor)).status_code == 200


@pytest.mark.parametrize("stored_deadline", [
    None, "invalid", "2026-01-01T05:30:00+05:30", datetime(2026, 1, 1),
])
def test_old_or_unreadable_deadlines_cannot_authorize(client, monkeypatch, stored_deadline):
    token = register_and_login(client)
    consent = grant(client, token).json["consent"]
    get_db().consents.update_one({"_id": consent["_id"]}, {"$set": {"expires_at": stored_deadline}})
    monkeypatch.setattr(consent_service, "utc_now_datetime", lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    # An expired grant must permit renewal even when no doctor has opened the chart.
    assert grant(client, token).status_code == 201
    assert get_db().consents.find_one({"_id": consent["_id"]})["status"] == "expired"


@pytest.mark.parametrize("scope", [[], "allergies", ["contact_info"], [{"category": "allergies"}]])
def test_grant_and_modify_reject_invalid_treatment_scopes(client, scope):
    patient = auth(register_and_login(client))
    body = {"consent_type": "healthcare_treatment", "recipient": {"kind": "hospital", "hospital_id": "citycare"},
            "custom_scope": scope}
    assert client.post("/api/v1/consents/grant", headers=patient, json=body).status_code == 422
    body["custom_scope"] = ["allergies"]
    granted = client.post("/api/v1/consents/grant", headers=patient, json=body)
    assert granted.status_code == 201
    consent_id = granted.json["consent"]["_id"]
    edit = client.put(f"/api/v1/consents/{consent_id}/modify", headers=patient, json={
        "new_scope": scope, "reason": "Change shared categories.",
    })
    assert edit.status_code == 422
    assert get_db().consents.find_one({"_id": consent_id})["data_categories_in_scope"] == ["allergies"]


@pytest.mark.parametrize("stored_scope", [[], None, "allergies", ["prescriptions"], ["unrecognized"]])
def test_chart_denied_when_no_supported_category_is_granted(client, stored_scope):
    patient = register_and_login(client)
    consent = grant(client, patient).json["consent"]
    get_db().consents.update_one({"_id": consent["_id"]}, {"$set": {"data_categories_in_scope": stored_scope}})
    create_test_account(client, email="dr@example.invalid", password="ExamplePass123", role="doctor", full_name="Doctor")
    get_db().users.update_one({"role": "doctor"}, {"$set": {"hospital_id": "citycare"}})
    doctor = client.post("/api/v1/auth/login", json={"email": "dr@example.invalid", "password": "ExamplePass123"})
    response = client.get(f"/api/v1/doctors/patients/{consent['patient_id']}/records",
                          headers=auth(doctor.json["access_token"]))
    assert response.status_code == 403
    assert response.json["reason"] == "CONSENT_SCOPE_RESTRICTED"
    assert "patient" not in response.json and "records" not in response.json
    assert get_db().data_access_logs.count_documents({"consent_id": consent["_id"]}) == 0


def test_specific_recipient_and_allergy_lifecycle(client):
    patient = auth(register_and_login(client))
    profile_url = "/api/v1/patients/me"
    profile = client.put(profile_url, headers=patient, json={"allergies": ["Latex", "Nickel"]}).json["patient"]
    chart = f"/api/v1/doctors/patients/{profile['_id']}/records"

    def doctor(name, hospital):
        credentials = {"email": f"{name}@example.invalid", "password": "ExamplePass123"}
        account = create_test_account(client, role="doctor", full_name=name, **credentials)
        get_db().users.update_one({"_id": account["id"]}, {"$set": {"hospital_id": hospital}})
        login = client.post("/api/v1/auth/login", json=credentials)
        return account["id"], auth(login.json["access_token"])

    first_id, first = doctor("Zara", "citycare")
    _, second = doctor("Asha", "citycare")
    _, outside = doctor("Mira", "riverside")
    groups = client.get("/api/v1/consents/providers", headers=patient).json["hospitals"]
    assert [d["name"] for d in groups[0]["doctors"]] == ["Asha", "Zara"]

    direct = {"kind": "doctor", "hospital_id": "citycare", "doctor_id": first_id}
    hospital = {"kind": "hospital", "hospital_id": "citycare"}

    def share(recipient, allergies):
        return client.post("/api/v1/consents/grant", headers=patient, json={
            "recipient": recipient, "consent_type": "healthcare_treatment",
            "custom_scope": ["allergies"], "selected_allergies": allergies,
        })

    assert share({**direct, "hospital_id": "riverside"}, ["Latex"]).status_code == 422
    assert share(direct, ["Unsaved entry"]).status_code == 422
    grant = share(direct, ["Latex"])
    assert grant.status_code == 201
    direct_id = grant.json["consent"]["_id"]
    assert grant.json["receipt"]["selected_allergies"] == ["Latex"]
    assert "Latex" not in str(get_db().consents.find_one({"_id": direct_id}))
    assert "Latex" not in str(get_db().consent_receipts.find_one({"consent_id": direct_id}))
    assert share(direct, ["Nickel"]).status_code == 422
    response = client.get(chart, headers=first)
    assert response.json["patient"] == {"_id": profile["_id"], "allergies": ["Latex"]}
    assert client.get(chart, headers=second).status_code == 403
    assert client.get(chart, headers=outside).status_code == 403
    search = client.get("/api/v1/doctors/patients/search?q=Test", headers=second)
    assert search.json["patients"][0]["has_treatment_consent"] is False

    broader = share(hospital, ["Nickel"])
    assert broader.status_code == 201
    assert client.get(chart, headers=second).json["patient"]["allergies"] == ["Nickel"]
    assert client.get(chart, headers=first).json["patient"]["allergies"] == ["Latex"]
    assert client.get(chart, headers=outside).status_code == 403
    client.put(profile_url, headers=patient, json={"allergies": ["Nickel", "Dust"]})
    assert client.get(chart, headers=first).json["patient"]["allergies"] == []
    edit = client.put(f"/api/v1/consents/{direct_id}/modify", headers=patient, json={
        "new_scope": ["allergies"], "selected_allergies": ["Dust"], "reason": "Update my selection.",
    })
    assert edit.json["receipt"]["selected_allergies"] == ["Dust"]
    assert client.get(chart, headers=first).json["patient"]["allergies"] == ["Dust"]
    client.post(f"/api/v1/consents/{direct_id}/withdraw", headers=patient)
    assert client.get(chart, headers=first).json["patient"]["allergies"] == ["Nickel"]
    hospital_id = broader.json["consent"]["_id"]
    # Historical grants with only a display name cannot authorize any clinician.
    get_db().consents.update_one({"_id": hospital_id}, {"$unset": {"processing_entity_id": ""}})
    assert client.get(chart, headers=first).status_code == 403
    assert client.get(chart, headers=second).status_code == 403
