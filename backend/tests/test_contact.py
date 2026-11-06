"""Tests for the public contact form and the shared admin inbox (#15).

The interesting failures here are not "does the row save" but the boundary:
markup must not survive into the inbox, the 1,000-character cap must be enforced
on the server rather than only by the form, a filled honeypot must not tell the
bot it was caught, and every admin must see the same messages. The public write
is also deliberately absent from the audit log, which is asserted rather than
assumed.
"""

import pytest
from sqlalchemy import select

from app.config import settings
from app.models import AuditEntry, Submission

VALID = {
    "name": "Ana",
    "contact": "ana@example.com",
    "subject": "Table for Friday",
    "message": "Do you have a table for six on Friday?",
    "website": "",
}


def submit(client, headers=None, **over):
    payload = {**VALID, **over}
    return client.post("/api/contact", json=payload, headers=headers)


def rows(db_session):
    return list(db_session.execute(select(Submission)).scalars().all())


def inbox(client):
    return client.get("/api/submissions").json()


# --- The public write ------------------------------------------------------


def test_a_visitor_can_send_a_message(client, db_session):
    resp = submit(
        client,
        headers={"User-Agent": "Browser/1.0"},
    )
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}

    stored = rows(db_session)
    assert len(stored) == 1
    assert stored[0].name == "Ana"
    assert stored[0].contact == "ana@example.com"
    assert stored[0].subject == "Table for Friday"
    assert stored[0].message == "Do you have a table for six on Friday?"
    assert stored[0].ip == "testclient"
    assert stored[0].user_agent == "Browser/1.0"
    assert stored[0].is_read is False
    assert stored[0].created_at is not None


def test_a_public_submission_is_not_written_to_the_audit_log(client, db_session):
    """The audit log records admin changes; a visitor's message is not one."""
    assert submit(client).status_code == 201
    assert db_session.execute(select(AuditEntry)).scalars().all() == []


def test_the_message_is_capped_at_one_thousand_characters(client):
    assert submit(client, message="a" * 1000).status_code == 201
    assert submit(client, message="a" * 1001).status_code == 422


@pytest.mark.parametrize("over", [
    {"name": ""},
    {"contact": ""},
    {"message": ""},
    {"message": "   \n\t  "},
    # Markup alone leaves nothing behind once the tags are stripped.
    {"message": "<script></script>"},
])
def test_required_fields_are_required_after_cleaning(client, over):
    assert submit(client, **over).status_code == 422


def test_markup_and_control_characters_never_reach_storage(client, db_session):
    resp = submit(
        client,
        name="<script>alert(1)</script>Ana",
        subject="<b>Hello</b>",
        message="<img src=x onerror=alert(1)>Hi <script>bad()</script>\x00 there",
    )
    assert resp.status_code == 201

    stored = rows(db_session)[0]
    for value in (stored.name, stored.contact, stored.subject, stored.message):
        assert "<" not in value
        assert ">" not in value
        assert "\x00" not in value
    assert stored.name == "alert(1)Ana"
    assert stored.subject == "Hello"
    assert stored.message == "Hi bad() there"


def test_whitespace_is_normalised_but_message_paragraphs_survive(client, db_session):
    resp = submit(
        client,
        name="  Ana \n  Maria  ",
        message="  Hello   there \n\n\n  second paragraph  ",
    )
    assert resp.status_code == 201

    stored = rows(db_session)[0]
    assert stored.name == "Ana Maria"
    assert stored.message == "Hello there\n\nsecond paragraph"


def test_a_filled_honeypot_is_silently_dropped(client, db_session):
    """A bot gets the same success response; nothing is stored."""
    resp = submit(client, website="http://spam.example")
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    assert rows(db_session) == []


def test_the_contact_endpoint_is_rate_limited_per_ip(client, db_session):
    for _ in range(settings.RATE_LIMIT_ATTEMPTS):
        assert submit(client).status_code == 201

    assert submit(client).status_code == 429
    assert len(rows(db_session)) == settings.RATE_LIMIT_ATTEMPTS


# --- The shared inbox ------------------------------------------------------


def test_the_inbox_needs_a_session(client):
    assert client.get("/api/submissions").status_code == 401


def test_the_inbox_lists_newest_first_with_an_unread_count(
    client, auth_cookies
):
    submit(client, name="First")
    submit(client, name="Second")

    data = inbox(client)
    assert [row["name"] for row in data["submissions"]] == ["Second", "First"]
    assert data["unread"] == 2


def test_an_admin_can_mark_a_message_read_and_unread(
    client, auth_cookies, csrf_token
):
    submit(client)
    message_id = inbox(client)["submissions"][0]["id"]

    read = client.patch(
        f"/api/submissions/{message_id}",
        json={"is_read": True},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert read.status_code == 200
    assert read.json()["is_read"] is True
    assert inbox(client)["unread"] == 0

    unread = client.patch(
        f"/api/submissions/{message_id}",
        json={"is_read": False},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert unread.status_code == 200
    assert inbox(client)["unread"] == 1


def test_an_admin_can_delete_a_message(client, auth_cookies, csrf_token):
    submit(client)
    message_id = inbox(client)["submissions"][0]["id"]

    resp = client.delete(
        f"/api/submissions/{message_id}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 204
    assert inbox(client)["submissions"] == []

    again = client.delete(
        f"/api/submissions/{message_id}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert again.status_code == 404


def test_admin_writes_need_the_csrf_token(client, auth_cookies):
    submit(client)
    message_id = inbox(client)["submissions"][0]["id"]

    assert client.patch(
        f"/api/submissions/{message_id}", json={"is_read": True}
    ).status_code == 403
    assert client.delete(f"/api/submissions/{message_id}").status_code == 403


def test_the_inbox_page_needs_a_session(client):
    assert client.get("/admin/inbox").status_code == 401


def test_the_inbox_page_renders_for_an_admin(client, auth_cookies):
    body = client.get("/admin/inbox").text
    assert "/api/submissions" in body
    assert "inbox_heading" in body
    assert "/admin/static/admin_i18n.js" in body


def test_the_dashboard_links_to_the_inbox_and_counts_unread(
    client, auth_cookies
):
    submit(client)
    body = client.get("/admin").text
    assert 'href="/admin/inbox"' in body
    assert '<span class="badge">1 ' in body


def test_the_dashboard_badge_is_absent_with_no_unread_messages(
    client, auth_cookies
):
    body = client.get("/admin").text
    assert 'href="/admin/inbox"' in body
    assert '<span class="badge">' not in body
