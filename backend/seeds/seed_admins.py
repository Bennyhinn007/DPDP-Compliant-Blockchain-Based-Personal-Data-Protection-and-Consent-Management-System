"""
Admin (DPO) account seeder — ADDITIVE, does not wipe any other data.

Creates the 5 DPO admin accounts and removes the old single `admin@dpdp-health.in`
account. Safe to run against either the local dev database or the Atlas
production database: it only touches these specific admin accounts, nothing else.

Usage (local dev, uses backend/.env MONGO_URI):
    python seeds/seed_admins.py

Usage (target a specific database, e.g. Atlas):
    $env:MONGO_URI="mongodb+srv://...";  $env:MONGO_DB_NAME="dpdp_healthcare"
    python seeds/seed_admins.py

Idempotent: re-running updates existing accounts' password/name rather than
creating duplicates (email is unique).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import get_db
from app.services.auth_service import AuthService
from app.config import get_config

# (email, password, full_name). Passwords are intentionally simple demo values;
# this is a prototype. Enable MFA / biometrics per account afterwards.
ADMINS = [
    ("benny@dpdp-health.in",       "Benny@Secure123",      "Benny (DPO)"),
    ("pratiksha@dpdp-health.in",   "Pratiksha@Secure123",  "Pratiksha (DPO)"),
    ("rishi@dpdp-health.in",       "Rishi@Secure123",      "Rishi (DPO)"),
    ("rajeshwari@dpdp-health.in",  "Rajeshwari@Secure123", "Rajeshwari (DPO)"),
    ("harishjoshi@dpdp-health.in", "Harishjoshi@Secure123", "Harish Joshi (DPO)"),
]

# Old account to remove so there are exactly 5 admins.
REMOVE_EMAILS = ["admin@dpdp-health.in"]


def _email_hash(auth: AuthService, email: str) -> str:
    return auth._hash_email(email.lower().strip())


def seed_admins():
    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        db = get_db()
        auth = AuthService(db, get_config(os.environ.get("FLASK_ENV", "development")))
        users = db["users"]

        print("=" * 60)
        print("  DPDP Healthcare — Admin (DPO) Seeder")
        print(f"  DB: {db.name}")
        print("=" * 60)

        # 1) Remove the old single admin account(s).
        for email in REMOVE_EMAILS:
            res = users.delete_many({"email_hash": _email_hash(auth, email)})
            if res.deleted_count:
                print(f"  - removed old admin: {email}")

        # 2) Create or update the 5 DPO admins.
        for email, password, full_name in ADMINS:
            eh = _email_hash(auth, email)
            existing = users.find_one({"email_hash": eh})
            if existing:
                users.update_one({"_id": existing["_id"]}, {"$set": {
                    "password_hash": auth._hash_password(password),
                    "full_name": full_name,
                    "role": "admin",
                    "status": "active",
                }})
                print(f"  ~ updated admin: {email}")
            else:
                auth.register(email, password, "admin", full_name,
                              allow_privileged_roles=True)
                print(f"  + created admin: {email}")

        print("\nAdmin accounts now in this database:")
        print(f"  {'Email':<32} {'Password':<22} Name")
        print("  " + "-" * 70)
        for email, password, full_name in ADMINS:
            print(f"  {email:<32} {password:<22} {full_name}")
        print("\nDone. Enable MFA / fingerprint per account from the Profile page.")


if __name__ == "__main__":
    seed_admins()
