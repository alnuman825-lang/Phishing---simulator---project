"""
CyberShield application factory.

Creates and configures the Flask application, initialises extensions,
and registers blueprints. Keeping this as a factory (rather than a
module-level `app = Flask(__name__)`) makes the app easier to test
and lets future team members add new blueprints without touching
this file's core logic.
"""

from flask import Flask

from app.config import get_config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_name: str = None) -> Flask:
    """Application factory.

    Args:
        config_name: Optional override, e.g. "testing". Defaults to
            reading FLASK_ENV / FLASK_CONFIG from the environment.
    """
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # --- Initialise extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # --- Register models so Flask-Migrate can see them ---
    from app.models import user, scenario, response  # noqa: F401

    # --- Register blueprints ---
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.training import training_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return db.session.get(User, int(user_id))

    return app
