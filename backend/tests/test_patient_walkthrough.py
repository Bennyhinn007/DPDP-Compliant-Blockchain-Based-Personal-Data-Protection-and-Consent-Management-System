"""Keep the public synthetic case in step with the authenticated patient journey."""

import json
from pathlib import Path

from tests.accounts import create_test_account
from app import create_app


def test_public_consent_example_matches_api():
    sample_file = Path(__file__).resolve().parents[2] / "frontend/src/pages/consentExample.json"
    sample = json.loads(sample_file.read_text(encoding="utf-8"))
    client = create_app("testing").test_client()

    def sign_in(role, name):
        credentials = {"email": f"{role}@example.invalid", "password": "ExamplePass123"}
        create_test_account(client, **credentials, role=role, full_name=name)
        login = client.post("/api/v1/auth/login", json=credentials)
        assert login.status_code == 200
        return {"Authorization": "Bearer " + login.json["access_token"]}

    patient = sign_in("patient", sample["patient"])
    doctor = sign_in("doctor", sample["doctor"])
    patient_id = client.get("/api/v1/patients/me", headers=patient).json["patient"]["_id"]
    assert client.put("/api/v1/patients/me", headers=patient, json={
        "allergies": [sample["allergy"]], "blood_group": "AB+",
    }).status_code == 200
    record = client.post(f"/api/v1/patients/{patient_id}/records", headers=doctor, json={
        "record_type": "consultation", "title": sample["record"],
        "description": "Synthetic consultation for the public walkthrough.",
    })
    assert record.status_code == 201
    reads = []

    def read_chart():
        response = client.get(f"/api/v1/doctors/patients/{patient_id}/records", headers=doctor)
        records = response.json.get("records", [])
        profile = response.json.get("patient", {})
        if records:
            assert "allergies" not in profile
            assert profile["blood_group"] == "AB+"
            assert [r["_id"] for r in records] == [record.json["record"]["_id"]]
        reads.append({"status": response.status_code, "decision": response.json["access_status"],
                      "records": len(records), "allergies": profile.get("allergies", [])})
        return response

    read_chart()
    directory = client.get("/api/v1/consents/providers", headers=patient).json["hospitals"]
    clinician = next(d for h in directory for d in h["doctors"])
    grant = client.post("/api/v1/consents/grant", headers=patient, json={
        "consent_type": "healthcare_treatment", "recipient": {
            "kind": "doctor", "hospital_id": "unaffiliated", "doctor_id": clinician["id"]},
        "custom_scope": ["medical_history"],
    })
    assert grant.status_code == 201
    read_chart()
    consent_id = grant.json["consent"]["_id"]
    change = client.put(f"/api/v1/consents/{consent_id}/modify", headers=patient, json={
        "new_scope": ["allergies"], "selected_allergies": [sample["allergy"]], "reason": "Share my allergy list only.",
    })
    assert change.status_code == 200
    assert change.json["receipt"]["scope_after"] == ["allergies"]
    limited = read_chart()
    assert limited.json["patient"] == {"_id": patient_id, "allergies": [sample["allergy"]]}
    assert limited.json["records"] == []
    assert limited.json["consent"]["chart_scope"] == ["allergies"]
    withdrawal = client.post(f"/api/v1/consents/{consent_id}/withdraw", headers=patient,
                             json={"reason": "Treatment complete"})
    assert withdrawal.status_code == 200
    read_chart()
    assert reads == sample["access"]
    timeline = client.get("/api/v1/audit/timeline", headers=patient).json["timeline"]
    attempts = [e for e in timeline if e["actor_role"] == "doctor" and e["action_type"] == "read"]
    assert [e["severity"] for e in attempts] == ["warning", "info", "info", "warning"]
    history = client.get("/api/v1/audit/access-history", headers=patient).json["access_history"]
    assert [h["data_categories"] for h in history] == [["allergies"], ["medical_history"]]
    assert [e["details"]["data_categories"] for e in attempts if e["severity"] == "info"] == [
        ["allergies"], ["medical_history"],
    ]
    assert all(h["consent_id"] == consent_id and h["purpose"] == sample["auditPurpose"] for h in history)
