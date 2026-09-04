"""
Local development entry point.

Usage:
    python run.py
"""

import os
from dotenv import load_dotenv

load_dotenv()  # populate os.environ from .env before the app reads config

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=app.config.get("DEBUG", False))
