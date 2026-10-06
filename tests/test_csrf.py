"""
CSRF protection tests.

Every other test module runs with CSRF disabled (see TestingConfig) so
forms can be posted without a token. Here the `csrf_client` fixture
turns protection back on, so these tests check the protection itself:
a state-changing POST without a valid token must be rejected, and the
same POST with the token rendered in the page must succeed.
"""

import re

from app.extensions import db
from app.models.response import Response
from app.models.scenario import Scenario
from app.models.user import User

TOKEN_PATTERN = re.compile(rb'name="csrf_token"[^>]*value="([^"]+)"')


def csrf_token_from(client, url):
    """Fetch a page and pull the CSRF token out of its form."""
    page = client.get(url)
    match = TOKEN_PATTERN.search(page.data)
    assert match, f"No CSRF token field found on {url}"
    return match.group(1).decode()


def register_with_token(client, email="sam@example.com", password="password123"):
    token = csrf_token_from(client, "/register")
    return client.post("/register", data={
        "name": "Sam Test", "email": email,
        "password": password, "confirm_password": password,
        "csrf_token": token,
    })


def login_with_token(client, email="sam@example.com", password="password123"):
    token = csrf_token_from(client, "/login")
    return client.post("/login", data={
        "email": email, "password": password, "csrf_token": token,
    })


def make_scenario():
    scenario = Scenario(
        title="CSRF Scenario", sender_name="Tester", sender_email="tester@example.com",
        subject="Test subject", body="Test body", explanation="Test explanation",
        correct_response="report",
    )
    db.session.add(scenario)
    db.session.commit()
    return scenario.id


def test_forms_render_a_csrf_token(csrf_client):
    assert csrf_token_from(csrf_client, "/register")
    assert csrf_token_from(csrf_client, "/login")


def test_registration_without_csrf_token_is_rejected(csrf_client):
    resp = csrf_client.post("/register", data={
        "name": "Sam Test", "email": "sam@example.com",
        "password": "password123", "confirm_password": "password123",
    })

    assert resp.status_code == 400
    assert User.query.count() == 0


def test_registration_with_invalid_csrf_token_is_rejected(csrf_client):
    resp = csrf_client.post("/register", data={
        "name": "Sam Test", "email": "sam@example.com",
        "password": "password123", "confirm_password": "password123",
        "csrf_token": "not-a-real-token",
    })

    assert resp.status_code == 400
    assert User.query.count() == 0


def test_registration_with_valid_csrf_token_succeeds(csrf_client):
    resp = register_with_token(csrf_client)

    assert resp.status_code == 302
    assert User.query.filter_by(email="sam@example.com").count() == 1


def test_login_without_csrf_token_is_rejected(csrf_client):
    register_with_token(csrf_client)

    resp = csrf_client.post("/login", data={
        "email": "sam@example.com", "password": "password123",
    })

    assert resp.status_code == 400
    # Still logged out: the dashboard sends us back to the login page.
    assert "/login" in csrf_client.get("/dashboard").headers["Location"]


def test_scenario_response_without_csrf_token_is_rejected(csrf_client):
    register_with_token(csrf_client)
    login_with_token(csrf_client)
    scenario_id = make_scenario()

    resp = csrf_client.post(f"/training/{scenario_id}", data={"selected_response": "report"})

    assert resp.status_code == 400
    assert Response.query.count() == 0


def test_scenario_response_with_valid_csrf_token_is_recorded(csrf_client):
    register_with_token(csrf_client)
    login_with_token(csrf_client)
    scenario_id = make_scenario()
    token = csrf_token_from(csrf_client, f"/training/{scenario_id}")

    resp = csrf_client.post(f"/training/{scenario_id}", data={
        "selected_response": "report", "csrf_token": token,
    })

    assert resp.status_code == 302
    stored = Response.query.one()
    assert stored.is_correct is True
    assert stored.score == 100
