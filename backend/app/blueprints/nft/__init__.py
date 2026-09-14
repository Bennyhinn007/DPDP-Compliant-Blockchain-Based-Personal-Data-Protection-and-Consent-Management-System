from flask import Blueprint

nft_bp = Blueprint("nft", __name__)

from app.blueprints.nft import routes  # noqa: E402, F401
