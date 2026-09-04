from app.extensions import db as _db
from app.models.scenario import Scenario
from app.models.response import Response


def register(client, name="Sam Test", email="sam@example.com", password="password123"):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password, "confirm_password": password},
        follow_redirects=True,
    )


def login(client, email="sam@example.com", password="password123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def make_scenario(db, correct="report", title="Test Scenario"):
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
    )
    db.session.add(scenario)
    db.session.commit()
    return scenario


def test_training_requires_login(client, db):
    resp = client.get("/training", follow_redirects=True)
    assert b"Log in" in resp.data


def test_authenticated_user_can_access_training(client, db):
    register(client)
    login(client)
    resp = client.get("/training")
    assert resp.status_code == 200


def test_scenario_can_be_displayed(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db)
    resp = client.get(f"/training/{scenario.id}")
    assert resp.status_code == 200
    assert scenario.subject.encode() in resp.data
    # The correct answer must never appear in the attempt page markup
    assert scenario.explanation.encode() not in resp.data


def test_valid_response_can_be_submitted_and_scored_correct(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db, correct="report")

    resp = client.post(
        f"/training/{scenario.id}",
        data={"selected_response": "report"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    stored = Response.query.filter_by(user_id=1, scenario_id=scenario.id).first()
    assert stored is not None
    assert stored.is_correct is True
    assert stored.score == 100


def test_incorrect_response_scores_zero(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db, correct="report")

    client.post(f"/training/{scenario.id}", data={"selected_response": "click"}, follow_redirects=True)

    stored = Response.query.filter_by(user_id=1, scenario_id=scenario.id).first()
    assert stored.is_correct is False
    assert stored.score == 0


def test_invalid_response_value_is_rejected(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db)

    client.post(f"/training/{scenario.id}", data={"selected_response": "not_a_real_option"}, follow_redirects=True)

    stored = Response.query.filter_by(scenario_id=scenario.id).first()
    assert stored is None  # nothing should have been recorded


def test_response_is_stored_in_database(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db)

    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)

    assert Response.query.filter_by(scenario_id=scenario.id).count() == 1


def test_user_can_view_own_results(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db, correct="report")
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)

    resp = client.get("/results")
    assert resp.status_code == 200
    assert scenario.title.encode() in resp.data


def test_user_cannot_see_another_users_results(client, db):
    # User A completes a scenario
    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    scenario = make_scenario(db, correct="report", title="A's Scenario")
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)
    client.get("/logout")

    # User B logs in and views their own (empty) results
    register(client, name="User B", email="b@example.com")
    login(client, email="b@example.com")
    resp = client.get("/results")

    assert b"A's Scenario" not in resp.data
    assert b"haven't completed" in resp.data


def test_feedback_page_includes_indicator_analysis(client, db):
    register(client)
    login(client)
    scenario = Scenario(
        title="Urgent Account Alert",
        sender_name="Tester",
        sender_email="tester@example.com",
        subject="URGENT: verify your password immediately",
        body="Please confirm your account and payment details within 24 hours.",
        context="Test context",
        explanation="Test explanation",
        correct_response="report",
        difficulty="beginner",
        category="general",
    )
    db.session.add(scenario)
    db.session.commit()

    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)
    resp = client.get(f"/training/{scenario.id}/feedback")

    assert resp.status_code == 200
    assert b"Automated Indicator Analysis" in resp.data
    assert b"Urgency or pressure" in resp.data
    assert b"Credential request" in resp.data


def test_dashboard_updates_after_completing_scenario(client, db):
    register(client)
    login(client)
    scenario = make_scenario(db, correct="report")

    before = client.get("/dashboard")
    assert b"0 / 1" in before.data

    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)

    after = client.get("/dashboard")
    assert b"1 / 1" in after.data
