"""Add sample doctors to the local development directory without replacing accounts.

Run from backend with: python -m seeds.seed_provider_directory
"""

from secrets import token_urlsafe
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.config import get_config
from app.db_init import ensure_recipient_index
from app.extensions import get_db
from app.services.auth_service import AuthService


DOCTORS = [
    ("citycare", "asha", "Dr. Asha Rao (demo)"),
    ("citycare", "neel", "Dr. Neel Shah (demo)"),
    ("riverside", "mira", "Dr. Mira Sen (demo)"),
]


def seed():
    config = get_config("development")
    if urlsplit(config.MONGO_URI).hostname not in ("localhost", "127.0.0.1", "::1"):
        raise RuntimeError("The sample directory requires a local development database.")
    app = create_app("development")
    with app.app_context():
        db = get_db()
        ensure_recipient_index(db)
        auth = AuthService(db, config)
        added = 0
        for hospital, alias, name in DOCTORS:
            email = f"{alias}.{hospital}@directory.example.invalid"
            if db.users.find_one({"email_hash": auth._hash_email(email)}, {"_id": 1}):
                continue
            auth.register(email, token_urlsafe(32), "doctor", name,
                          allow_privileged_roles=True, hospital_id=hospital)
            added += 1
        print(f"Added {added} sample doctors.")


if __name__ == "__main__":
    seed()
