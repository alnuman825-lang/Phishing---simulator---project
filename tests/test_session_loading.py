"""
Tests that the logged-in user is reloaded from the session cookie on
each request.

The shared `client` fixture keeps one application context open for the
whole test, so Flask-Login caches the user after login and never calls
the user loader in app/__init__.py again. These tests make each request
in its own context -- the way a real browser session behaves -- so the
loader is actually exercised.
"""

import pytest

from app import create_app
from app.extensions import db
from app.models.user import User


@pytest.fixture()
def fresh_client():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    yield app.test_client()
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def register_and_login(client):
    client.post("/register", data={
        "name": "Sam Test", "email": "sam@example.com",
        "password": "password123", "confirm_password": "password123",
    })
    return client.post("/login", data={"email": "sam@example.com", "password": "password123"})


def test_user_is_reloaded_from_session_on_later_requests(fresh_client):
    register_and_login(fresh_client)

    first = fresh_client.get("/dashboard")
    second = fresh_client.get("/training")

    assert first.status_code == 200
    assert b"Welcome, Sam Test" in first.data
    assert second.status_code == 200


def test_session_for_deleted_user_is_treated_as_logged_out(fresh_client):
    register_and_login(fresh_client)
    with fresh_client.application.app_context():
        db.session.delete(User.query.filter_by(email="sam@example.com").one())
        db.session.commit()

    resp = fresh_client.get("/dashboard")

    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_logout_ends_the_session(fresh_client):
    register_and_login(fresh_client)
    fresh_client.get("/logout")

    resp = fresh_client.get("/dashboard")

    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
