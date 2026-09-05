"""
Physical Presence Service.

Manages short-lived "physical presence tokens" issued when a user taps
their RFID card. Sensitive operations (record erasure, chameleon redaction,
privileged admin actions) can require a valid, unexpired presence token —
proving the user is PHYSICALLY present, not just holding a stolen password.

This is the hardware step-up authentication layer:
    Password (something you know)  +  RFID card (something you have / physical presence)
"""

from datetime import datetime, timezone, timedelta
from app.utils.helpers import generate_uuid, utc_now


# How long a physical tap remains valid for gating operations
PRESENCE_VALIDITY_SECONDS = 120  # 2 minutes


class PhysicalPresenceService:
    """Issues and verifies physical presence tokens from RFID taps."""

    def __init__(self, db):
        self.db = db
        self.presence = db["physical_presence"]

    def record_presence(self, user_id: str, card_id: str) -> dict:
        """
        Record a physical presence event (called after a successful RFID tap).

        Creates/refreshes a presence token valid for PRESENCE_VALIDITY_SECONDS.
        """
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=PRESENCE_VALIDITY_SECONDS)).isoformat()

        doc = {
            "_id": generate_uuid(),
            "user_id": user_id,
            "card_id": card_id,
            "verified_at": now.isoformat(),
            "expires_at": expires_at,
        }
        # Remove any older presence for this user, keep only the latest
        self.presence.delete_many({"user_id": user_id})
        self.presence.insert_one(doc)
        return doc

    def is_physically_present(self, user_id: str) -> dict:
        """
        Check whether the user has a valid, unexpired physical presence token.

        Returns a dict: { present: bool, verified_at, expires_at, seconds_left }
        """
        now = datetime.now(timezone.utc)
        doc = self.presence.find_one({"user_id": user_id})

        if not doc:
            return {"present": False, "reason": "No physical verification on record"}

        try:
            expires = datetime.fromisoformat(doc["expires_at"])
        except (ValueError, TypeError, KeyError):
            return {"present": False, "reason": "Invalid presence record"}

        if now > expires:
            return {"present": False, "reason": "Physical verification expired"}

        seconds_left = int((expires - now).total_seconds())
        return {
            "present": True,
            "verified_at": doc.get("verified_at"),
            "expires_at": doc.get("expires_at"),
            "seconds_left": seconds_left,
            "card_id": doc.get("card_id"),
        }

    def clear_presence(self, user_id: str) -> None:
        """Consume/clear a presence token after a sensitive operation (optional)."""
        self.presence.delete_many({"user_id": user_id})


# ─────────────────────────────────────────────────────────────────────
# DECORATOR — gate any route behind physical RFID presence
# ─────────────────────────────────────────────────────────────────────

def physical_presence_required(func):
    """
    Decorator that blocks a route unless the current user has a valid,
    unexpired physical presence token (i.e., they recently tapped their
    RFID card).

    Must be used AFTER @jwt_required so that g.current_user_id is set.

    Returns 403 with requires_physical_verification=True if not present.
    """
    from functools import wraps
    from flask import g, jsonify
    from app.extensions import get_db

    @wraps(func)
    def wrapper(*args, **kwargs):
        service = PhysicalPresenceService(get_db())
        status = service.is_physically_present(g.current_user_id)
        if not status.get("present"):
            return jsonify({
                "error": True,
                "message": "Physical verification required. Tap your RFID card to authorize this action.",
                "requires_physical_verification": True,
                "reason": status.get("reason", "No physical verification on record"),
            }), 403
        return func(*args, **kwargs)

    return wrapper
