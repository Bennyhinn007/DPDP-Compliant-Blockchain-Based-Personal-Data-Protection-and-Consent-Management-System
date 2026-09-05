"""
Authentication Service.

Handles user registration, login, JWT token management,
password hashing (bcrypt), and account lockout logic.
"""

import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.utils.helpers import generate_uuid, utc_now, compute_sha256
from app.utils.constants import UserRole
from app.utils.errors import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
)


# Cached Google transport — reused across requests so google-auth can cache
# Google's signing certs (per their Cache-Control headers) instead of making
# a fresh HTTPS round-trip on every login. Built lazily and only once.
_GOOGLE_REQUEST = None


def _google_request():
    """Return a shared google.auth transport Request (cached certs)."""
    global _GOOGLE_REQUEST
    if _GOOGLE_REQUEST is None:
        from google.auth.transport import requests as google_requests
        _GOOGLE_REQUEST = google_requests.Request()
    return _GOOGLE_REQUEST


class AuthService:
    """Manages authentication operations."""

    def __init__(self, db, config):
        self.db = db
        self.users = db["users"]
        self.config = config

    # ─────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ─────────────────────────────────────────────────────────────────

    def register(self, email: str, password: str, role: str, full_name: str) -> dict:
        """
        Register a new user.

        Args:
            email: User email (unique)
            password: Plaintext password (min 8 chars)
            role: User role (patient or admin for MVP)
            full_name: Display name

        Returns:
            Created user document (password excluded)

        Raises:
            ValidationError: Invalid input
        """
        # Validate inputs
        self._validate_registration(email, password, role)

        # Check email uniqueness via hash
        email_hash = self._hash_email(email)
        if self.users.find_one({"email_hash": email_hash}):
            raise ValidationError("Email already registered")

        # Hash password
        password_hash = self._hash_password(password)

        # Create user document
        user_id = generate_uuid()
        now = utc_now()

        user_doc = {
            "_id": user_id,
            "email_hash": email_hash,
            "email_encrypted": email,  # In production: encrypt with AES-256
            "password_hash": password_hash,
            "role": role,
            "full_name": full_name,
            "status": "active",
            "mfa_enabled": False,
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login": None,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id,
        }

        self.users.insert_one(user_doc)

        # Auto-create patient profile if registering as patient
        if role == UserRole.PATIENT.value:
            from app.services.patient_service import PatientService
            patient_svc = PatientService(self.db)
            patient_svc.create_patient_profile(user_id, full_name)

        # Return sanitized response
        return self._sanitize_user(user_doc)

    # ─────────────────────────────────────────────────────────────────
    # LOGIN
    # ─────────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> dict:
        """
        Authenticate user and issue JWT tokens.

        Args:
            email: User email
            password: Plaintext password

        Returns:
            Dict with access_token, refresh_token, user info

        Raises:
            AuthenticationError: Invalid credentials or locked account
        """
        if not email or not password:
            raise AuthenticationError("Email and password required")

        email_hash = self._hash_email(email)
        user = self.users.find_one({"email_hash": email_hash})

        if not user:
            raise AuthenticationError("Invalid email or password")

        # Check account lockout
        if user.get("locked_until"):
            lock_time = datetime.fromisoformat(user["locked_until"])
            if datetime.now(timezone.utc) < lock_time:
                remaining = int((lock_time - datetime.now(timezone.utc)).total_seconds() / 60)
                raise AuthenticationError(
                    f"Account locked. Try again in {remaining} minutes."
                )
            else:
                # Lockout expired — reset
                self.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"locked_until": None, "failed_login_attempts": 0}}
                )

        # Verify password
        if not self._verify_password(password, user["password_hash"]):
            self._record_failed_attempt(user)
            raise AuthenticationError("Invalid email or password")

        # Successful login — reset failed attempts
        now = utc_now()
        self.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"failed_login_attempts": 0, "last_login": now, "updated_at": now}}
        )

        # Generate tokens
        access_token = self._generate_access_token(user)
        refresh_token = self._generate_refresh_token(user)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": int(self.config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
            "user": self._sanitize_user(user),
        }

    # ─────────────────────────────────────────────────────────────────
    # GOOGLE OAUTH 2.0 LOGIN
    # ─────────────────────────────────────────────────────────────────

    def login_with_google(self, id_token_str: str) -> dict:
        """
        Authenticate a user via a Google ID token (Sign in with Google).

        Verifies the ID token against Google using our GOOGLE_CLIENT_ID as the
        expected audience, then finds-or-creates a passwordless user and issues
        the SAME JWT token pair as a normal login.

        Args:
            id_token_str: The Google ID token (JWT) from the browser.

        Returns:
            Identical shape to login(): access_token, refresh_token, token_type,
            expires_in, user.

        Raises:
            AuthenticationError: Token missing, invalid, or Google not configured.
        """
        if not id_token_str:
            raise AuthenticationError("Google ID token required")

        client_id = getattr(self.config, "GOOGLE_CLIENT_ID", "")
        if not client_id:
            raise AuthenticationError("Google login is not configured on the server")

        # Verify the token with Google's public keys. A module-level cached
        # transport reuses the HTTP connection AND lets google-auth cache the
        # certs (honouring their Cache-Control), so repeat logins don't refetch
        # Google's certs every time — this is the main latency fix.
        try:
            from google.oauth2 import id_token as google_id_token

            claims = google_id_token.verify_oauth2_token(
                id_token_str,
                _google_request(),
                client_id,
            )
        except ValueError as e:
            raise AuthenticationError(f"Invalid Google token: {str(e)[:120]}")

        # Google guarantees these on a valid ID token.
        issuer = claims.get("iss", "")
        if issuer not in ("accounts.google.com", "https://accounts.google.com"):
            raise AuthenticationError("Invalid Google token issuer")

        if not claims.get("email_verified", False):
            raise AuthenticationError("Google account email is not verified")

        email = (claims.get("email") or "").strip().lower()
        if not email:
            raise AuthenticationError("Google token missing email")

        full_name = claims.get("name") or email.split("@")[0]
        google_sub = claims.get("sub")

        # Find existing user by email hash, or create a passwordless one.
        email_hash = self._hash_email(email)
        user = self.users.find_one({"email_hash": email_hash})

        if user is None:
            user = self._create_oauth_user(
                email=email,
                full_name=full_name,
                google_sub=google_sub,
            )
        else:
            # Block Google login for suspended/deleted accounts.
            if user.get("status") not in ("active", None):
                raise AuthenticationError("Account is not active")
            # Backfill provider linkage on first Google login for a password user.
            now = utc_now()
            self.users.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "last_login": now,
                    "updated_at": now,
                    "failed_login_attempts": 0,
                    "google_sub": user.get("google_sub") or google_sub,
                }},
            )

        # Issue the identical token pair used by password login.
        access_token = self._generate_access_token(user)
        refresh_token = self._generate_refresh_token(user)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": int(self.config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
            "user": self._sanitize_user(user),
        }

    def _create_oauth_user(self, email: str, full_name: str, google_sub: str = None) -> dict:
        """
        Create a passwordless user for OAuth sign-in (defaults to patient role).

        Mirrors register() but with password_hash=None and auth_provider set.
        Also creates the patient profile so the account behaves like a normal
        self-registered patient.
        """
        user_id = generate_uuid()
        now = utc_now()

        user_doc = {
            "_id": user_id,
            "email_hash": self._hash_email(email),
            "email_encrypted": email,  # In production: encrypt with AES-256
            "password_hash": None,     # Passwordless — login only via Google
            "auth_provider": "google",
            "google_sub": google_sub,
            "role": UserRole.PATIENT.value,
            "full_name": full_name,
            "status": "active",
            "mfa_enabled": False,
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login": now,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id,
        }

        self.users.insert_one(user_doc)

        # Auto-create the patient profile, matching register()'s behaviour.
        from app.services.patient_service import PatientService
        patient_svc = PatientService(self.db)
        patient_svc.create_patient_profile(user_id, full_name)

        return user_doc

    # ─────────────────────────────────────────────────────────────────
    # TOKEN OPERATIONS
    # ─────────────────────────────────────────────────────────────────

    def verify_token(self, token: str) -> dict:
        """
        Verify and decode a JWT access token.

        Returns:
            Token payload (sub, role, exp, etc.)

        Raises:
            AuthenticationError: Invalid or expired token
        """
        try:
            payload = jwt.decode(
                token,
                self.config.JWT_SECRET_KEY,
                algorithms=[self.config.JWT_ALGORITHM],
                audience="dpdp-healthcare-api",
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Fetch user by UUID."""
        user = self.users.find_one({"_id": user_id})
        if not user:
            return None
        return self._sanitize_user(user)

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _validate_registration(self, email: str, password: str, role: str) -> None:
        """Validate registration inputs."""
        errors = {}

        if not email or "@" not in email:
            errors["email"] = "Valid email required"

        if not password or len(password) < 8:
            errors["password"] = "Password must be at least 8 characters"

        allowed_roles = [UserRole.PATIENT.value, UserRole.ADMIN.value, UserRole.DOCTOR.value]
        if role not in allowed_roles:
            errors["role"] = f"Role must be one of: {allowed_roles}"

        if errors:
            raise ValidationError("Validation failed", details=errors)

    def _hash_password(self, password: str) -> str:
        """Hash password with bcrypt (cost factor 12)."""
        salt = bcrypt.gensalt(rounds=self.config.BCRYPT_COST_FACTOR)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify plaintext password against bcrypt hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def _hash_email(email: str) -> str:
        """SHA-256 hash of lowercase email for indexed lookups."""
        import hashlib
        return hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()

    def _generate_access_token(self, user: dict) -> str:
        """Generate JWT access token (1 hour)."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user["_id"],
            "role": user["role"],
            "iat": now,
            "exp": now + self.config.JWT_ACCESS_TOKEN_EXPIRES,
            "iss": "dpdp-healthcare-platform",
            "aud": "dpdp-healthcare-api",
            "type": "access",
        }
        return jwt.encode(payload, self.config.JWT_SECRET_KEY, algorithm=self.config.JWT_ALGORITHM)

    def _generate_refresh_token(self, user: dict) -> str:
        """Generate JWT refresh token (24 hours)."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user["_id"],
            "role": user["role"],
            "iat": now,
            "exp": now + self.config.JWT_REFRESH_TOKEN_EXPIRES,
            "iss": "dpdp-healthcare-platform",
            "aud": "dpdp-healthcare-api",
            "type": "refresh",
        }
        return jwt.encode(payload, self.config.JWT_SECRET_KEY, algorithm=self.config.JWT_ALGORITHM)

    def _record_failed_attempt(self, user: dict) -> None:
        """Record failed login and lock if threshold exceeded. Role-based lockout durations."""
        attempts = user.get("failed_login_attempts", 0) + 1
        now_str = utc_now()
        update = {
            "failed_login_attempts": attempts,
            "last_failed_attempt": now_str,
            "updated_at": now_str,
        }

        if attempts >= self.config.MAX_LOGIN_ATTEMPTS:
            # Role-based lockout duration
            role = user.get("role", "patient")
            if role in ("admin", "dpo"):
                duration = self.config.LOCKOUT_DURATION_ADMIN
            elif role == "doctor":
                duration = self.config.LOCKOUT_DURATION_DOCTOR
            else:
                duration = self.config.LOCKOUT_DURATION_PATIENT

            lock_until = datetime.now(timezone.utc) + duration
            update["locked_until"] = lock_until.isoformat()

            # Audit: ACCOUNT_LOCKED
            from app.services.audit_service import AuditService
            audit = AuditService(self.db)
            audit.log_event(
                actor_id=user["_id"],
                actor_role=role,
                action_type="login",
                resource_type="auth",
                resource_id=user["_id"],
                reason=f"Account locked after {attempts} failed attempts. Duration: {int(duration.total_seconds() / 60)} minutes.",
                severity="critical",
            )

        self.users.update_one({"_id": user["_id"]}, {"$set": update})

    @staticmethod
    def _sanitize_user(user: dict) -> dict:
        """Remove sensitive fields from user document."""
        return {
            "id": user["_id"],
            "email": user.get("email_encrypted", ""),
            "role": user["role"],
            "full_name": user.get("full_name", ""),
            "status": user["status"],
            "mfa_enabled": user.get("mfa_enabled", False),
            "last_login": user.get("last_login"),
            "created_at": user["created_at"],
        }
