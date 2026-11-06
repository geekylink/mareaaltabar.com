"""Tests for reservation requests (ticket #14).

A request is not a booking: the public write always lands as ``pending``, and the
admin queue is the only place its outcome changes. The date rules are pinned to
the bar's calendar, so the tests compute their dates from the same helper.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import Reservation
from app.schemas import RESERVATION_MAX_DAYS_AHEAD, RESERVATION_MAX_GUESTS
from app.ssr import bar_today


@pytest.fixture()
def edit_as_admin(client, auth_cookies, csrf_token):
    def _edit(method, url, **kwargs):
        return client.request(method, url, headers={"X-CSRF-Token": csrf_token}, **kwargs)

    return _edit


def today():
    return date.fromisoformat(bar_today()[1])


def request_booking(client, **over):
    payload = {
        "date": today().isoformat(),
        "time": "20:00",
        "party_size": 4,
        "name": "Guest",
        "contact": "+593 99 000 0000",
        "notes": "",
    }
    payload.update(over)
    return client.post("/api/reservations", json=payload)


def rows(db_session):
    return db_session.execute(select(Reservation)).scalars().all()


def test_a_request_is_stored_as_pending(client, db_session):
    resp = request_booking(client)
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}

    [row] = rows(db_session)
    assert row.status == "pending"
    assert row.date == today().isoformat()
    assert row.time == "20:00"
    assert row.party_size == 4
    assert row.name == "Guest"
    assert row.ip != ""


@pytest.mark.parametrize("field, value", [
    ("time", "8pm"),
    ("time", "25:00"),
    ("time", ""),
    ("party_size", 0),
    ("party_size", RESERVATION_MAX_GUESTS + 1),
    ("name", ""),
    ("contact", ""),
])
def test_invalid_requests_are_rejected(client, db_session, field, value):
    assert request_booking(client, **{field: value}).status_code == 422
    assert rows(db_session) == []


def test_a_past_date_is_rejected(client, db_session):
    yesterday = (today() - timedelta(days=1)).isoformat()
    assert request_booking(client, date=yesterday).status_code == 422
    assert rows(db_session) == []


def test_the_horizon_is_ninety_days(client, db_session):
    edge = (today() + timedelta(days=RESERVATION_MAX_DAYS_AHEAD)).isoformat()
    beyond = (today() + timedelta(days=RESERVATION_MAX_DAYS_AHEAD + 1)).isoformat()

    assert request_booking(client, date=edge).status_code == 201
    assert request_booking(client, date=beyond).status_code == 422
    assert len(rows(db_session)) == 1


def test_the_honeypot_stores_nothing(client, db_session):
    resp = request_booking(client, website="http://spam.example")
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    assert rows(db_session) == []


def test_requests_are_rate_limited(client, db_session, monkeypatch):
    from app.routers import reservations

    monkeypatch.setattr(reservations.settings, "RATE_LIMIT_ATTEMPTS", 2)
    assert request_booking(client, name="One").status_code == 201
    assert request_booking(client, name="Two").status_code == 201
    assert request_booking(client, name="Three").status_code == 429
    assert len(rows(db_session)) == 2


# --- Admin queue -----------------------------------------------------------


def test_the_queue_requires_a_session(client):
    assert client.get("/api/reservations").status_code == 401


def test_the_queue_reports_the_pending_count(client, edit_as_admin, db_session):
    request_booking(client, name="One")
    request_booking(client, name="Two")

    data = client.get("/api/reservations").json()
    assert data["pending"] == 2
    assert len(data["reservations"]) == 2

    first = rows(db_session)[0]
    edit_as_admin("PATCH", f"/api/reservations/{first.id}", json={"status": "confirmed"})
    assert client.get("/api/reservations").json()["pending"] == 1


@pytest.mark.parametrize("status", ["pending", "confirmed", "declined"])
def test_every_known_status_round_trips(client, edit_as_admin, db_session, status):
    request_booking(client)
    [row] = rows(db_session)
    resp = edit_as_admin("PATCH", f"/api/reservations/{row.id}", json={"status": status})
    assert resp.status_code == 200
    assert resp.json()["status"] == status


def test_an_unknown_status_is_rejected(client, edit_as_admin, db_session):
    request_booking(client)
    [row] = rows(db_session)
    resp = edit_as_admin("PATCH", f"/api/reservations/{row.id}", json={"status": "maybe"})
    assert resp.status_code == 422


def test_deleting_removes_the_request(client, edit_as_admin, db_session):
    request_booking(client)
    [row] = rows(db_session)
    assert edit_as_admin("DELETE", f"/api/reservations/{row.id}").status_code == 204
    assert rows(db_session) == []


def test_a_write_needs_a_csrf_token(client, auth_cookies, db_session):
    request_booking(client)
    [row] = rows(db_session)
    resp = client.patch(f"/api/reservations/{row.id}", json={"status": "confirmed"})
    assert resp.status_code == 403


# --- Admin page and dashboard ---------------------------------------------


def test_the_reservations_page_needs_a_session(client):
    assert client.get("/admin/reservations").status_code == 401


def test_the_reservations_page_renders_for_an_admin(client, auth_cookies):
    body = client.get("/admin/reservations").text
    assert "/api/reservations" in body
    assert "data-filter=\"pending\"" in body
    assert "reservations_heading" in body


def test_the_dashboard_links_to_reservations_and_counts_pending(
    client, auth_cookies, db_session
):
    request_booking(client)
    body = client.get("/admin").text
    assert 'href="/admin/reservations"' in body
    assert '1 <span data-i18n="reservation_pending">' in body
