"""Flow audit tests: consent audit timeline, chart gate edge cases, record anchors."""

from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.extensions import get_db
from app.services import consent_service
from app.services.encryption_service import get_encryption_service
from tests.accounts import create_test_account

PATIENT_EMAIL = "flow.patient@example.invalid"
PASSWORD = "ExamplePass123"
HOSPITAL = {"kind": "hospital", "hospital_id": "citycare"}


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    names = ["users", "patients", "consents", "consent_receipts", "audit_logs",
             "healthcare_records", "blockchain_anchors", "data_access_logs"]

    def wipe():
        with app.app_context():
            for name in names:
                get_db()[name].delete_many({})

    wipe()
    yield
    wipe()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def patient_login(client, email=PATIENT_EMAIL):
    create_test_account(client, role="patient", full_name="Flow Patient", email=email, password=PASSWORD)
    token = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json["access_token"]
    return auth(token)


def doctor_login(client, name="Asha", hospital="citycare"):
    credentials = {"email": f"{name.lower()}@example.invalid", "password": PASSWORD}
    account = create_test_account(client, role="doctor", full_name=name, **credentials)
    update = {"$set": {"hospital_id": hospital}} if hospital else {"$unset": {"hospital_id": ""}}
    get_db().users.update_one({"_id": account["id"]}, update)
    token = client.post("/api/v1/auth/login", json=credentials).json["access_token"]
    return account["id"], auth(token)


def save_allergies(client, patient, allergies):
    return client.put("/api/v1/patients/me", headers=patient, json={"allergies": allergies}).json["patient"]


def share(client, patient, recipient, allergies, expiry_days=365):
    return client.post("/api/v1/consents/grant", headers=patient, json={
        "recipient": recipient, "consent_type": "healthcare_treatment",
        "custom_scope": ["allergies"], "selected_allergies": allergies, "expiry_days": expiry_days,
    })


def timeline(client, patient):
    return client.get("/api/v1/audit/timeline?limit=100", headers=patient).json["timeline"]


def test_consent_events_reach_patient_timeline(client):
    patient = patient_login(client)
    save_allergies(client, patient, ["Latex", "Nickel"])
    granted = share(client, patient, HOSPITAL, ["Latex"])
    consent_id = granted.json["consent"]["_id"]
    assert client.put(f"/api/v1/consents/{consent_id}/modify", headers=patient, json={
        "new_scope": ["allergies"], "selected_allergies": ["Nickel"], "reason": "Change selection.",
    }).status_code == 200
    assert client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=patient).status_code == 200

    events = timeline(client, patient)
    by_type = {e["action_type"]: e for e in events}
    assert {"consent_grant", "consent_modify", "consent_withdraw"} <= set(by_type)
    details = by_type["consent_grant"]["details"]
    assert details["recipient"] == "hospital:citycare"
    assert details["allergy_count"] == 1
    assert "Latex" not in str(events)


def test_doctor_created_record_appears_on_timeline(client):
    patient = patient_login(client)
    profile = client.get("/api/v1/patients/me", headers=patient).json["patient"]
    _, doctor = doctor_login(client)
    response = client.post(f"/api/v1/patients/{profile['_id']}/records", headers=doctor, json={
        "record_type": "consultation", "title": "Synthetic visit", "description": "Routine test consultation.",
    })
    assert response.status_code == 201
    created = [e for e in timeline(client, patient) if e["action_type"] == "create" and e["resource_type"] == "healthcare_records"]
    assert len(created) == 1
    assert created[0]["actor_role"] == "doctor"
    assert created[0]["resource_id"] == response.json["record"]["_id"]


def test_search_flag_follows_chart_scope(client):
    patient = patient_login(client)
    save_allergies(client, patient, ["Latex"])
    consent = share(client, patient, HOSPITAL, ["Latex"]).json["consent"]
    _, doctor = doctor_login(client)

    def flag():
        found = client.get("/api/v1/doctors/patients/search?q=Flow", headers=doctor).json["patients"]
        return found[0]["has_treatment_consent"]

    assert flag() is True
    get_db().consents.update_one({"_id": consent["_id"]}, {"$set": {"data_categories_in_scope": ["prescriptions"]}})
    assert flag() is False


def test_search_finds_patient_beyond_first_fifty(client):
    enc = get_encryption_service()
    patients = get_db().patients
    for i in range(50):
        patients.insert_one(enc.encrypt_document({
            "_id": f"filler-{i}", "user_id": f"filler-user-{i}", "full_name": f"Filler {i}", "redacted": False,
        }))
    patients.insert_one(enc.encrypt_document({
        "_id": "late-patient", "user_id": "late-user", "full_name": "Zed Latecomer", "redacted": False,
    }))
    _, doctor = doctor_login(client)
    found = client.get("/api/v1/doctors/patients/search?q=Latecomer", headers=doctor).json["patients"]
    assert [p["_id"] for p in found] == ["late-patient"]


def test_unknown_patient_is_404_and_audited(client):
    _, doctor = doctor_login(client)
    response = client.get("/api/v1/doctors/patients/missing-patient/records", headers=doctor)
    assert response.status_code == 404
    event = get_db().audit_logs.find_one({"details.patient_id": "missing-patient"})
    assert event["severity"] == "warning"
    assert event["action_type"] == "read"
    assert event["patient_id"] is None
    assert event["details"]["doctor_name"] == "Asha"


def test_expired_direct_grant_falls_back_to_hospital_grant(client, monkeypatch):
    patient = patient_login(client)
    profile = save_allergies(client, patient, ["Latex", "Nickel"])
    doctor_id, doctor = doctor_login(client)
    chart = f"/api/v1/doctors/patients/{profile['_id']}/records"
    direct = {"kind": "doctor", "hospital_id": "citycare", "doctor_id": doctor_id}
    assert share(client, patient, direct, ["Latex"], expiry_days=1).status_code == 201
    assert client.get(chart, headers=doctor).json["patient"]["allergies"] == ["Latex"]

    later = datetime.now(timezone.utc) + timedelta(days=2)
    monkeypatch.setattr(consent_service, "utc_now_datetime", lambda: later)
    denied = client.get(chart, headers=doctor)
    assert denied.status_code == 403
    assert denied.json["reason"] == "CONSENT_EXPIRED"
    denial = get_db().audit_logs.find_one({"severity": "warning", "details.consent_status": "expired"})
    assert denial["details"]["doctor_name"] == "Asha"

    monkeypatch.undo()
    assert share(client, patient, HOSPITAL, ["Nickel"]).status_code == 201
    monkeypatch.setattr(consent_service, "utc_now_datetime", lambda: later)
    assert client.get(chart, headers=doctor).json["patient"]["allergies"] == ["Nickel"]


def test_doctor_without_hospital_gets_direct_grants_only(client):
    patient = patient_login(client)
    profile = save_allergies(client, patient, ["Latex"])
    doctor_id, doctor = doctor_login(client, hospital=None)
    chart = f"/api/v1/doctors/patients/{profile['_id']}/records"
    assert share(client, patient, HOSPITAL, ["Latex"]).status_code == 201
    assert client.get(chart, headers=doctor).status_code == 403
    direct = {"kind": "doctor", "hospital_id": "unaffiliated", "doctor_id": doctor_id}
    assert share(client, patient, direct, ["Latex"]).status_code == 201
    assert client.get(chart, headers=doctor).status_code == 200


def test_withdrawn_grant_denial_is_audited_with_doctor_name(client):
    patient = patient_login(client)
    profile = save_allergies(client, patient, ["Latex"])
    _, doctor = doctor_login(client)
    chart = f"/api/v1/doctors/patients/{profile['_id']}/records"
    consent = share(client, patient, HOSPITAL, ["Latex"]).json["consent"]
    assert client.get(chart, headers=doctor).status_code == 200
    client.post(f"/api/v1/consents/{consent['_id']}/withdraw", headers=patient)
    denied = client.get(chart, headers=doctor)
    assert denied.status_code == 403
    assert denied.json["reason"] == "CONSENT_NOT_GRANTED"
    reads = [e for e in timeline(client, patient) if e["action_type"] == "read"]
    assert len(reads) == 2
    granted, refused = sorted(reads, key=lambda e: e["severity"] != "warning")[::-1]
    assert granted["details"]["doctor_name"] == "Asha"
    assert refused["details"]["consent_status"] == "withdrawn"
    assert refused["details"]["doctor_name"] == "Asha"


def test_receipts_carry_recipient_and_selected_allergies(client):
    patient = patient_login(client)
    save_allergies(client, patient, ["Latex", "Nickel"])
    consent_id = share(client, patient, HOSPITAL, ["Latex"]).json["consent"]["_id"]
    client.put(f"/api/v1/consents/{consent_id}/modify", headers=patient, json={
        "new_scope": ["allergies"], "selected_allergies": ["Nickel"], "reason": "Change selection.",
    })
    client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=patient)
    receipts = client.get("/api/v1/consents/receipts", headers=patient).json["receipts"]
    assert sorted(r["action_type"] for r in receipts) == ["grant", "modify", "withdraw"]
    for receipt in receipts:
        assert receipt["processing_entity_id"] == "hospital:citycare"
        assert isinstance(receipt["selected_allergies"], list)
    chosen = {r["action_type"]: r["selected_allergies"] for r in receipts}
    assert chosen["grant"] == ["Latex"]
    assert chosen["modify"] == ["Nickel"]


def test_record_anchors_are_limited_to_the_owner(client):
    owner = patient_login(client)
    other = patient_login(client, "other.patient@example.invalid")
    record = client.post("/api/v1/patients/me/records", headers=owner, json={
        "record_type": "consultation", "title": "Synthetic chart", "description": "Routine test consultation.",
    }).json["record"]
    url = f"/api/v1/integrity/anchors/{record['_id']}"
    assert client.get(url, headers=other).status_code == 403
    assert client.get(url, headers=owner).status_code == 200
