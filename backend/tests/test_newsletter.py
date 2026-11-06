"""Tests for newsletter signups (ticket #12).

The public write is the part that has to be defensive: explicit consent, a
honeypot, a rate limit and no information leak about whether an address is
already on the list. The admin side is a list, an active switch and a CSV.
"""

import pytest
from sqlalchemy import select

from app.models import Subscriber


@pytest.fixture()
def edit_as_admin(client, auth_cookies, csrf_token):
    def _edit(method, url, **kwargs):
        return client.request(method, url, headers={"X-CSRF-Token": csrf_token}, **kwargs)

    return _edit


def signup(client, **over):
    payload = {
        "email": "visitor@example.com",
        "name": "Visitor",
        "consent": True,
    }
    payload.update(over)
    return client.post("/api/newsletter", json=payload)


def rows(db_session):
    return db_session.execute(select(Subscriber)).scalars().all()


def test_a_signup_is_stored_with_consent(client, db_session):
    resp = signup(client)
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}

    [row] = rows(db_session)
    assert row.email == "visitor@example.com"
    assert row.name == "Visitor"
    assert row.consented_at is not None
    assert row.is_active is True
    assert row.ip != ""


def test_an_address_is_lower_cased(client, db_session):
    signup(client, email="Visitor@Example.COM")
    assert rows(db_session)[0].email == "visitor@example.com"


def test_consent_is_required(client, db_session):
    assert signup(client, consent=False).status_code == 422
    assert rows(db_session) == []


@pytest.mark.parametrize("email", ["", "not-an-email", "two@@example.com", "no-dot@example"])
def test_an_invalid_address_is_rejected(client, db_session, email):
    assert signup(client, email=email).status_code == 422
    assert rows(db_session) == []


def test_a_duplicate_signup_is_a_quiet_success(client, db_session):
    signup(client)
    resp = signup(client, name="Second time")
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    assert len(rows(db_session)) == 1


def test_the_honeypot_stores_nothing_but_looks_successful(client, db_session):
    resp = signup(client, website="http://spam.example")
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    assert rows(db_session) == []


def test_signups_are_rate_limited(client, db_session, monkeypatch):
    from app.routers import newsletter

    monkeypatch.setattr(newsletter.settings, "RATE_LIMIT_ATTEMPTS", 2)
    assert signup(client, email="one@example.com").status_code == 201
    assert signup(client, email="two@example.com").status_code == 201
    assert signup(client, email="three@example.com").status_code == 429
    assert len(rows(db_session)) == 2


# --- Admin list ------------------------------------------------------------


def test_the_subscriber_list_requires_a_session(client):
    assert client.get("/api/subscribers").status_code == 401


def test_the_admin_list_shows_counts(client, auth_cookies, db_session):
    signup(client, email="one@example.com")
    signup(client, email="two@example.com")

    resp = client.get("/api/subscribers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["active"] == 2
    assert {row["email"] for row in data["subscribers"]} == {"one@example.com", "two@example.com"}


def test_unsubscribing_keeps_the_row(client, edit_as_admin, db_session):
    signup(client)
    [row] = rows(db_session)

    resp = edit_as_admin("PATCH", f"/api/subscribers/{row.id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert len(rows(db_session)) == 1


def test_deleting_removes_the_row(client, edit_as_admin, db_session):
    signup(client)
    [row] = rows(db_session)

    assert edit_as_admin("DELETE", f"/api/subscribers/{row.id}").status_code == 204
    assert rows(db_session) == []


def test_a_write_needs_a_csrf_token(client, auth_cookies, db_session):
    signup(client)
    [row] = rows(db_session)
    resp = client.patch(f"/api/subscribers/{row.id}", json={"is_active": False})
    assert resp.status_code == 403


# --- CSV export ------------------------------------------------------------


def test_export_contains_only_active_addresses(client, edit_as_admin, db_session):
    signup(client, email="stay@example.com", name="Stay")
    signup(client, email="leave@example.com", name="Leave")
    leave = next(row for row in rows(db_session) if row.email == "leave@example.com")
    edit_as_admin("PATCH", f"/api/subscribers/{leave.id}", json={"is_active": False})

    resp = client.get("/api/subscribers/export.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    body = resp.text
    assert "stay@example.com" in body
    assert "leave@example.com" not in body
    assert body.splitlines()[0] == "email,name,consented_at,created_at"


def test_export_requires_a_session(client):
    assert client.get("/api/subscribers/export.csv").status_code == 401


# --- Admin page and dashboard ---------------------------------------------


def test_the_subscribers_page_needs_a_session(client):
    assert client.get("/admin/subscribers").status_code == 401


def test_the_subscribers_page_renders_for_an_admin(client, auth_cookies):
    body = client.get("/admin/subscribers").text
    assert "/api/subscribers" in body
    assert "/api/subscribers/export.csv" in body
    assert "subscribers_heading" in body


def test_the_dashboard_links_to_the_newsletter_and_counts_active(
    client, auth_cookies, db_session
):
    signup(client)
    body = client.get("/admin").text
    assert 'href="/admin/subscribers"' in body
    assert '1 <span data-i18n="subscriber_active_label">' in body
