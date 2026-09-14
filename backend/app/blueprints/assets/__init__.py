from flask import Blueprint

assets_bp = Blueprint("assets", __name__)

from app.blueprints.assets import routes  # noqa: E402, F401
