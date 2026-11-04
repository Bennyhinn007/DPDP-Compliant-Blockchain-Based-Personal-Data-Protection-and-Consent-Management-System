from flask import Blueprint

biometric_bp = Blueprint("biometric", __name__)

from app.blueprints.biometric import routes  # noqa: E402, F401
