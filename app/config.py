"""
Application configuration.

All secrets and environment-specific values are read from environment
variables (see .env.example). Nothing sensitive is hard-coded here.
"""

import os


class BaseConfig:
    """Shared configuration for all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session / cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour, in seconds

    # CSRF (Flask-WTF)
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # allow http on localhost


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # requires HTTPS


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False  # simplifies posting test forms
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "sqlite:///:memory:"
    )
    SECRET_KEY = "testing-secret-key"


_CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str = None):
    """Resolve a config class by name, falling back to FLASK_ENV/default."""
    name = name or os.environ.get("FLASK_CONFIG") or os.environ.get("FLASK_ENV") or "development"
    return _CONFIGS.get(name, DevelopmentConfig)
