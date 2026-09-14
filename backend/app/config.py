"""
Application Configuration.

Environment-specific settings for development, testing, and production.
"""

import os
from datetime import timedelta


class BaseConfig:
    """Base configuration shared across all environments."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    JSON_SORT_KEYS = False

    # MongoDB
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "dpdp_healthcare_db")

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-dev-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_ALGORITHM = "HS256"  # RS256 in production with key pair

    # Google OAuth 2.0 (Sign in with Google)
    # Secrets come from the environment / .env — never hard-code them.
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Blockchain (Ganache)
    GANACHE_URL = os.environ.get("GANACHE_URL", "http://localhost:8545")
    GANACHE_CHAIN_ID = int(os.environ.get("GANACHE_CHAIN_ID", "1337"))

    # Blockchain network selector: "ganache" (local) or "sepolia" (public testnet).
    # Sepolia anchoring makes record hashes verifiable on a public block explorer.
    BLOCKCHAIN_NETWORK = os.environ.get("BLOCKCHAIN_NETWORK", "ganache").lower()
    # Public Sepolia RPC (e.g. an Infura/Alchemy URL). Only used when network=sepolia.
    SEPOLIA_RPC_URL = os.environ.get("SEPOLIA_RPC_URL", "")
    # Private key of the funded Sepolia sender account (hex, 0x-prefixed).
    # NEVER commit this — keep it only in .env. Testnet ETH has no real value,
    # but a leaked key is still bad hygiene.
    SEPOLIA_PRIVATE_KEY = os.environ.get("SEPOLIA_PRIVATE_KEY", "")
    SEPOLIA_CHAIN_ID = int(os.environ.get("SEPOLIA_CHAIN_ID", "11155111"))
    # Block-explorer base used to build human-clickable links for anchored txs.
    BLOCKCHAIN_EXPLORER_URL = os.environ.get(
        "BLOCKCHAIN_EXPLORER_URL",
        "https://sepolia.etherscan.io/tx/",
    )

    # ── SIH 26125 Identity & Asset Extension (ADDITIVE) ──────────────────
    # Master feature flag for the DID / smart-contract / NFT layer. When False,
    # the SIH endpoints and UI are inert and the platform is the pure DPDP
    # healthcare product. Healthcare functionality NEVER depends on this flag.
    SIH_FEATURES_ENABLED = os.environ.get("SIH_FEATURES_ENABLED", "true").lower() == "true"
    # Prototype DID method name (labeled prototype, not a production DID network).
    SIH_DID_METHOD = os.environ.get("SIH_DID_METHOD", "rakshaid")
    # DID auth challenge lifetime (seconds). Application-level expiry (no Mongo TTL).
    SIH_DID_CHALLENGE_TTL_SECONDS = int(os.environ.get("SIH_DID_CHALLENGE_TTL_SECONDS", "120"))
    # Optional: require an RFID physical-presence tap for high-risk SIH operations
    # (NFT mint, DID revoke). OFF by default so it never blocks normal usage or
    # healthcare workflows. When on, reuses the existing physical-presence layer.
    SIH_RFID_GATE_ENABLED = os.environ.get("SIH_RFID_GATE_ENABLED", "false").lower() == "true"
    # Deployed contract addresses (populated in Week 2-3; empty until then).
    SIH_IDENTITY_REGISTRY_ADDRESS = os.environ.get("SIH_IDENTITY_REGISTRY_ADDRESS", "")
    SIH_ACCESS_CONTROL_ADDRESS = os.environ.get("SIH_ACCESS_CONTROL_ADDRESS", "")
    SIH_ASSET_NFT_ADDRESS = os.environ.get("SIH_ASSET_NFT_ADDRESS", "")

    # Encryption
    ENCRYPTION_KEY_STORE_PATH = os.environ.get("KEY_STORE_PATH", "./keystore")
    AES_KEY_ROTATION_DAYS = 90

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Rate Limiting
    RATE_LIMIT_PATIENT = 100  # requests per minute
    RATE_LIMIT_DOCTOR = 200
    RATE_LIMIT_PHARMACY = 200
    RATE_LIMIT_ADMIN = 300
    RATE_LIMIT_DPO = 300

    # Session
    SESSION_IDLE_TIMEOUT_PATIENT = timedelta(minutes=30)
    SESSION_IDLE_TIMEOUT_CLINICAL = timedelta(minutes=15)
    MAX_CONCURRENT_SESSIONS_PATIENT = 3
    MAX_CONCURRENT_SESSIONS_DOCTOR = 2
    MAX_CONCURRENT_SESSIONS_ADMIN = 1

    # Security
    BCRYPT_COST_FACTOR = 12
    MAX_LOGIN_ATTEMPTS = 3
    LOCKOUT_DURATION_PATIENT = timedelta(minutes=30)
    LOCKOUT_DURATION_DOCTOR = timedelta(minutes=30)
    LOCKOUT_DURATION_ADMIN = timedelta(hours=2)
    ACCOUNT_LOCKOUT_DURATION = timedelta(minutes=30)  # Default fallback

    # Blockchain Anchoring
    BLOCKCHAIN_ANCHOR_TIMEOUT = 10  # seconds


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False
    MONGO_DB_NAME = "dpdp_healthcare_dev"
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "ALqZ-f2S9tSruxC8YlTTInzGCYgFkTFztlerw8nxsyk=")


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    DEBUG = False
    TESTING = True
    MONGO_DB_NAME = "dpdp_healthcare_test"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    BCRYPT_COST_FACTOR = 4  # Faster hashing for tests
    ENCRYPTION_KEY = "ALqZ-f2S9tSruxC8YlTTInzGCYgFkTFztlerw8nxsyk="  # Stable test key


class ProductionConfig(BaseConfig):
    """Production environment configuration.

    All secrets MUST come from the environment. The JWT scheme stays HS256
    (symmetric) to match the implementation, which signs/verifies with
    JWT_SECRET_KEY — do NOT switch to RS256 without adding an RSA key pair.
    """

    DEBUG = False
    TESTING = False
    JWT_ALGORITHM = "HS256"
    BCRYPT_COST_FACTOR = 12

    # Encryption key MUST be provided in production (no dev fallback).
    # If unset, encryption/decryption of stored PII would silently fail,
    # so we surface it loudly at startup instead.
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")

    # Production Mongo DB name (Atlas). Falls back to base default if unset.
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "dpdp_healthcare")


_config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str = "development"):
    """Get configuration class by environment name."""
    return _config_map.get(config_name, DevelopmentConfig)
