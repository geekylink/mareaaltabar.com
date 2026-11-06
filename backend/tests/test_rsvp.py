"""Tests for free event RSVPs (ticket #25).

An RSVP is a head count, not a reservation and not a ticket. The failures worth
pinning are: an RSVP for an event the public cannot see, a party size outside
the cap, a bot filling the honeypot, a flood from one IP, and an event deletion
that leaves orphan guests behind.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import Rsvp, SpecialEvent
from app.schemas import RESERVATION_MAX_GUESTS
from app.ssr import bar_today


def future(days=30):
    return (date.fromisoformat(bar_today()[1]) + timedelta(days=days)).isoformat()


def past(days=30):
    return (date.fromisoformat(bar_today()[1]) - timedelta(days=days)).isoformat()


def create_event(client, csrf_token, **over):
    payload = {
        "date": future(),
        "title_en": "DJ Sol",
        "title_es": "DJ Sol",
        "description_en": "Guest set on the terrace.",
        "description_es": "Sesión invitada en la terraza.",
        "start_time": "21:00",
        "end_time": "02:00",
        "image_url": "",
        "is_active": True,
        **over,
    }
    return client.post(
        "/api/special-events",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
    )


def rsvp(client, event_id, **over):
    payload = {
        "name": "Ana",
        "contact": "ana@example.com",
        "party_size": 2,
        "notes": "",
        "website": "",
    }
    payload.update(over)
    return client.post(f"/api/special-events/{event_id}/rsvp", json=payload)


def rows(db_session):
    return list(db_session.execute(select(Rsvp)).scalars().all())


def events(db_session):
    return list(db_session.execute(select(SpecialEvent)).scalars().all())


def add_event(db_session, **over):
    """Insert an event directly when the admin API would reject its date."""
    row = SpecialEvent(
        date=over.get("date", future()),
        title_en=over.get("title_en", "DJ Sol"),
        title_es=over.get("title_es", "DJ Sol"),
        description_en="",
        description_es="",
        start_time="21:00",
        end_time="02:00",
        image_url="",
        is_active=over.get("is_active", True),
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row.id


@pytest.fixture()
def event_id(client, auth_cookies, csrf_token):
    return create_event(client, csrf_token).json()["id"]


# --- Public RSVP -----------------------------------------------------------


def test_a_guest_can_rsvp_to_an_upcoming_event(
    client, auth_cookies, csrf_token, db_session, event_id
):
    resp = client.post(
        f"/api/special-events/{event_id}/rsvp",
        json={
            "name": "Ana",
            "contact": "ana@example.com",
            "party_size": 4,
            "notes": "Celebrating a birthday.",
        },
        headers={"User-Agent": "Marea Alta test browser"},
    )
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}

    [row] = rows(db_session)
    assert row.event_id == event_id
    assert row.name == "Ana"
    assert row.contact == "ana@example.com"
    assert row.party_size == 4
    assert row.notes == "Celebrating a birthday."
    assert row.ip != ""
    assert row.user_agent == "Marea Alta test browser"


@pytest.mark.parametrize("field, value", [
    ("name", ""),
    ("contact", ""),
    ("party_size", 0),
    ("party_size", RESERVATION_MAX_GUESTS + 1),
])
def test_invalid_rsvps_are_rejected(
    client, auth_cookies, csrf_token, db_session, event_id, field, value
):
    assert rsvp(client, event_id, **{field: value}).status_code == 422
    assert rows(db_session) == []


def test_an_unknown_event_is_404(client, db_session):
    assert rsvp(client, 9999).status_code == 404
    assert rows(db_session) == []


def test_a_hidden_event_is_404(client, auth_cookies, csrf_token, db_session):
    event_id = create_event(client, csrf_token, is_active=False).json()["id"]
    assert rsvp(client, event_id).status_code == 404
    assert rows(db_session) == []


def test_a_past_event_is_404(client, db_session):
    event_id = add_event(db_session, date=past())
    assert rsvp(client, event_id).status_code == 404
    assert rows(db_session) == []


def test_an_event_today_is_still_open(client, auth_cookies, csrf_token, db_session):
    event_id = create_event(client, csrf_token, date=bar_today()[1]).json()["id"]
    assert rsvp(client, event_id).status_code == 201
    assert len(rows(db_session)) == 1


def test_the_honeypot_stores_nothing(client, auth_cookies, csrf_token, db_session, event_id):
    resp = rsvp(client, event_id, website="http://spam.example")
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    assert rows(db_session) == []


def test_rsvps_are_rate_limited(client, auth_cookies, csrf_token, db_session, event_id, monkeypatch):
    from app.routers import rsvps

    monkeypatch.setattr(rsvps.settings, "RATE_LIMIT_ATTEMPTS", 2)
    assert rsvp(client, event_id, name="One").status_code == 201
    assert rsvp(client, event_id, name="Two").status_code == 201
    assert rsvp(client, event_id, name="Three").status_code == 429
    assert len(rows(db_session)) == 2


# --- Admin guest list ------------------------------------------------------


def test_the_guest_list_requires_a_session(client, db_session):
    event_id = add_event(db_session)
    rsvp(client, event_id)
    assert client.get("/api/rsvps").status_code == 401


def test_the_guest_list_counts_people_not_just_rows(
    client, auth_cookies, csrf_token, db_session, event_id
):
    rsvp(client, event_id, name="Ana", party_size=4)
    rsvp(client, event_id, name="Luis", party_size=3)

    data = client.get("/api/rsvps").json()
    assert data["total_rsvps"] == 2
    assert data["total_guests"] == 7
    assert [row["name"] for row in data["rsvps"]] == ["Luis", "Ana"]
    assert data["rsvps"][0]["event_title_en"] == "DJ Sol"
    assert data["rsvps"][0]["event_date"] == future()


def test_the_guest_list_can_be_filtered_to_one_event(
    client, auth_cookies, csrf_token, db_session
):
    first = create_event(client, csrf_token, title_en="First").json()["id"]
    second = create_event(client, csrf_token, title_en="Second").json()["id"]
    rsvp(client, first, name="Ana")
    rsvp(client, second, name="Luis")

    data = client.get(f"/api/rsvps?event_id={first}").json()
    assert [row["name"] for row in data["rsvps"]] == ["Ana"]
    assert data["total_guests"] == 2


def test_an_admin_can_delete_one_rsvp(
    client, auth_cookies, csrf_token, db_session, event_id
):
    rsvp(client, event_id)
    [row] = rows(db_session)

    resp = client.delete(
        f"/api/rsvps/{row.id}", headers={"X-CSRF-Token": csrf_token}
    )
    assert resp.status_code == 204
    assert rows(db_session) == []

    again = client.delete(
        f"/api/rsvps/{row.id}", headers={"X-CSRF-Token": csrf_token}
    )
    assert again.status_code == 404


def test_deleting_an_rsvp_needs_a_csrf_token(
    client, auth_cookies, csrf_token, db_session, event_id
):
    rsvp(client, event_id)
    [row] = rows(db_session)
    assert client.delete(f"/api/rsvps/{row.id}").status_code == 403
    assert len(rows(db_session)) == 1


def test_deleting_an_event_removes_its_guest_list(
    client, auth_cookies, csrf_token, db_session, event_id
):
    rsvp(client, event_id)
    assert len(rows(db_session)) == 1

    resp = client.delete(
        f"/api/special-events/{event_id}", headers={"X-CSRF-Token": csrf_token}
    )
    assert resp.status_code == 204
    assert events(db_session) == []
    assert rows(db_session) == []


# --- Admin page and dashboard ---------------------------------------------


def test_the_rsvps_page_needs_a_session(client):
    assert client.get("/admin/rsvps").status_code == 401


def test_the_rsvps_page_renders_for_an_admin(client, auth_cookies):
    body = client.get("/admin/rsvps").text
    assert "/api/rsvps" in body
    assert "/api/special-events/all" in body
    assert "rsvps_heading" in body


def test_the_dashboard_links_to_event_rsvps(client, auth_cookies):
    body = client.get("/admin").text
    assert 'href="/admin/rsvps"' in body
    assert "card_rsvps_title" in body
