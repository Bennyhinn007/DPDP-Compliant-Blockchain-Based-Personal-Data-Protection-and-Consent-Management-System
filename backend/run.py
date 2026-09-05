"""
Application Entry Point.

Starts the Flask development server.
Usage: python run.py
"""

import os

# Load environment variables from .env BEFORE importing the app, because
# config classes read os.environ at import time.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional; env may be provided by the OS / docker

from app import create_app

config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    is_dev = config_name == "development"
    # use_reloader is disabled to avoid a known Windows + Python 3.13 socket
    # error in Flask's auto-reloader (WinError 10038). Debug mode stays on.
    app.run(
        host="0.0.0.0",
        port=port,
        debug=is_dev,
        use_reloader=False,
    )
