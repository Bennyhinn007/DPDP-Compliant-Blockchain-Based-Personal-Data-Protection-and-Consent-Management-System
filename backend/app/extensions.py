"""
Application Extensions.

Initializes MongoDB client and Web3 connection.
These are configured once and shared across the application.
"""

from flask import Flask
from pymongo import MongoClient

# Global instances (initialized in init_extensions)
mongo_client: MongoClient = None
db = None
w3 = None


def init_extensions(app: Flask) -> None:
    """
    Initialize all application extensions.

    Args:
        app: Flask application instance
    """
    global mongo_client, db, w3

    # MongoDB
    mongo_client = MongoClient(app.config["MONGO_URI"])
    db = mongo_client[app.config["MONGO_DB_NAME"]]

    # Web3 — skipped entirely under TESTING so the suite is self-contained
    # (no network). Otherwise connect to either the local Ganache node or the
    # public Sepolia testnet, per BLOCKCHAIN_NETWORK. Blockchain anchoring
    # degrades gracefully to "not connected" if the endpoint is unreachable.
    if app.config.get("TESTING"):
        w3 = None
    else:
        network = app.config.get("BLOCKCHAIN_NETWORK", "ganache")
        if network == "sepolia":
            rpc_url = app.config.get("SEPOLIA_RPC_URL", "")
        else:
            rpc_url = app.config.get("GANACHE_URL", "http://localhost:8545")
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 5})) if rpc_url else None
        except Exception:
            w3 = None

    # Set encryption key in environment if configured
    if app.config.get("ENCRYPTION_KEY"):
        import os
        os.environ["ENCRYPTION_KEY"] = app.config["ENCRYPTION_KEY"]
        # Reset singleton so it picks up the new key
        from app.services.encryption_service import EncryptionService
        import app.services.encryption_service as enc_mod
        enc_mod._instance = EncryptionService(app.config["ENCRYPTION_KEY"])

    app.extensions["mongo_client"] = mongo_client
    app.extensions["db"] = db
    app.extensions["w3"] = w3


def get_db():
    """Get the MongoDB database instance."""
    return db


def get_web3():
    """Get the Web3 instance."""
    return w3
