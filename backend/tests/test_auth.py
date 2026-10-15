"""Tests for authentication endpoints."""


def test_login_page_loads(client):
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    assert "Admin Login" in resp.text or "login" in resp.text.lower()


def test_login_success(client, admin_user):
    resp = client.post(
        "/admin/login",
        data={
            "username": admin_user["username"],
            "password": admin_user["password"],
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "session_token" in dict(resp.cookies)


def test_login_wrong_password(client, admin_user):
    resp = client.post(
        "/admin/login",
        data={
            "username": admin_user["username"],
            "password": "wrongpassword",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "error" in resp.headers.get("location", "")


def test_login_nonexistent_user(client):
    resp = client.post(
        "/admin/login",
        data={"username": "nobody", "password": "wrong"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "error" in resp.headers.get("location", "")


def test_logout(client, auth_cookies):
    resp = client.post(
        "/admin/logout",
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_admin_requires_auth(client):
    resp = client.get("/admin")
    assert resp.status_code == 401


def test_admin_panel_requires_auth(client):
    """The admin panel itself must never be reachable without a session."""
    resp = client.get("/admin")
    assert resp.status_code == 401


def test_session_cookie_is_httponly(client, admin_user):
    resp = client.post(
        "/admin/login",
        data={
            "username": admin_user["username"],
            "password": admin_user["password"],
        },
        follow_redirects=False,
    )
    # Check Set-Cookie header for HttpOnly
    set_cookie = resp.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie


def test_rate_limiting(client, admin_user):
    """After 5 failed attempts, the 6th should be rate limited."""
    for i in range(5):
        resp = client.post(
            "/admin/login",
            data={
                "username": admin_user["username"],
                "password": "wrong",
            },
            follow_redirects=False,
        )
        # First 5 should redirect with error
        assert resp.status_code == 303

    # 6th attempt should be rate limited
    resp = client.post(
        "/admin/login",
        data={
            "username": admin_user["username"],
            "password": "wrong",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "rate_limited" in resp.headers.get("location", "")
