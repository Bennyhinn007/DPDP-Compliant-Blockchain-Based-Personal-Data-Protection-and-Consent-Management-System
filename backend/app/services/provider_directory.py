"""Directory of provisioned clinicians and the MVP's demo hospitals."""

from app.utils.errors import ValidationError


HOSPITALS = {"citycare": "CityCare Hospital", "riverside": "Riverside Medical Centre"}
INDEPENDENT = "unaffiliated"


def _group(doctor):
    hospital = doctor.get("hospital_id")
    return hospital if hospital in HOSPITALS else INDEPENDENT


def provider_directory(db):
    groups = {key: {"id": key, "name": name, "hospital_grant": True, "doctors": []}
              for key, name in HOSPITALS.items()}
    doctors = db.users.find({"role": "doctor", "status": "active"}, {"full_name": 1, "hospital_id": 1})
    for doctor in doctors:
        group = _group(doctor)
        if group not in groups:
            groups[group] = {"id": group, "name": "Doctors without a listed hospital",
                             "hospital_grant": False, "doctors": []}
        groups[group]["doctors"].append({"id": doctor["_id"], "name": doctor["full_name"]})
    for entry in groups.values():
        entry["doctors"].sort(key=lambda d: (d["name"].casefold(), d["id"]))
    return sorted(groups.values(), key=lambda g: (not g["hospital_grant"], g["name"].casefold()))


def resolve_recipient(db, recipient):
    if not isinstance(recipient, dict):
        raise ValidationError("Select a doctor or hospital from the directory.")
    hospital = recipient.get("hospital_id")
    doctor_id = recipient.get("doctor_id")
    if not isinstance(hospital, str):
        raise ValidationError("Select a hospital or the unaffiliated doctor list.")
    if recipient.get("kind") == "hospital" and hospital in HOSPITALS and doctor_id is None:
        return f"hospital:{hospital}", HOSPITALS[hospital]
    if recipient.get("kind") == "doctor" and isinstance(doctor_id, str):
        doctor = db.users.find_one({"_id": doctor_id, "role": "doctor", "status": "active"})
        if doctor and _group(doctor) == hospital:
            name = doctor["full_name"]
            if hospital in HOSPITALS:
                name += f" · {HOSPITALS[hospital]}"
            return f"doctor:{hospital}:{doctor_id}", name
    raise ValidationError("Select an available recipient from that hospital or doctor list.")


def doctor_recipient_keys(db, doctor_id):
    doctor = db.users.find_one({"_id": doctor_id, "role": "doctor", "status": "active"}, {"hospital_id": 1})
    if not doctor:
        return []
    group = _group(doctor)
    keys = [f"doctor:{group}:{doctor_id}"]
    if group in HOSPITALS:
        keys.append(f"hospital:{group}")
    return keys
