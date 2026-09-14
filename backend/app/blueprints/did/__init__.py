from flask import Blueprint

did_bp = Blueprint("did", __name__)

from app.blueprints.did import routes  # noqa: E402, F401
