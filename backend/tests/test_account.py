"""Tests for the account page: password change and second admin (ticket #54).

The point of the feature is that the owner is not locked out when they lose SSH
access, so these tests exercise the whole path: the session guard, the form CSRF
token, the password rules, the login with the new password, and the revocation
of the other sessions.
"""

import pytest
from sqlalchemy import select

from app import auth
from app.models import Admin


def admin_row(db_session, username: str = "testadmin") -> Admin:
    return db_session.execute(
        select(Admin).where(Admin.username == username)
    ).scalar_one()


def post_password(client, csrf_token: str, current: str, new: str, confirm: str):
    return client.post(
        "/admin/account/password",
        data={
            "current_password": current,
            "new_password": new,
            "confirm_password": confirm,
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )


def post_new_admin(client, csrf_token: str, username: str, password: str, confirm: str):
    return client.post(
        "/admin/account/admins",
        data={
            "username": username,
            "password": password,
            "confirm_password": confirm,
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )


# --- Guards ----------------------------------------------------------------


def test_account_page_requires_a_session(client):
    assert client.get("/admin/account").status_code == 401


def test_account_posts_require_a_session(client):
    assert post_password(client, "", "a", "b", "b").status_code == 401
    assert post_new_admin(client, "", "someone", "password1", "password1").status_code == 401


def test_account_page_has_both_forms_and_a_csrf_token(client, auth_cookies):
    resp = client.get("/admin/account")

    assert resp.status_code == 200
    assert 'action="/admin/account/password"' in resp.text
    assert 'action="/admin/account/admins"' in resp.text
    assert 'name="csrf_token"' in resp.text


def test_account_page_only_renders_known_error_codes(client, auth_cookies):
    known = client.get("/admin/account?error=invalid_current").text
    assert 'data-i18n="account_error_invalid_current"' in known

    # A crafted query string must not become page text.
    unknown = client.get("/admin/account?error=%3Cscript%3Ealert(1)%3C/script%3E").text
    assert "<script>alert(1)</script>" not in unknown


def test_account_posts_reject_a_missing_or_wrong_csrf_token(
    client, admin_user, auth_cookies
):
    assert post_password(
        client, "wrong", admin_user["password"], "newpass456", "newpass456"
    ).status_code == 403
    assert post_new_admin(
        client, "wrong", "second", "secondpass1", "secondpass1"
    ).status_code == 403


# --- Password rules --------------------------------------------------------


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        ("short1", "too_short"),
        ("letters-only", "needs_digit"),
        ("12345678", "needs_letter"),
        ("a1" * 40, "too_long"),
    ],
)
def test_password_problem_reports_the_first_broken_rule(password, problem):
    assert auth.password_problem(password) == problem


def test_password_problem_accepts_a_reasonable_password():
    assert auth.password_problem("newpass456") is None


# --- Changing a password ---------------------------------------------------


def test_change_password_rotates_the_hash_and_keeps_the_current_session(
    client, db_session, admin_user, auth_cookies, csrf_token
):
    admin = admin_row(db_session)
    other_token = auth.create_session(db_session, admin.id).token

    resp = post_password(
        client,
        csrf_token,
        admin_user["password"],
        "newpass456",
        "newpass456",
    )

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("changed=1")

    # The session that made the change survives; every other one is gone.
    assert auth.get_session(db_session, auth_cookies["session_token"]) is not None
    assert auth.get_session(db_session, other_token) is None

    # The old password stops working and the new one logs in.
    assert auth.authenticate_admin(db_session, "testadmin", admin_user["password"]) is None
    assert auth.authenticate_admin(db_session, "testadmin", "newpass456") is not None

    # The session cookie itself still works against the panel.
    assert client.get("/admin").status_code == 200


def test_change_password_requires_the_current_password(
    client, db_session, admin_user, auth_cookies, csrf_token
):
    resp = post_password(client, csrf_token, "wrong-password", "newpass456", "newpass456")

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=invalid_current")
    assert auth.authenticate_admin(db_session, "testadmin", admin_user["password"]) is not None
    assert auth.authenticate_admin(db_session, "testadmin", "newpass456") is None


def test_change_password_rejects_a_mismatch(client, admin_user, auth_cookies, csrf_token):
    resp = post_password(
        client, csrf_token, admin_user["password"], "newpass456", "different456"
    )

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=password_mismatch")


@pytest.mark.parametrize("new_password", ["short1", "lettersonly"])
def test_change_password_rejects_a_weak_password(
    client, admin_user, auth_cookies, csrf_token, new_password
):
    resp = post_password(
        client, csrf_token, admin_user["password"], new_password, new_password
    )

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=password_weak")


def test_change_password_rejects_the_current_password(
    client, admin_user, auth_cookies, csrf_token
):
    resp = post_password(
        client,
        csrf_token,
        admin_user["password"],
        admin_user["password"],
        admin_user["password"],
    )

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=password_same")


def test_a_failed_change_leaves_the_old_password_working(
    client, db_session, admin_user, auth_cookies, csrf_token
):
    post_password(client, csrf_token, "wrong-password", "newpass456", "newpass456")

    assert auth.authenticate_admin(db_session, "testadmin", admin_user["password"]) is not None
    assert auth.authenticate_admin(db_session, "testadmin", "newpass456") is None


# --- Creating a second admin -----------------------------------------------


def test_create_a_second_admin_who_can_log_in(
    client, db_session, auth_cookies, csrf_token
):
    resp = post_new_admin(client, csrf_token, "second", "secondpass1", "secondpass1")

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("created=1")

    second = admin_row(db_session, "second")
    assert auth.verify_password("secondpass1", second.password_hash)

    login = client.post(
        "/admin/login",
        data={"username": "second", "password": "secondpass1"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    assert login.headers["location"] == "/admin"
    assert "session_token" in dict(login.cookies)


def test_create_admin_rejects_a_duplicate_username(
    client, db_session, admin_user, auth_cookies, csrf_token
):
    resp = post_new_admin(
        client, csrf_token, admin_user["username"], "secondpass1", "secondpass1"
    )

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=username_taken")
    # The original hash is untouched.
    assert auth.verify_password(
        admin_user["password"], admin_row(db_session, admin_user["username"]).password_hash
    )


@pytest.mark.parametrize("username", ["ab", "bad<name", "bad'name", "bad\\name"])
def test_create_admin_rejects_an_unsafe_username(
    client, auth_cookies, csrf_token, username
):
    resp = post_new_admin(client, csrf_token, username, "secondpass1", "secondpass1")

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=username_invalid")


def test_create_admin_requires_a_username(client, auth_cookies, csrf_token):
    resp = post_new_admin(client, csrf_token, "   ", "secondpass1", "secondpass1")

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=username_required")


def test_create_admin_rejects_a_mismatch(client, auth_cookies, csrf_token):
    resp = post_new_admin(client, csrf_token, "second", "secondpass1", "secondpass2")

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=password_mismatch")


def test_create_admin_rejects_a_weak_password(client, auth_cookies, csrf_token):
    resp = post_new_admin(client, csrf_token, "second", "short1", "short1")

    assert resp.status_code == 303
    assert resp.headers["location"].endswith("error=password_weak")


def test_creating_an_admin_does_not_sign_the_creator_out(
    client, auth_cookies, csrf_token
):
    post_new_admin(client, csrf_token, "second", "secondpass1", "secondpass1")

    assert client.get("/admin").status_code == 200
