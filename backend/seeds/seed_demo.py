"""
Demo Data Seeder.

Populates the development database with realistic healthcare data
for demonstration purposes. Run after starting MongoDB:

    python seeds/seed_demo.py

Creates:
- 3 patients (with profiles)
- 1 admin user
- 10 healthcare records (consultations, diagnoses)
- 12 consents (mix of active, withdrawn)
- 30+ audit events
- Blockchain anchors for records
- 1 correction (chameleon hash)
- 1 erasure (chameleon hash)
- Consent receipts
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import get_db
from app.services.auth_service import AuthService
from app.services.patient_service import PatientService
from app.services.healthcare_record_service import HealthcareRecordService
from app.services.consent_service import ConsentService
from app.services.audit_service import AuditService
from app.services.blockchain_service import BlockchainService
from app.services.encryption_service import get_encryption_service
from app.extensions import get_web3
from app.config import get_config


def seed():
    app = create_app("development")

    with app.app_context():
        db = get_db()
        config = get_config("development")

        print("=" * 60)
        print("  DPDP Healthcare — Demo Data Seeder")
        print("=" * 60)
        print()

        # Clear existing data
        print("Clearing existing demo data...")
        for col in ["users", "patients", "healthcare_records", "consents",
                    "consent_receipts", "audit_logs", "data_access_logs",
                    "blockchain_anchors", "version_history", "chameleon_hash_records"]:
            if col in db.list_collection_names():
                db[col].delete_many({})
        print("  ✓ Database cleared\n")

        auth = AuthService(db, config)
        patient_svc = PatientService(db)
        record_svc = HealthcareRecordService(db)
        consent_svc = ConsentService(db)
        audit_svc = AuditService(db)

        # ─── USERS ────────────────────────────────────────────────
        print("Creating users...")

        # Admin
        admin = auth.register("admin@dpdp-health.in", "Admin@Secure123", "admin", "Dr. Kaushalya (DPO)")
        print(f"  ✓ Admin: admin@dpdp-health.in / Admin@Secure123")

        # Doctor (Healthcare Provider) — logs into the Provider Portal to create records
        doctor = auth.register("dr.rahul@citycare.in", "Doctor@123", "doctor", "Dr. Rahul Sharma")
        print(f"  ✓ Doctor: dr.rahul@citycare.in / Doctor@123")

        # Registration Staff (hospital front desk) — restricted portal: register patients only
        reg_staff = auth.register("reception@citycare.in", "Staff@123", "registration_staff", "Reception Desk")
        print(f"  ✓ Registration Staff: reception@citycare.in / Staff@123")

        # Patient 1
        p1 = auth.register("rajesh.kumar@gmail.com", "Patient@123", "patient", "Rajesh Kumar")
        print(f"  ✓ Patient: rajesh.kumar@gmail.com / Patient@123")

        # Patient 2
        p2 = auth.register("priya.sharma@gmail.com", "Patient@456", "patient", "Priya Sharma")
        print(f"  ✓ Patient: priya.sharma@gmail.com / Patient@456")

        # Patient 3
        p3 = auth.register("amit.patel@gmail.com", "Patient@789", "patient", "Amit Patel")
        print(f"  ✓ Patient: amit.patel@gmail.com / Patient@789")

        print()

        # ─── PATIENT PROFILES ─────────────────────────────────────
        print("Updating patient profiles...")

        pat1 = patient_svc.get_patient_by_user_id(p1["id"])
        patient_svc.update_patient_profile(pat1["_id"], p1["id"], {
            "phone_number": "+91-9876543210",
            "blood_group": "O+",
            "allergies": ["Penicillin", "Sulfa drugs"],
            "chronic_conditions": ["Hypertension"],
            "address": "42 MG Road, Chennai, Tamil Nadu 600001",
        })

        pat2 = patient_svc.get_patient_by_user_id(p2["id"])
        patient_svc.update_patient_profile(pat2["_id"], p2["id"], {
            "phone_number": "+91-9123456789",
            "blood_group": "A+",
            "allergies": ["Aspirin"],
            "chronic_conditions": ["Diabetes Type 2"],
            "address": "15 Brigade Road, Bangalore, Karnataka 560001",
        })

        pat3 = patient_svc.get_patient_by_user_id(p3["id"])
        patient_svc.update_patient_profile(pat3["_id"], p3["id"], {
            "phone_number": "+91-9988776655",
            "blood_group": "B+",
            "allergies": [],
            "chronic_conditions": [],
            "address": "7 Connaught Place, New Delhi 110001",
        })
        print("  ✓ Profiles updated with Indian healthcare data\n")

        # ─── ADDITIONAL DEMO PATIENTS (bulk) ──────────────────────
        # 10 extra patients so dashboards/metrics look realistic. Registered the
        # same way as above (register -> profile update). Idempotent: skips any
        # that already exist so re-running the seed won't error.
        print("Creating 10 additional demo patients...")
        extra_patients = [
            ("sneha.iyer@gmail.com",     "Patient@1001", "Sneha Iyer",      "+91-9801100011", "O+",  ["Latex"],        ["Asthma"],            "12 Anna Salai, Chennai, Tamil Nadu 600002"),
            ("vikram.singh@gmail.com",   "Patient@1002", "Vikram Singh",    "+91-9801100012", "B-",  [],               ["Hypertension"],      "88 Sector 17, Chandigarh 160017"),
            ("ananya.das@gmail.com",     "Patient@1003", "Ananya Das",      "+91-9801100013", "A-",  ["Peanuts"],      [],                    "5 Park Street, Kolkata, West Bengal 700016"),
            ("rohan.mehta@gmail.com",    "Patient@1004", "Rohan Mehta",     "+91-9801100014", "AB+", [],               ["Diabetes Type 2"],   "23 CG Road, Ahmedabad, Gujarat 380009"),
            ("fatima.khan@gmail.com",    "Patient@1005", "Fatima Khan",     "+91-9801100015", "O-",  ["Sulfa drugs"],  ["Thyroid"],           "9 Charminar Road, Hyderabad, Telangana 500002"),
            ("arjun.nair@gmail.com",     "Patient@1006", "Arjun Nair",      "+91-9801100016", "B+",  [],               [],                    "31 Marine Drive, Kochi, Kerala 682031"),
            ("meera.pillai@gmail.com",   "Patient@1007", "Meera Pillai",    "+91-9801100017", "A+",  ["Penicillin"],   ["Migraine"],          "14 FC Road, Pune, Maharashtra 411004"),
            ("kabir.verma@gmail.com",    "Patient@1008", "Kabir Verma",     "+91-9801100018", "O+",  [],               [],                    "60 Hazratganj, Lucknow, Uttar Pradesh 226001"),
            ("isha.gupta@gmail.com",     "Patient@1009", "Isha Gupta",      "+91-9801100019", "AB-", ["Aspirin"],      ["Anemia"],            "27 Civil Lines, Jaipur, Rajasthan 302006"),
            ("dev.reddy@gmail.com",      "Patient@1010", "Dev Reddy",       "+91-9801100020", "B+",  [],               ["Hypertension"],      "40 Banjara Hills, Hyderabad, Telangana 500034"),
        ]
        extra_created = 0
        extra_profiles = []  # (patient_id, user_id, name, chronic[]) for record seeding
        for email, pwd, name, phone, blood, allergies, chronic, address in extra_patients:
            try:
                u = auth.register(email, pwd, "patient", name)
            except Exception:
                # register() raises if the email is already registered — idempotent skip.
                print(f"  • Skipped (exists): {email}")
                continue
            prof = patient_svc.get_patient_by_user_id(u["id"])
            patient_svc.update_patient_profile(prof["_id"], u["id"], {
                "phone_number": phone,
                "blood_group": blood,
                "allergies": allergies,
                "chronic_conditions": chronic,
                "address": address,
            })
            extra_profiles.append((prof["_id"], u["id"], name, chronic))
            extra_created += 1
            print(f"  ✓ Patient: {email} / {pwd}")
        print(f"  ✓ {extra_created} additional patients created\n")

        # ─── PROVIDER-AUTHORED RECORDS for the extra patients ─────
        # Created by the seeded DOCTOR (Healthcare Provider), so provenance shows
        # "CityCare Hospital · Dr. Rahul Sharma". Reuses create_record (encryption
        # + blockchain anchor + audit-on-create).
        if extra_created:
            print("Creating provider-authored records for additional patients...")
            provider_id = doctor["id"]
            extra_record_count = 0
            for pid, uid, name, chronic in extra_profiles:
                cond = chronic[0] if chronic else "General Health"
                record_svc.create_record(
                    patient_id=pid,
                    created_by=provider_id,
                    record_type="consultation",
                    title=f"Consultation — {cond}",
                    description=f"{name} seen at CityCare Hospital. Routine evaluation for {cond.lower()}; vitals stable, no acute distress.",
                    diagnosis_codes=["Z00.0"],
                    symptoms=["none"],
                    treatment_notes="Advised routine follow-up and healthy lifestyle.",
                )
                extra_record_count += 1
            print(f"  ✓ {extra_record_count} provider-authored records created\n")

        # ─── HEALTHCARE RECORDS ───────────────────────────────────
        print("Creating healthcare records...")

        records_data = [
            (pat1["_id"], p1["id"], "consultation", "Cardiology Consultation",
             "Patient presents with chest pain and shortness of breath. ECG shows mild ST changes.",
             ["I25.1", "R07.9"], ["chest_pain", "dyspnea"], "Prescribed Aspirin 75mg and Atorvastatin 20mg."),
            (pat1["_id"], p1["id"], "diagnosis", "Hypertension Stage 1",
             "BP readings consistently above 140/90 over 3 visits. No target organ damage.",
             ["I10"], ["headache", "dizziness"], "Started Amlodipine 5mg daily. Lifestyle modifications advised."),
            (pat1["_id"], p1["id"], "follow_up", "Cardiology Follow-up",
             "Patient reports improved symptoms. BP now 130/85. Continuing current medications.",
             ["I25.1"], ["none"], "Continue current regimen. Next follow-up in 3 months."),
            (pat2["_id"], p2["id"], "consultation", "Endocrinology Consultation",
             "Patient referred for uncontrolled diabetes. HbA1c 8.2%. Fundoscopy normal.",
             ["E11.9"], ["polyuria", "fatigue"], "Added Metformin 500mg BD. Dietary counseling provided."),
            (pat2["_id"], p2["id"], "diagnosis", "Type 2 Diabetes Mellitus",
             "Confirmed T2DM based on fasting glucose 180mg/dL and HbA1c 8.2%.",
             ["E11.9", "R73.0"], ["polyuria", "polydipsia"], "Metformin + lifestyle modification. Target HbA1c <7%."),
            (pat2["_id"], p2["id"], "treatment_plan", "Diabetes Management Plan",
             "Comprehensive diabetes care plan including medication, diet, exercise, and monitoring.",
             ["E11.9"], [], "Quarterly HbA1c, annual eye exam, foot exam."),
            (pat3["_id"], p3["id"], "consultation", "General Health Checkup",
             "Annual preventive health screening. All parameters within normal limits.",
             ["Z00.0"], ["none"], "No intervention required. Continue healthy lifestyle."),
            (pat3["_id"], p3["id"], "consultation", "Orthopedic Consultation",
             "Patient complains of lower back pain for 2 weeks after lifting heavy object.",
             ["M54.5"], ["back_pain", "stiffness"], "Prescribed Diclofenac gel, physiotherapy x 10 sessions."),
            (pat1["_id"], p1["id"], "consultation", "Annual Health Checkup 2025",
             "Comprehensive annual checkup including blood work, ECG, and chest X-ray.",
             ["Z00.0"], ["none"], "All reports normal except mildly elevated cholesterol."),
            (pat3["_id"], p3["id"], "follow_up", "Back Pain Follow-up",
             "Improvement after 7 physiotherapy sessions. Pain reduced from 7/10 to 2/10.",
             ["M54.5"], ["mild_discomfort"], "Complete remaining sessions. No further medication needed."),
        ]

        created_records = []
        for patient_id, user_id, rtype, title, desc, codes, symptoms, notes in records_data:
            rec = record_svc.create_record(
                patient_id=patient_id,
                created_by=user_id,
                record_type=rtype,
                title=title,
                description=desc,
                diagnosis_codes=codes,
                symptoms=symptoms,
                treatment_notes=notes,
            )
            created_records.append(rec)

        print(f"  ✓ {len(created_records)} healthcare records created (with blockchain anchors)\n")

        # ─── CONSENTS ─────────────────────────────────────────────
        print("Creating consents...")

        consent_data = [
            (p1["id"], pat1["_id"], "healthcare_treatment", "Apollo Hospitals Chennai", 365),
            (p1["id"], pat1["_id"], "pharmacy_access", "MedPlus Pharmacy", 180),
            (p1["id"], pat1["_id"], "insurance_access", "Star Health Insurance", 365),
            (p1["id"], pat1["_id"], "research_access", "ICMR Research Division", 730),
            (p2["id"], pat2["_id"], "healthcare_treatment", "Manipal Hospital Bangalore", 365),
            (p2["id"], pat2["_id"], "pharmacy_access", "Apollo Pharmacy", 180),
            (p2["id"], pat2["_id"], "analytics_access", "National Health Authority", 365),
            (p3["id"], pat3["_id"], "healthcare_treatment", "AIIMS New Delhi", 365),
            (p3["id"], pat3["_id"], "pharmacy_access", "Netmeds Pharmacy", 90),
            (p3["id"], pat3["_id"], "marketing_access", "Practo Health", 180),
        ]

        created_consents = []
        for user_id, patient_id, ctype, entity, days in consent_data:
            result = consent_svc.grant_consent(
                user_id=user_id,
                patient_id=patient_id,
                consent_type=ctype,
                processing_entity_name=entity,
                expiry_days=days,
            )
            created_consents.append(result["consent"])

            # Audit the grant
            audit_svc.log_event(
                actor_id=user_id, actor_role="patient",
                action_type="consent_grant", resource_type="consents",
                resource_id=result["consent"]["_id"], patient_id=user_id,
                reason=f"Consent granted: {ctype} to {entity}",
            )

        # Withdraw 2 consents
        withdrawn1 = consent_svc.withdraw_consent(created_consents[3]["_id"], p1["id"], "No longer participating in research")
        withdrawn2 = consent_svc.withdraw_consent(created_consents[9]["_id"], p3["id"], "Too many marketing communications")

        audit_svc.log_event(
            actor_id=p1["id"], actor_role="patient",
            action_type="consent_withdraw", resource_type="consents",
            resource_id=created_consents[3]["_id"], patient_id=p1["id"],
            reason="Consent withdrawn: research_access", severity="warning",
        )
        audit_svc.log_event(
            actor_id=p3["id"], actor_role="patient",
            action_type="consent_withdraw", resource_type="consents",
            resource_id=created_consents[9]["_id"], patient_id=p3["id"],
            reason="Consent withdrawn: marketing_access", severity="warning",
        )

        print(f"  ✓ {len(created_consents)} consents created (2 withdrawn)\n")

        # ─── AUDIT EVENTS ─────────────────────────────────────────
        print("Creating additional audit events...")

        # Login events
        for user in [p1, p2, p3, admin]:
            audit_svc.log_event(
                actor_id=user["id"], actor_role=user["role"],
                action_type="login", resource_type="auth",
                resource_id=user["id"], patient_id=user["id"] if user["role"] == "patient" else None,
                reason="User login",
            )

        # Data access events
        audit_svc.log_data_access(
            patient_id=p1["id"], accessor_id="doc-001", accessor_role="doctor",
            accessor_name="Dr. Suresh Menon (Cardiologist)",
            access_type="view", data_categories=["medical_history", "allergies"],
            purpose="Cardiology consultation review",
        )
        audit_svc.log_data_access(
            patient_id=p2["id"], accessor_id="doc-002", accessor_role="doctor",
            accessor_name="Dr. Kavitha Reddy (Endocrinologist)",
            access_type="view", data_categories=["medical_history", "prescriptions"],
            purpose="Diabetes management review",
        )
        audit_svc.log_data_access(
            patient_id=p1["id"], accessor_id="pharm-001", accessor_role="pharmacy_staff",
            accessor_name="MedPlus Pharmacy - T. Nagar Branch",
            access_type="view", data_categories=["prescriptions", "allergies"],
            purpose="Prescription dispensing verification",
        )

        print(f"  ✓ 30+ audit events created\n")

        # ─── CORRECTION (Chameleon Hash) ──────────────────────────
        print("Creating correction request (Chameleon Hash demo)...")

        if len(created_records) > 0:
            # Simulate a correction on the first record
            from app.services.chameleon_hash_service import ChameleonHashSimulator, RedactionType
            ch = ChameleonHashSimulator()
            enc = get_encryption_service()

            target_record = db["healthcare_records"].find_one({"patient_id": pat1["_id"]})
            if target_record:
                req = ch.create_redaction_request(
                    resource_type="healthcare_records",
                    resource_id=target_record["_id"],
                    patient_id=pat1["_id"],
                    redaction_type=RedactionType.CORRECTION,
                    reason="Diagnosis code correction: I25.1 should be I25.10",
                    requested_by=p1["id"],
                    affected_fields=["diagnosis_codes"],
                )
                ch.authorize_redaction(req, p1["id"], "patient", "DPDP Act Section 12 - Right to Correction")
                req["status"] = "authorized"

                encrypted_correction = {"diagnosis_codes": enc.encrypt_field(["I25.10", "R07.9"])}
                result = ch.execute_correction(req, target_record, encrypted_correction)

                db["healthcare_records"].replace_one({"_id": target_record["_id"]}, result["modified_record"])
                db["version_history"].insert_one(result["version_archive"])
                db["chameleon_hash_records"].insert_one(req)

                audit_svc.log_event(
                    actor_id=p1["id"], actor_role="patient",
                    action_type="update", resource_type="healthcare_records",
                    resource_id=target_record["_id"], patient_id=p1["id"],
                    reason="Record corrected: Diagnosis code correction",
                    details={"chameleon_proof": result["redaction_proof_hash"]},
                )
                print("  ✓ Correction request created with chameleon hash proof\n")

        # ─── ERASURE (Chameleon Hash) ─────────────────────────────
        print("Creating erasure request (Chameleon Hash demo)...")

        # Find a record from patient 3 to erase
        erase_target = db["healthcare_records"].find_one({"patient_id": pat3["_id"], "redacted": False})
        if erase_target:
            req2 = ch.create_redaction_request(
                resource_type="healthcare_records",
                resource_id=erase_target["_id"],
                patient_id=pat3["_id"],
                redaction_type=RedactionType.ERASURE,
                reason="Exercising right to erasure under DPDP Act",
                requested_by=p3["id"],
                affected_fields=["title", "description", "diagnosis_codes", "symptoms", "treatment_notes"],
            )
            ch.authorize_redaction(req2, p3["id"], "patient", "DPDP Act Section 12 - Right to Erasure")
            req2["status"] = "authorized"

            result2 = ch.execute_erasure(req2, erase_target, ["title", "description", "diagnosis_codes", "symptoms", "treatment_notes"])

            db["healthcare_records"].replace_one({"_id": erase_target["_id"]}, result2["modified_record"])
            db["version_history"].insert_one(result2["version_archive"])
            db["chameleon_hash_records"].insert_one(req2)

            audit_svc.log_event(
                actor_id=p3["id"], actor_role="patient",
                action_type="delete", resource_type="healthcare_records",
                resource_id=erase_target["_id"], patient_id=p3["id"],
                reason="Record erased: Right to erasure exercised",
                details={"chameleon_proof": result2["redaction_proof_hash"]},
                severity="warning",
            )
            print("  ✓ Erasure request created with chameleon hash proof\n")

        # ─── SUMMARY ──────────────────────────────────────────────
        print("=" * 60)
        print("  SEEDING COMPLETE")
        print("=" * 60)
        print(f"""
  Database: {db.name}
  Users:              {db['users'].count_documents({})}
  Patients:           {db['patients'].count_documents({})}
  Healthcare Records: {db['healthcare_records'].count_documents({})}
  Consents:           {db['consents'].count_documents({})}
  Consent Receipts:   {db['consent_receipts'].count_documents({})}
  Audit Logs:         {db['audit_logs'].count_documents({})}
  Blockchain Anchors: {db['blockchain_anchors'].count_documents({})}
  Version History:    {db['version_history'].count_documents({})}
  Chameleon Records:  {db['chameleon_hash_records'].count_documents({})}

  Login Credentials:
  ┌────────────────────────────────┬───────────────────┬─────────┐
  │ Email                          │ Password          │ Role    │
  ├────────────────────────────────┼───────────────────┼─────────┤
  │ admin@dpdp-health.in           │ Admin@Secure123   │ admin   │
  │ dr.rahul@citycare.in           │ Doctor@123        │ doctor  │
  │ reception@citycare.in          │ Staff@123         │ reg.staff│
  │ rajesh.kumar@gmail.com         │ Patient@123       │ patient │
  │ priya.sharma@gmail.com         │ Patient@456       │ patient │
  │ amit.patel@gmail.com           │ Patient@789       │ patient │
  └────────────────────────────────┴───────────────────┴─────────┘
""")


if __name__ == "__main__":
    seed()
