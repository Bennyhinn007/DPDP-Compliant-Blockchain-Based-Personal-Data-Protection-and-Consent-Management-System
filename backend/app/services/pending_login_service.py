"""
Pending Login Service.

Holds a short-lived, single-use, attempt-limited "pending login" between the
password step and the fingerprint second factor of an admin login.

The token handed to the client is opaque (secrets.token_urlsafe); only its
SHA-256 hash is stored, so a database leak does not yield usable tokens.

Rate limiting: each pending login allows at most `max_attempts` wrong
fingerprint submissions, after which it is deleted and the user must start over
with the password. (There is no global limiter in this project; the password
step is protected by the existing account lockout, and a pending token can only
be minted after a correct password.)
"""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from app.utils.errors import AuthenticationError

PENDING_LOGIN_TTL_SECONDS = 120
PENDING_LOGIN_MAX_ATTEMPTS = 3


def _hash(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


class PendingLoginService:
    """Creates and validates pending fingerprint-login tokens."""

    def __init__(self, db):
        self.db = db
        self.pending = db["mfa_pending_logins"]

    def create(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        # Opportunistic cleanup of expired rows.
        self.pending.delete_many({"expires_at": {"$lt": now.isoformat()}})
        token = secrets.token_urlsafe(32)
        self.pending.insert_one({
            "_id": _hash(token),
            "user_id": user_id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=PENDING_LOGIN_TTL_SECONDS)).isoformat(),
            "attempts": 0,
            "max_attempts": PENDING_LOGIN_MAX_ATTEMPTS,
        })
        return token

    def get_valid(self, token: str) -> dict:
        """Return the pending doc or raise AuthenticationError (unknown/expired)."""
        err = AuthenticationError("Login session expired or invalid. Please sign in again.")
        if not token or not isinstance(token, str):
            raise err
        doc = self.pending.find_one({"_id": _hash(token)})
        if not doc:
            raise err
        try:
            expires = datetime.fromisoformat(doc["expires_at"])
        except (ValueError, TypeError, KeyError):
            raise err
        if datetime.now(timezone.utc) > expires:
            self.pending.delete_one({"_id": doc["_id"]})
            raise err
        return doc

    def register_failure(self, token: str) -> int:
        """Count a failed attempt; delete the row when exhausted. Returns attempts left."""
        key = _hash(token)
        doc = self.pending.find_one({"_id": key})
        if not doc:
            return 0
        attempts = int(doc.get("attempts", 0)) + 1
        remaining = max(int(doc.get("max_attempts", PENDING_LOGIN_MAX_ATTEMPTS)) - attempts, 0)
        if remaining <= 0:
            self.pending.delete_one({"_id": key})
        else:
            self.pending.update_one({"_id": key}, {"$set": {"attempts": attempts}})
        return remaining

    def consume(self, token: str) -> None:
        """Single use: delete after a successful login."""
        self.pending.delete_one({"_id": _hash(token)})
