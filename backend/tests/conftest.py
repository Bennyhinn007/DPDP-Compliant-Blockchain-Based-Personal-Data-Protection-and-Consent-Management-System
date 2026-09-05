"""
Pytest configuration — makes the entire suite self-contained.

Patches PyMongo's MongoClient with an in-memory ``mongomock`` client so
tests run with ZERO external dependencies: no MongoDB server, no Ganache,
no network. Just run ``pytest`` and everything passes.

This module is auto-discovered by pytest and applied before any test
module is imported, so every existing ``create_app("testing")`` call in
the suite transparently uses the in-memory database.
"""

import os
import mongomock
import pymongo

# Force testing config for any code that reads the env directly.
os.environ.setdefault("FLASK_ENV", "testing")

# ─────────────────────────────────────────────────────────────────────
# Patch MongoClient -> mongomock, at import time (before app creation)
# ─────────────────────────────────────────────────────────────────────
# app.extensions does `from pymongo import MongoClient` and calls
# `MongoClient(uri)`. We replace that symbol with mongomock's client so
# the whole application layer talks to an in-memory Mongo.

import app.extensions as _extensions  # noqa: E402

_extensions.MongoClient = mongomock.MongoClient
# Also patch the top-level pymongo attribute for safety (any late imports).
pymongo.MongoClient = mongomock.MongoClient


import pytest  # noqa: E402
from app import create_app  # noqa: E402
from app.extensions import get_db  # noqa: E402


# Collections cleared between tests to guarantee isolation.
_ALL_COLLECTIONS = [
    "users",
    "patients",
    "doctors",
    "pharmacy_staff",
    "healthcare_records",
    "prescriptions",
    "consents",
    "consent_receipts",
    "audit_logs",
    "blockchain_anchors",
    "data_access_logs",
    "physical_access_tokens",
    "physical_access_logs",
    "rfid_cards",
    "webauthn_credentials",
    "mfa_secrets",
]


@pytest.fixture(scope="session")
def _mongomock_app():
    """A session-scoped testing app backed by mongomock."""
    return create_app("testing")


@pytest.fixture(autouse=True)
def _reset_mongomock(_mongomock_app):
    """Wipe all collections before AND after every test for isolation."""
    def _wipe():
        with _mongomock_app.app_context():
            db = get_db()
            for name in _ALL_COLLECTIONS:
                try:
                    db[name].delete_many({})
                except Exception:
                    pass

    _wipe()
    yield
    _wipe()
