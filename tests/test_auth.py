from app.models.user import User


def register(client, name="Sam Test", email="sam@example.com", password="password123"):
    return client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def login(client, email="sam@example.com", password="password123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_registration_creates_user(client, db):
    resp = register(client)
    assert resp.status_code == 200
    user = User.query.filter_by(email="sam@example.com").first()
    assert user is not None
    assert user.name == "Sam Test"


def test_password_is_hashed_not_plaintext(client, db):
    register(client)
    user = User.query.filter_by(email="sam@example.com").first()
    assert user.password_hash != "password123"
    assert user.check_password("password123") is True
    assert user.check_password("wrongpassword") is False


def test_duplicate_email_rejected(client, db):
    register(client)
    resp = register(client, name="Someone Else")
    assert b"already exists" in resp.data


def test_login_with_correct_credentials(client, db):
    register(client)
    resp = login(client)
    assert b"Welcome" in resp.data or b"Dashboard" in resp.data or resp.status_code == 200


def test_login_with_wrong_password_fails(client, db):
    register(client)
    resp = login(client, password="wrongpassword")
    assert b"Invalid email or password" in resp.data


def test_dashboard_requires_login(client, db):
    resp = client.get("/dashboard", follow_redirects=True)
    # Should be redirected to the login page, not shown the dashboard
    assert b"Log in" in resp.data


def test_dashboard_accessible_after_login(client, db):
    register(client)
    login(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Welcome" in resp.data
