"""
Flask Application Factory.

Creates and configures the Flask application with all extensions,
blueprints, middleware, and error handlers.
"""

from flask import Flask
from flask_cors import CORS

from app.config import get_config
from app.extensions import init_extensions


def create_app(config_name: str = "development") -> Flask:
    """
    Application factory pattern.

    Args:
        config_name: Configuration environment (development, testing, production)

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # Production guardrail: fail fast on missing/insecure secrets rather than
    # starting up with silently-broken encryption or default dev keys.
    if config_name == "production":
        _assert_production_config(app)

    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config["CORS_ORIGINS"],
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True,
        }
    })

    # Initialize extensions (MongoDB, Web3)
    init_extensions(app)

    # Swagger API documentation
    try:
        from flasgger import Swagger
        from app.swagger_config import SWAGGER_TEMPLATE, SWAGGER_CONFIG
        Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG)
    except ImportError:
        pass  # flasgger optional in test environment

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    _register_error_handlers(app)

    # Health check endpoint
    @app.route("/health")
    def health_check():
        return {"status": "healthy", "service": "dpdp-healthcare-api"}, 200

    return app


def _assert_production_config(app: Flask) -> None:
    """Refuse to start production with missing or default-dev secrets."""
    problems = []

    if not app.config.get("ENCRYPTION_KEY"):
        problems.append("ENCRYPTION_KEY is not set (stored PII cannot be decrypted).")

    insecure_defaults = {
        "SECRET_KEY": "dev-secret-key-change-in-production",
        "JWT_SECRET_KEY": "jwt-dev-secret-change-in-production",
    }
    for key, dev_value in insecure_defaults.items():
        if app.config.get(key) == dev_value:
            problems.append(f"{key} is still the insecure development default.")

    if "mongodb://localhost" in str(app.config.get("MONGO_URI", "")):
        problems.append("MONGO_URI points at localhost (set your Atlas connection string).")

    if problems:
        raise RuntimeError(
            "Refusing to start in production due to configuration problems:\n  - "
            + "\n  - ".join(problems)
        )


def _register_blueprints(app: Flask) -> None:
    """Register all API blueprints."""
    from app.blueprints.auth import auth_bp
    from app.blueprints.patients import patients_bp
    from app.blueprints.doctors import doctors_bp
    from app.blueprints.pharmacy import pharmacy_bp
    from app.blueprints.consents import consents_bp
    from app.blueprints.audit import audit_bp
    from app.blueprints.blockchain import blockchain_bp
    from app.blueprints.integrity import integrity_bp
    from app.blueprints.compliance import compliance_bp
    # SIH 26125 identity extension (ADDITIVE — new blueprint, existing ones unchanged)
    from app.blueprints.did import did_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(patients_bp, url_prefix="/api/v1/patients")
    app.register_blueprint(doctors_bp, url_prefix="/api/v1/doctors")
    app.register_blueprint(pharmacy_bp, url_prefix="/api/v1/pharmacy")
    app.register_blueprint(consents_bp, url_prefix="/api/v1/consents")
    app.register_blueprint(audit_bp, url_prefix="/api/v1/audit")
    app.register_blueprint(blockchain_bp, url_prefix="/api/v1/blockchain")
    app.register_blueprint(integrity_bp, url_prefix="/api/v1/integrity")
    app.register_blueprint(compliance_bp, url_prefix="/api/v1/compliance")
    app.register_blueprint(did_bp, url_prefix="/api/v1/did")


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    from app.utils.errors import (
        AppError,
        handle_app_error,
        handle_validation_error,
        handle_not_found,
        handle_internal_error,
    )

    app.register_error_handler(AppError, handle_app_error)
    app.register_error_handler(400, handle_validation_error)
    app.register_error_handler(404, handle_not_found)
    app.register_error_handler(500, handle_internal_error)
