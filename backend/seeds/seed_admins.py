"""
Admin (DPO) account seeder — ADDITIVE, does not wipe any other data.

Creates the 5 DPO admin accounts and removes the old single `admin@dpdp-health.in`
account. Connects DIRECTLY to the database named by the MONGO_URI / MONGO_DB_NAME
environment variables (it does NOT load backend/.env), so you can safely point it
at either the local dev DB or the Atlas production DB.

Local dev:
    $env:MONGO_URI="mongodb://localhost:27017"; $env:MONGO_DB_NAME="dpdp_healthcare_dev"
    python seeds/seed_admins.py

Atlas (production) — copy MONGO_URI from the Render dashboard or Atlas "Connect":
    $env:MONGO_URI="mongodb+srv://USER:PASS@cluster0.xxxx.mongodb.net/?retryWrites=true&w=majority"
    $env:MONGO_DB_NAME="DPDP"          # the database name the live app uses
    python seeds/seed_admins.py

IMPORTANT: the password hash must be compatible with the live app. This script
uses bcrypt with the same cost factor as production config, so logins will work.

Idempotent: re-running updates existing accounts rather than duplicating them.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from datetime import datetime, timezone
from pymongo import MongoClient
from app.utils.helpers import generate_uuid  # UUID format used by the app

# (email, password, full_name).
ADMINS = [
    ("benny@dpdp-health.in",       "Benny@Secure123",      "Benny (DPO)"),
    ("pratiksha@dpdp-health.in",   "Pratiksha@Secure123",  "Pratiksha (DPO)"),
    ("rishi@dpdp-health.in",       "Rishi@Secure123",      "Rishi (DPO)"),
    ("rajeshwari@dpdp-health.in",  "Rajeshwari@Secure123", "Rajeshwari (DPO)"),
    ("harishjoshi@dpdp-health.in", "Harishjoshi@Secure123", "Harish Joshi (DPO)"),
]
REMOVE_EMAILS = ["admin@dpdp-health.in"]

# Must match how the app hashes emails/passwords.
BCRYPT_COST = int(os.environ.get("BCRYPT_COST_FACTOR", "12"))


def _hash_email(email: str) -> str:
    import hashlib
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_COST)).decode()


def seed_admins():
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGO_DB_NAME", "dpdp_healthcare_dev")
    client = MongoClient(uri, serverSelectionTimeoutMS=20000)
    db = client[db_name]
    users = db["users"]

    host = client.address[0] if client.address else "?"
    safe_host = "atlas" if "mongodb.net" in uri or uri.startswith("mongodb+srv") else host

    print("=" * 60)
    print("  DPDP Healthcare — Admin (DPO) Seeder")
    print(f"  DB name : {db_name}")
    print(f"  Host    : {safe_host}")
    print("=" * 60)

    # Confirm the connection works before writing anything.
    client.admin.command("ping")

    for email in REMOVE_EMAILS:
        res = users.delete_many({"email_hash": _hash_email(email)})
        if res.deleted_count:
            print(f"  - removed old admin: {email}")

    now = datetime.now(timezone.utc).isoformat()
    for email, password, full_name in ADMINS:
        eh = _hash_email(email)
        existing = users.find_one({"email_hash": eh})
        doc = {
            "email_hash": eh,
            "email_encrypted": email,
            "password_hash": _hash_password(password),
            "role": "admin",
            "full_name": full_name,
            "status": "active",
            "mfa_enabled": False,
            "failed_login_attempts": 0,
            "locked_until": None,
        }
        if existing:
            users.update_one({"_id": existing["_id"]}, {"$set": doc})
            print(f"  ~ updated admin: {email}")
        else:
            doc["_id"] = generate_uuid()
            doc["created_at"] = now
            users.insert_one(doc)
            print(f"  + created admin: {email}")

    total = users.count_documents({"role": "admin"})
    print(f"\n  Admin accounts in '{db_name}': {total}")
    print(f"  {'Email':<32} {'Password':<22} Name")
    print("  " + "-" * 70)
    for email, password, full_name in ADMINS:
        print(f"  {email:<32} {password:<22} {full_name}")
    print("\nDone. Enable MFA / fingerprint per account from the Profile page.")
    client.close()


if __name__ == "__main__":
    seed_admins()
