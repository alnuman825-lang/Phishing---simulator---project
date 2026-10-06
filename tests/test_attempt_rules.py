"""
Tests for the one-attempt-per-scenario rule, duplicate-submission
prevention, feedback access without an attempt, and inactive scenarios.

These behaviours existed in the application before this file was added
but were not covered by any test.
"""

import re

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.response import Response
from app.models.scenario import Scenario
from app.models.user import User


def register(client, name="Sam Test", email="sam@example.com", password="password123"):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password, "confirm_password": password},
        follow_redirects=True,
    )


def login(client, email="sam@example.com", password="password123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def make_scenario(db, correct="report", title="Test Scenario", is_active=True):
    scenario = Scenario(
        title=title,
        sender_name="Tester",
        sender_email="tester@example.com",
        subject="Test subject",
        body="Test body",
        context="Test context",
        explanation="Test explanation",
        correct_response=correct,
        difficulty="beginner",
        category="general",
        is_active=is_active,
    )
    db.session.add(scenario)
    db.session.commit()
    return scenario


# --- One attempt per scenario -------------------------------------------------

def test_completed_scenario_redirects_to_feedback_instead_of_form(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db)
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"})

    resp = client.get(f"/training/{scenario.id}")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/training/{scenario.id}/feedback")


def test_second_submission_does_not_create_or_change_a_response(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db, correct="report")
    client.post(f"/training/{scenario.id}", data={"selected_response": "click"})

    # Try to "fix" the wrong answer by submitting the correct one afterwards.
    resp = client.post(f"/training/{scenario.id}", data={"selected_response": "report"})

    assert resp.status_code == 302
    stored = Response.query.filter_by(scenario_id=scenario.id).all()
    assert len(stored) == 1
    assert stored[0].selected_response == "click"
    assert stored[0].is_correct is False
    assert stored[0].score == 0


def test_second_submission_tells_the_user_it_is_already_completed(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db)
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"})

    resp = client.post(
        f"/training/{scenario.id}",
        data={"selected_response": "ignore"},
        follow_redirects=True,
    )

    assert b"already completed this scenario" in resp.data


# --- Duplicate submission prevention at the database level --------------------

def test_database_rejects_duplicate_response_for_same_user_and_scenario(client, db):
    register(client)
    user = User.query.filter_by(email="sam@example.com").first()
    scenario = make_scenario(db)
    db.session.add(Response(
        user_id=user.id, scenario_id=scenario.id,
        selected_response="report", is_correct=True, score=100,
    ))
    db.session.commit()

    db.session.add(Response(
        user_id=user.id, scenario_id=scenario.id,
        selected_response="click", is_correct=False, score=0,
    ))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    assert Response.query.filter_by(user_id=user.id, scenario_id=scenario.id).count() == 1


def test_duplicate_submission_race_is_handled_without_server_error(client, db, monkeypatch):
    """Simulates two near-simultaneous submissions (e.g. a double click).

    The route's "already attempted?" check finds nothing, but the database
    unique constraint rejects the insert. The route must roll back and
    redirect rather than return a 500.
    """
    register(client)
    login(client)
    scenario = make_scenario(db)
    scenario_id = scenario.id

    def raise_integrity_error():
        raise IntegrityError("INSERT INTO responses", {}, Exception("uq_user_scenario"))

    monkeypatch.setattr(db.session, "commit", raise_integrity_error)
    resp = client.post(f"/training/{scenario_id}", data={"selected_response": "report"})
    monkeypatch.undo()

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/training/{scenario_id}/feedback")
    assert Response.query.filter_by(scenario_id=scenario_id).count() == 0


# --- Feedback access when no attempt exists -----------------------------------

def test_feedback_without_attempt_redirects_to_training_list(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db)

    resp = client.get(f"/training/{scenario.id}/feedback")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/training")


def test_feedback_without_attempt_does_not_reveal_the_answer(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db)

    resp = client.get(f"/training/{scenario.id}/feedback", follow_redirects=True)

    assert b"attempted that scenario yet" in resp.data
    assert scenario.explanation.encode() not in resp.data
    assert b"The recommended response was" not in resp.data


def test_feedback_for_another_users_attempt_is_not_shown(client, db):
    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    scenario = make_scenario(db)
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"})
    client.get("/logout")

    register(client, name="User B", email="b@example.com")
    login(client, email="b@example.com")
    resp = client.get(f"/training/{scenario.id}/feedback")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/training")


def test_feedback_requires_login(client, db):
    scenario = make_scenario(db)
    resp = client.get(f"/training/{scenario.id}/feedback")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_feedback_for_unknown_scenario_returns_404(client, db):
    register(client)
    login(client)
    assert client.get("/training/9999/feedback").status_code == 404


# --- Inactive scenarios -------------------------------------------------------

def test_inactive_scenario_is_not_listed(client, db):
    register(client)
    login(client)
    make_scenario(db, title="Visible Scenario")
    make_scenario(db, title="Hidden Scenario", is_active=False)

    resp = client.get("/training")

    assert b"Visible Scenario" in resp.data
    assert b"Hidden Scenario" not in resp.data


def test_inactive_scenario_cannot_be_opened(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db, is_active=False)
    assert client.get(f"/training/{scenario.id}").status_code == 404


def test_inactive_scenario_cannot_be_answered(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db, is_active=False)

    resp = client.post(f"/training/{scenario.id}", data={"selected_response": "report"})

    assert resp.status_code == 404
    assert Response.query.count() == 0


def test_inactive_scenario_is_excluded_from_dashboard_total(client, db):
    register(client)
    login(client)
    make_scenario(db, title="Active One")
    make_scenario(db, title="Active Two")
    make_scenario(db, title="Retired", is_active=False)

    resp = client.get("/dashboard")

    assert b"0 / 2" in resp.data
    assert b"0 / 3" not in resp.data


def test_inactive_scenario_is_excluded_from_admin_overview_count(client, db):
    register(client, name="Admin", email="admin@example.com")
    admin = User.query.filter_by(email="admin@example.com").first()
    admin.role = "admin"
    db.session.commit()
    login(client, email="admin@example.com")
    make_scenario(db, title="Active One")
    make_scenario(db, title="Retired", is_active=False)

    resp = client.get("/admin/")

    assert resp.status_code == 200
    assert Scenario.query.count() == 2
    # The "Active scenarios" card must show 1, not 2.
    assert re.search(
        rb'stat-card__value">1</span>\s*<span class="stat-card__label">Active scenarios',
        resp.data,
    )
