"""
Biometric (fingerprint) Service — PROTOTYPE second factor for admins.

How it fits together:
  * The fingerprint is captured and MATCHED in the browser by the vendor's local
    service (SecuGen SgiBioSrv, or Mantra MFS100). The backend never sees raw
    fingerprint images.
  * The backend stores the admin's enrolled TEMPLATE encrypted at rest (Fernet,
    via the existing EncryptionService) in its own collection.
  * After a successful match the client reports the score; if it meets the
    configured threshold the backend records a short-lived physical-presence
    token — the SAME token an RFID tap creates — so every existing presence gate
    accepts it.

HONEST LIMITATION: because matching happens in the browser, the backend trusts the
client's reported score. This proves "someone operating the enrolled admin's
session, at a machine with the sensor, matched a finger" — it is NOT
tamper-proof against a malicious client. Labeled as a prototype second factor.
"""

from __future__ import annotations

import base64
import binascii
from typing import Optional

from app.utils.helpers import utc_now
from app.utils.errors import ValidationError
from app.services.encryption_service import get_encryption_service
from app.services.physical_presence_service import PhysicalPresenceService

ALLOWED_PROVIDERS = ("secugen", "mantra")
MIN_TEMPLATE_BYTES = 16
MAX_TEMPLATE_BYTES = 64 * 1024


class BiometricService:
    """Stores encrypted fingerprint templates and issues presence tokens."""

    def __init__(self, db):
        self.db = db
        self.templates = db["biometric_templates"]
        self.enc = get_encryption_service()

    # ── validation ─────────────────────────────────────────────────────

    @staticmethod
    def _validate_template(template_b64: str, provider: str) -> None:
        if provider not in ALLOWED_PROVIDERS:
            raise ValidationError(f"provider must be one of: {list(ALLOWED_PROVIDERS)}")
        if not template_b64 or not isinstance(template_b64, str):
            raise ValidationError("template is required")
        try:
            raw = base64.b64decode(template_b64, validate=True)
        except (binascii.Error, ValueError):
            raise ValidationError("template must be valid base64")
        if not (MIN_TEMPLATE_BYTES <= len(raw) <= MAX_TEMPLATE_BYTES):
            raise ValidationError("template size is outside the accepted range")

    # ── enrollment ─────────────────────────────────────────────────────

    def status(self, user_id: str) -> dict:
        doc = self.templates.find_one({"_id": user_id})
        if not doc:
            return {"enrolled": False}
        return {
            "enrolled": True,
            "provider": doc.get("provider"),
            "quality": doc.get("quality"),
            "enrolled_at": doc.get("enrolled_at"),
        }

    def is_enrolled(self, user_id: str) -> bool:
        return self.templates.count_documents({"_id": user_id}) > 0

    def enroll(self, user_id: str, template_b64: str, provider: str,
               quality: Optional[int] = None) -> dict:
        """Store (or replace) the user's template, encrypted."""
        provider = (provider or "").strip().lower()
        self._validate_template(template_b64, provider)
        now = utc_now()
        existing = self.templates.find_one({"_id": user_id})
        doc = {
            "provider": provider,
            "template_enc": self.enc.encrypt_field(template_b64),
            "quality": quality,
            "updated_at": now,
        }
        if existing:
            self.templates.update_one({"_id": user_id}, {"$set": doc})
        else:
            self.templates.insert_one({"_id": user_id, "enrolled_at": now, **doc})
        return self.status(user_id)

    def get_template(self, user_id: str) -> Optional[dict]:
        """Decrypted template for the user's OWN client-side match."""
        doc = self.templates.find_one({"_id": user_id})
        if not doc:
            return None
        return {
            "template": self.enc.decrypt_field(doc["template_enc"]),
            "provider": doc.get("provider"),
        }

    def remove(self, user_id: str) -> bool:
        return self.templates.delete_one({"_id": user_id}).deleted_count > 0

    # ── verification → presence token ──────────────────────────────────

    def record_verification(self, user_id: str, score: float, provider: str,
                            min_score: int) -> dict:
        """
        If `score` meets the threshold, record a physical-presence token and return
        {verified: True, ...}. Otherwise {verified: False} and NO token is issued.
        """
        if not self.is_enrolled(user_id):
            return {"verified": False, "reason": "No fingerprint enrolled"}
        try:
            score = float(score)
        except (TypeError, ValueError):
            raise ValidationError("score must be a number")
        if score < min_score:
            return {"verified": False, "reason": "Fingerprint did not match",
                    "min_score": min_score}
        token = PhysicalPresenceService(self.db).record_presence(
            user_id, card_id=f"biometric:{provider or 'unknown'}"
        )
        return {"verified": True, "physical_presence_expires_at": token["expires_at"]}
