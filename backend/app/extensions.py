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
_w3_rpc_url = None  # RPC endpoint, set by init_extensions
_w3_ready = False   # True once get_web3() has tried to build the client


def init_extensions(app: Flask) -> None:
    """
    Initialize all application extensions.

    Args:
        app: Flask application instance
    """
    global mongo_client, db, w3, _w3_rpc_url, _w3_ready

    # MongoDB
    mongo_client = MongoClient(app.config["MONGO_URI"])
    db = mongo_client[app.config["MONGO_DB_NAME"]]

    # Web3 — skipped entirely under TESTING so the suite is self-contained
    # (no network). Otherwise connect to either the local Ganache node or the
    # public Sepolia testnet, per BLOCKCHAIN_NETWORK. Blockchain anchoring
    # degrades gracefully to "not connected" if the endpoint is unreachable.
    w3 = None
    _w3_rpc_url = None
    _w3_ready = False
    if not app.config.get("TESTING"):
        network = app.config.get("BLOCKCHAIN_NETWORK", "ganache")
        if network == "sepolia":
            rpc_url = app.config.get("SEPOLIA_RPC_URL", "")
        else:
            rpc_url = app.config.get("GANACHE_URL", "http://localhost:8545")
        # web3 takes ~0.85 s to import, paid by every worker on a cold start, and
        # the login path never touches the chain. So only remember the endpoint
        # here; get_web3() builds the client on first use.
        _w3_rpc_url = rpc_url or None

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
    # app.extensions["w3"] is no longer set (nothing read it); use get_web3().


def get_db():
    """Get the MongoDB database instance."""
    return db


def get_web3():
    """Get the Web3 instance (built on first call; None if not configured)."""
    global w3, _w3_ready
    if not _w3_ready:
        _w3_ready = True
        if _w3_rpc_url:
            try:
                from web3 import Web3
                w3 = Web3(Web3.HTTPProvider(_w3_rpc_url, request_kwargs={"timeout": 5}))
            except Exception:
                w3 = None
    return w3
