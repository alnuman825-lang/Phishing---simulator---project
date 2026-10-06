import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def csrf_client():
    """Test client for an app with CSRF protection switched ON.

    TestingConfig disables CSRF so ordinary tests can post forms without
    a token. These fixtures re-enable it so the protection itself is
    exercised. Flask-WTF reads WTF_CSRF_ENABLED at request time, so
    flipping the flag after create_app() is sufficient.
    """
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        _db.create_all()
        yield app.test_client()
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()
