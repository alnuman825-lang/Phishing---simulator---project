from app.models.user import User
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


def make_admin(db, email="admin@example.com", password="adminpass123"):
    admin = User(name="Admin User", email=email, role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    return admin


def make_scenario(db, correct="report", title="Admin Test Scenario"):
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


def test_admin_requires_login(client, db):
    resp = client.get("/admin/", follow_redirects=True)
    assert b"Log in" in resp.data


def test_regular_user_forbidden_from_admin(client, db):
    register(client)
    login(client)
    resp = client.get("/admin/")
    assert resp.status_code == 403


def test_regular_user_forbidden_from_admin_subpages(client, db):
    register(client)
    login(client)
    for path in (
        "/admin/users",
        "/admin/results",
        "/admin/scenarios",
        "/admin/analytics",
        "/admin/results/export.csv",
    ):
        resp = client.get(path)
        assert resp.status_code == 403, f"{path} should be forbidden for a non-admin"


def test_regular_user_forbidden_from_admin_user_detail(client, db):
    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    target = User.query.filter_by(email="a@example.com").first()
    resp = client.get(f"/admin/users/{target.id}")
    assert resp.status_code == 403


def test_admin_can_access_overview(client, db):
    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get("/admin/")
    assert resp.status_code == 200


def test_admin_users_page_lists_users_without_password_hash(client, db):
    user = User(name="Regular Person", email="reg@example.com", role="user")
    user.set_password("somepassword123")
    db.session.add(user)
    db.session.commit()

    admin = make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")

    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert b"Regular Person" in resp.data
    assert b"reg@example.com" in resp.data
    # The real password hash must never appear in the rendered page
    assert user.password_hash.encode() not in resp.data
    assert admin.password_hash.encode() not in resp.data


def test_admin_sees_all_users_results(client, db):
    scenario = make_scenario(db, correct="report")

    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)
    client.get("/logout")

    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get("/admin/results")

    assert resp.status_code == 200
    assert b"User A" in resp.data
    assert scenario.title.encode() in resp.data


def test_admin_scenario_performance_shows_accuracy(client, db):
    scenario = make_scenario(db, correct="report")

    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)
    client.get("/logout")

    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get("/admin/scenarios")

    assert resp.status_code == 200
    assert scenario.title.encode() in resp.data
    assert b"100.0%" in resp.data


def test_admin_analytics_page_loads(client, db):
    # This route previously referenced a non-existent template and 500'd —
    # this test exists specifically to catch that regression.
    make_scenario(db)
    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get("/admin/analytics")
    assert resp.status_code == 200


def test_admin_analytics_shows_category_and_difficulty_breakdown(client, db):
    scenario = make_scenario(db, correct="report")

    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)
    client.get("/logout")

    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get("/admin/analytics")

    assert resp.status_code == 200
    assert b"general" in resp.data  # category
    assert b"Beginner" in resp.data  # difficulty, capitalised in the template


def test_admin_analytics_integrates_phishing_indicator_analysis(client, db):
    scenario = Scenario(
        title="Urgent Credential Scenario",
        sender_name="Tester",
        sender_email="tester@example.com",
        subject="URGENT: verify your password immediately",
        body="Please confirm your account and payment details within 24 hours.",
        context="ctx",
        explanation="exp",
        correct_response="report",
        difficulty="beginner",
        category="general",
    )
    db.session.add(scenario)
    db.session.commit()

    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get("/admin/analytics")

    assert resp.status_code == 200
    assert b"Urgency or pressure" in resp.data
    assert b"Credential request" in resp.data
    assert b"Financial request" in resp.data
    assert b"Analyzer risk level" in resp.data


def test_admin_user_detail_shows_target_users_history(client, db):
    scenario = make_scenario(db, correct="report")

    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)
    client.get("/logout")

    target = User.query.filter_by(email="a@example.com").first()

    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get(f"/admin/users/{target.id}")

    assert resp.status_code == 200
    assert b"User A" in resp.data
    assert scenario.title.encode() in resp.data
    assert b"1 / 1" in resp.data


def test_admin_user_detail_does_not_leak_other_users_data(client, db):
    scenario_a = make_scenario(db, correct="report", title="A Scenario")
    scenario_b = make_scenario(db, correct="ignore", title="B Scenario")

    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    client.post(f"/training/{scenario_a.id}", data={"selected_response": "report"}, follow_redirects=True)
    client.get("/logout")

    register(client, name="User B", email="b@example.com")
    login(client, email="b@example.com")
    client.post(f"/training/{scenario_b.id}", data={"selected_response": "ignore"}, follow_redirects=True)
    client.get("/logout")

    user_b = User.query.filter_by(email="b@example.com").first()

    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get(f"/admin/users/{user_b.id}")

    assert resp.status_code == 200
    assert b"B Scenario" in resp.data
    assert b"A Scenario" not in resp.data


def test_admin_can_export_results_csv(client, db):
    scenario = make_scenario(db, correct="report")

    register(client, name="User A", email="a@example.com")
    login(client, email="a@example.com")
    client.post(f"/training/{scenario.id}", data={"selected_response": "report"}, follow_redirects=True)
    client.get("/logout")

    make_admin(db)
    login(client, email="admin@example.com", password="adminpass123")
    resp = client.get("/admin/results/export.csv")

    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers.get("Content-Disposition", "")
    body = resp.data.decode()
    assert "user_name" in body.splitlines()[0]
    assert "User A" in body
    assert scenario.title in body
