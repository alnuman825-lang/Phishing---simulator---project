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
    for path in ("/admin/users", "/admin/results", "/admin/scenarios"):
        resp = client.get(path)
        assert resp.status_code == 403, f"{path} should be forbidden for a non-admin"


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
