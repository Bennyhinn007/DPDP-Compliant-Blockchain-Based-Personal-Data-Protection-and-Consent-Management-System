"""
MongoDB Database Initialization.

Creates all collections with indexes and validation.
Run once on first deployment or via Docker entrypoint.

Usage: python -m app.db_init
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from app.config import get_config
import os


def initialize_database(db):
    """
    Create all collections and indexes for the MVP.

    Collections: users, patients, doctors, pharmacy_staff,
    healthcare_records, prescriptions, consents, consent_receipts,
    audit_logs, blockchain_anchors
    """

    print("Initializing database collections and indexes...")

    # ─── users ───────────────────────────────────────────────────
    if "users" not in db.list_collection_names():
        db.create_collection("users")
    users = db["users"]
    users.create_index([("email_hash", ASCENDING)], unique=True, name="idx_email_hash")
    users.create_index([("role", ASCENDING), ("status", ASCENDING)], name="idx_role_status")
    users.create_index([("status", ASCENDING), ("locked_until", ASCENDING)], name="idx_lockout")
    print("  ✓ users collection ready")

    # ─── patients ────────────────────────────────────────────────
    if "patients" not in db.list_collection_names():
        db.create_collection("patients")
    patients = db["patients"]
    patients.create_index([("user_id", ASCENDING)], unique=True, name="idx_user_id")
    patients.create_index([("identity_number_hash", ASCENDING)], unique=True, sparse=True, name="idx_identity_hash")
    patients.create_index([("redacted", ASCENDING)], name="idx_redacted")
    patients.create_index([("created_at", DESCENDING)], name="idx_created")
    print("  ✓ patients collection ready")

    # ─── doctors ─────────────────────────────────────────────────
    if "doctors" not in db.list_collection_names():
        db.create_collection("doctors")
    doctors = db["doctors"]
    doctors.create_index([("user_id", ASCENDING)], unique=True, name="idx_user_id")
    doctors.create_index([("license_number_hash", ASCENDING)], unique=True, name="idx_license")
    doctors.create_index([("specialization", ASCENDING)], name="idx_specialization")
    print("  ✓ doctors collection ready")

    # ─── pharmacy_staff ──────────────────────────────────────────
    if "pharmacy_staff" not in db.list_collection_names():
        db.create_collection("pharmacy_staff")
    pharmacy = db["pharmacy_staff"]
    pharmacy.create_index([("user_id", ASCENDING)], unique=True, name="idx_user_id")
    pharmacy.create_index([("license_number_hash", ASCENDING)], unique=True, name="idx_license")
    print("  ✓ pharmacy_staff collection ready")

    # ─── healthcare_records ──────────────────────────────────────
    if "healthcare_records" not in db.list_collection_names():
        db.create_collection("healthcare_records")
    records = db["healthcare_records"]
    records.create_index([("patient_id", ASCENDING), ("created_at", DESCENDING)], name="idx_patient_date")
    records.create_index([("doctor_id", ASCENDING), ("created_at", DESCENDING)], name="idx_doctor_date")
    records.create_index([("record_type", ASCENDING), ("patient_id", ASCENDING)], name="idx_type_patient")
    records.create_index([("redacted", ASCENDING)], name="idx_redacted")
    records.create_index([("verification_hash", ASCENDING)], name="idx_verification")
    print("  ✓ healthcare_records collection ready")

    # ─── prescriptions ───────────────────────────────────────────
    if "prescriptions" not in db.list_collection_names():
        db.create_collection("prescriptions")
    prescriptions = db["prescriptions"]
    prescriptions.create_index([("patient_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)], name="idx_patient_status")
    prescriptions.create_index([("doctor_id", ASCENDING), ("created_at", DESCENDING)], name="idx_doctor_date")
    prescriptions.create_index([("dispensed_by", ASCENDING), ("dispensed_at", DESCENDING)], name="idx_dispensed")
    prescriptions.create_index([("redacted", ASCENDING)], name="idx_redacted")
    print("  ✓ prescriptions collection ready")

    # ─── consents ────────────────────────────────────────────────
    if "consents" not in db.list_collection_names():
        db.create_collection("consents")
    consents = db["consents"]
    consents.create_index([("patient_id", ASCENDING), ("consent_type", ASCENDING)], name="idx_patient_type")
    consents.create_index([("user_id", ASCENDING), ("status", ASCENDING)], name="idx_user_status")
    consents.create_index([("status", ASCENDING), ("expires_at", ASCENDING)], name="idx_expiry")
    consents.create_index([("processing_entity_id", ASCENDING), ("status", ASCENDING)], name="idx_processor")
    print("  ✓ consents collection ready")

    # ─── consent_receipts ────────────────────────────────────────
    if "consent_receipts" not in db.list_collection_names():
        db.create_collection("consent_receipts")
    receipts = db["consent_receipts"]
    receipts.create_index([("consent_id", ASCENDING)], name="idx_consent")
    receipts.create_index([("patient_id", ASCENDING), ("issued_at", DESCENDING)], name="idx_patient_date")
    receipts.create_index([("blockchain_tx_ref", ASCENDING)], name="idx_blockchain")
    print("  ✓ consent_receipts collection ready")

    # ─── audit_logs ──────────────────────────────────────────────
    if "audit_logs" not in db.list_collection_names():
        db.create_collection("audit_logs")
    audit = db["audit_logs"]
    audit.create_index([("actor_id", ASCENDING), ("created_at", DESCENDING)], name="idx_actor_date")
    audit.create_index([("patient_id", ASCENDING), ("created_at", DESCENDING)], name="idx_patient_date")
    audit.create_index([("action_type", ASCENDING), ("created_at", DESCENDING)], name="idx_action_date")
    audit.create_index([("severity", ASCENDING), ("created_at", DESCENDING)], name="idx_severity")
    audit.create_index([("resource_type", ASCENDING), ("resource_id", ASCENDING)], name="idx_resource")
    audit.create_index([("log_hash", ASCENDING)], name="idx_log_hash")
    audit.create_index([("created_at", DESCENDING)], name="idx_chronological")
    print("  ✓ audit_logs collection ready")

    # ─── blockchain_anchors ──────────────────────────────────────
    if "blockchain_anchors" not in db.list_collection_names():
        db.create_collection("blockchain_anchors")
    anchors = db["blockchain_anchors"]
    anchors.create_index([("transaction_hash", ASCENDING)], unique=True, sparse=True, name="idx_tx_hash")
    anchors.create_index([("resource_type", ASCENDING), ("resource_id", ASCENDING)], name="idx_resource")
    anchors.create_index([("patient_id", ASCENDING), ("anchor_type", ASCENDING)], name="idx_patient_type")
    anchors.create_index([("anchor_type", ASCENDING), ("created_at", DESCENDING)], name="idx_type_date")
    anchors.create_index([("data_hash", ASCENDING)], name="idx_data_hash")
    print("  ✓ blockchain_anchors collection ready")

    # ─── data_access_logs ────────────────────────────────────────
    if "data_access_logs" not in db.list_collection_names():
        db.create_collection("data_access_logs")
    access_logs = db["data_access_logs"]
    access_logs.create_index([("patient_id", ASCENDING), ("created_at", DESCENDING)], name="idx_patient_date")
    access_logs.create_index([("accessor_id", ASCENDING), ("created_at", DESCENDING)], name="idx_accessor_date")
    access_logs.create_index([("accessor_role", ASCENDING)], name="idx_role")
    access_logs.create_index([("patient_id", ASCENDING), ("accessor_role", ASCENDING)], name="idx_patient_role")
    print("  ✓ data_access_logs collection ready")

    # ─────────────────────────────────────────────────────────────────
    # SIH 26125 Identity & Asset Extension collections (ADDITIVE)
    # The 11 collections above are UNCHANGED. These 6 are new and independent;
    # they support the DID / access-control / NFT layer. Application-level
    # expiry is used for did_challenges (NO MongoDB TTL index).
    # ─────────────────────────────────────────────────────────────────

    # ─── dids ────────────────────────────────────────────────────
    if "dids" not in db.list_collection_names():
        db.create_collection("dids")
    dids = db["dids"]
    dids.create_index([("user_id", ASCENDING)], unique=True, name="idx_did_user")
    dids.create_index([("status", ASCENDING)], name="idx_did_status")
    print("  ✓ dids collection ready")

    # ─── did_challenges (application-level expiry; NOT a TTL index) ─
    if "did_challenges" not in db.list_collection_names():
        db.create_collection("did_challenges")
    did_challenges = db["did_challenges"]
    did_challenges.create_index([("nonce", ASCENDING)], unique=True, name="idx_did_nonce")
    did_challenges.create_index([("did", ASCENDING)], name="idx_did_challenge_did")
    print("  ✓ did_challenges collection ready")

    # ─── assets (encrypted metadata off-chain) ─────────────────────
    if "assets" not in db.list_collection_names():
        db.create_collection("assets")
    assets = db["assets"]
    assets.create_index([("asset_type", ASCENDING)], name="idx_asset_type")
    assets.create_index([("created_at", DESCENDING)], name="idx_asset_created")
    print("  ✓ assets collection ready")

    # ─── nft_tokens (NFT ↔ DID ↔ asset mapping) ────────────────────
    if "nft_tokens" not in db.list_collection_names():
        db.create_collection("nft_tokens")
    nft_tokens = db["nft_tokens"]
    nft_tokens.create_index([("token_id", ASCENDING)], unique=True, sparse=True, name="idx_nft_token")
    nft_tokens.create_index([("owner_did", ASCENDING)], name="idx_nft_owner")
    print("  ✓ nft_tokens collection ready")

    # ─── role_assignments (on-chain SIH-role mirror cache) ─────────
    if "role_assignments" not in db.list_collection_names():
        db.create_collection("role_assignments")
    role_assignments = db["role_assignments"]
    role_assignments.create_index([("did", ASCENDING)], name="idx_roleasgn_did")
    role_assignments.create_index([("sih_role", ASCENDING)], name="idx_roleasgn_role")
    print("  ✓ role_assignments collection ready")

    # ─── chain_events (contract-event cache; explorer + dual audit) ─
    if "chain_events" not in db.list_collection_names():
        db.create_collection("chain_events")
    chain_events = db["chain_events"]
    chain_events.create_index([("tx_hash", ASCENDING)], unique=True, sparse=True, name="idx_chainevt_tx")
    chain_events.create_index([("event_name", ASCENDING), ("block_number", DESCENDING)], name="idx_chainevt_name_block")
    print("  ✓ chain_events collection ready")

    print("\n✅ Database initialization complete. 11 core + 6 SIH extension collections ready.")


if __name__ == "__main__":
    config = get_config(os.environ.get("FLASK_ENV", "development"))
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB_NAME]
    initialize_database(db)
    client.close()
