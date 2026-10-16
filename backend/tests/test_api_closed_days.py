"""Tests for the bilingual closed-days API."""

import pytest

from app.models import ClosedDay
from app.ssr import bar_today


def add_closed_day(db, iso_date: str, reason_en: str = "Holiday", reason_es: str = "Feriado"):
    """Insert a closure straight into the database.

    `POST` refuses past dates, which is the point of the filter: the only way to
    get a row that has already passed is to write it directly, which is exactly
    what an old database full of closures looks like.
    """
    db.add(ClosedDay(date=iso_date, reason_en=reason_en, reason_es=reason_es))
    db.commit()
    return iso_date


def test_list_closed_days_is_public(client):
    resp = client.get("/api/closed-days")
    assert resp.status_code == 200


def test_list_closed_days_empty(client):
    assert client.get("/api/closed-days").json() == []


def test_list_omits_closures_that_have_passed(client, db_session):
    """A closure is only news on its own date — otherwise it renders for ever."""
    add_closed_day(db_session, "2001-12-25", "New Year", "Año Nuevo")
    assert client.get("/api/closed-days").json() == []


def test_list_keeps_a_closure_dated_today(client, db_session):
    """Today is included: it is the one date that must reach the frontend."""
    today = add_closed_day(db_session, bar_today()[1])
    assert [d["date"] for d in client.get("/api/closed-days").json()] == [today]


def test_list_keeps_future_closures_in_date_order(client, db_session):
    add_closed_day(db_session, "2099-12-25", "Christmas", "Navidad")
    add_closed_day(db_session, bar_today()[1], "Today", "Hoy")
    add_closed_day(db_session, "2001-12-25", "New Year", "Año Nuevo")
    add_closed_day(db_session, "2099-07-04", "Holiday", "Feriado")

    dates = [d["date"] for d in client.get("/api/closed-days").json()]

    assert set(dates) == {"2099-07-04", "2099-12-25", bar_today()[1]}
    assert dates == sorted(dates)


def test_list_reads_the_bar_clock_not_the_server_clock(client, db_session, monkeypatch):
    """The filter and the creation guard must ask the bar, not the server.

    The clock is pinned to a date well in the past: if either side fell back to
    `date.today()`, the guard would reject the closure and the filter would hide
    it. Both modules import `bar_today` by name, so each is patched where it is
    used — and to the same value, which is the real invariant: one clock decides
    what can be created and what gets published.
    """
    pinned = (3, "2019-07-04")
    monkeypatch.setattr("app.ssr.bar_today", lambda: pinned)
    monkeypatch.setattr("app.schemas.bar_today", lambda: pinned)

    assert client.get("/api/closed-days").status_code == 200

    add_closed_day(db_session, "2019-07-04", "Holiday", "Feriado")
    assert [d["date"] for d in client.get("/api/closed-days").json()] == ["2019-07-04"]


def test_create_accepts_the_bars_own_today(client, auth_cookies, csrf_token):
    """The guard accepts the bar's today, and the API publishes it."""
    today = bar_today()[1]
    resp = client.post(
        "/api/closed-days",
        json={"date": today, "reason_en": "Holiday", "reason_es": "Feriado"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 201
    assert [d["date"] for d in client.get("/api/closed-days").json()] == [today]


def test_create_requires_auth(client):
    resp = client.post(
        "/api/closed-days",
        json={"date": "2099-01-01", "reason_en": "Nope", "reason_es": "No"},
        headers={"X-CSRF-Token": "forged"},
    )
    assert resp.status_code == 401


def test_create_requires_csrf(client, auth_cookies):
    resp = client.post(
        "/api/closed-days",
        json={"date": "2099-01-01", "reason_en": "Nope", "reason_es": "No"},
    )
    assert resp.status_code == 403


def test_create_with_bilingual_reason(client, auth_cookies, csrf_token):
    resp = client.post(
        "/api/closed-days",
        json={"date": "2099-12-25", "reason_en": "Christmas", "reason_es": "Navidad"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["date"] == "2099-12-25"
    assert data["reason_en"] == "Christmas"
    assert data["reason_es"] == "Navidad"


def test_create_duplicate_date_conflicts(client, auth_cookies, csrf_token):
    payload = {"date": "2099-12-25", "reason_en": "Christmas", "reason_es": "Navidad"}
    client.post("/api/closed-days", json=payload, headers={"X-CSRF-Token": csrf_token})
    resp = client.post("/api/closed-days", json=payload, headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 409


def test_create_rejects_past_date(client, auth_cookies, csrf_token):
    resp = client.post(
        "/api/closed-days",
        json={"date": "2020-01-01", "reason_en": "gone", "reason_es": "pasado"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 422


def test_create_rejects_malformed_date(client, auth_cookies, csrf_token):
    resp = client.post(
        "/api/closed-days",
        json={"date": "25-12-2099", "reason_en": "", "reason_es": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 422


def test_patch_updates_translations(client, auth_cookies, csrf_token):
    created = client.post(
        "/api/closed-days",
        json={"date": "2099-07-04", "reason_en": "Holiday", "reason_es": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    day_id = created.json()["id"]

    resp = client.patch(
        f"/api/closed-days/{day_id}",
        json={"reason_en": "Private event", "reason_es": "Evento privado"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 200
    assert resp.json()["reason_en"] == "Private event"
    assert resp.json()["reason_es"] == "Evento privado"


def test_patch_requires_csrf(client, auth_cookies, csrf_token):
    created = client.post(
        "/api/closed-days",
        json={"date": "2099-07-05", "reason_en": "A", "reason_es": "B"},
        headers={"X-CSRF-Token": csrf_token},
    )
    resp = client.patch(
        f"/api/closed-days/{created.json()['id']}",
        json={"reason_en": "C", "reason_es": "D"},
    )
    assert resp.status_code == 403


def test_patch_missing_day_is_404(client, auth_cookies, csrf_token):
    resp = client.patch(
        "/api/closed-days/9999",
        json={"reason_en": "x", "reason_es": "y"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 404


def test_delete_removes_the_day(client, auth_cookies, csrf_token):
    created = client.post(
        "/api/closed-days",
        json={"date": "2099-08-08", "reason_en": "Gone", "reason_es": "Ido"},
        headers={"X-CSRF-Token": csrf_token},
    )
    day_id = created.json()["id"]
    assert client.get("/api/closed-days").json()

    resp = client.delete(f"/api/closed-days/{day_id}", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 204
    assert client.get("/api/closed-days").json() == []


def test_delete_missing_day_is_404(client, auth_cookies, csrf_token):
    resp = client.delete("/api/closed-days/9999", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 404


def test_delete_requires_csrf(client, auth_cookies, csrf_token):
    created = client.post(
        "/api/closed-days",
        json={"date": "2099-09-09", "reason_en": "A", "reason_es": "B"},
        headers={"X-CSRF-Token": csrf_token},
    )
    resp = client.delete(f"/api/closed-days/{created.json()['id']}")
    assert resp.status_code == 403