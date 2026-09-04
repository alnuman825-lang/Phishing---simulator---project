"""
Extension instances.

Declared here (uninitialised) and bound to the app in create_app()
via .init_app(). This avoids circular imports between app/__init__.py
and the models/routes that need db, login_manager, etc.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
