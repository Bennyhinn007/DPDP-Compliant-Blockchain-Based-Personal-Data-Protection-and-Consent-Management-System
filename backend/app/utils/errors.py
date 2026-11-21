"""
Custom Error Handling.

Standardized error responses across the application.
All API errors return JSON with consistent structure.
"""

from flask import jsonify


class AppError(Exception):
    """Base application error with HTTP status code."""

    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AppError):
    """Authentication failure (401)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationError(AppError):
    """Authorization failure (403)."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class NotFoundError(AppError):
    """Resource not found (404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConsentRequiredError(AppError):
    """Consent not granted for requested access (403)."""

    def __init__(self, message: str = "Consent not granted for this data access", consent_status: str = "absent"):
        super().__init__(message, status_code=403)
        self.consent_status = consent_status


class ValidationError(AppError):
    """Input validation failure (422)."""

    def __init__(self, message: str = "Validation failed", details: dict = None):
        super().__init__(message, status_code=422, details=details)


class RateLimitError(AppError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded. Please wait."):
        super().__init__(message, status_code=429)


def handle_app_error(error: AppError):
    """Handle custom application errors."""
    response = {
        "error": True,
        "message": error.message,
        "status_code": error.status_code,
    }
    if error.details:
        response["details"] = error.details
    return jsonify(response), error.status_code


def handle_validation_error(error):
    """Handle 400 Bad Request."""
    return jsonify({
        "error": True,
        "message": "Bad request",
        "status_code": 400,
    }), 400


def handle_not_found(error):
    """Handle 404 Not Found."""
    return jsonify({
        "error": True,
        "message": "Resource not found",
        "status_code": 404,
    }), 404


def handle_internal_error(error):
    """Handle 500 Internal Server Error."""
    return jsonify({
        "error": True,
        "message": "Internal server error",
        "status_code": 500,
    }), 500
