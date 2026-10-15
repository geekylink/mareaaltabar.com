"""Tests for the bilingual weekly schedule API."""

import pytest


def test_schedule_is_public(client):
    """The website reads this with no session."""
    resp = client.get("/api/schedule")
    assert resp.status_code == 200


def test_schedule_returns_all_seven_days(client):
    resp = client.get("/api/schedule")
    assert resp.status_code == 200
    schedule = resp.json()
    assert len(schedule) == 7
    assert [d["day"] for d in schedule] == list(range(7))


def test_schedule_includes_both_languages(client):
    schedule = client.get("/api/schedule").json()
    monday = schedule[1]
    for field in ("title_en", "title_es", "note_en", "note_es"):
        assert field in monday, field
    assert monday["title_en"] == "Singles Night"
    assert monday["title_es"] == "Noche de Solteros"


def test_schedule_includes_hours(client):
    """Hours are merged into the same resource, so the panel edits them in one place."""
    schedule = client.get("/api/schedule").json()
    monday = schedule[1]
    assert monday["open_time"] == "16:00"
    assert monday["close_time"] == "04:00"
    assert monday["is_closed"] is False


def test_schedule_reports_closed_days(client):
    schedule = client.get("/api/schedule").json()
    assert schedule[2]["is_closed"] is True


def test_update_day_requires_auth(client):
    resp = client.put(
        "/api/schedule/0",
        json={"title_en": "Hack", "title_es": "", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": False},
        headers={"X-CSRF-Token": "forged"},
    )
    assert resp.status_code == 401


def test_update_day_requires_csrf(client, auth_cookies):
    resp = client.put(
        "/api/schedule/0",
        json={"title_en": "Test", "title_es": "", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": False},
    )
    assert resp.status_code == 403


def test_update_day_saves_both_languages_and_hours(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/schedule/5",
        json={
            "title_en": "Reggae Night",
            "title_es": "Noche de Reggae",
            "note_en": "Roots and dub all night.",
            "note_es": "Roots y dub toda la noche.",
            "open_time": "18:00",
            "close_time": "03:00",
            "is_closed": False,
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title_en"] == "Reggae Night"
    assert data["title_es"] == "Noche de Reggae"
    assert data["note_es"] == "Roots y dub toda la noche."
    assert data["open_time"] == "18:00"
    assert data["close_time"] == "03:00"


def test_update_day_invalid_day(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/schedule/7",
        json={"title_en": "x", "title_es": "", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": False},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 400


def test_update_day_rejects_oversized_title(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/schedule/0",
        json={"title_en": "x" * 300, "title_es": "", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": False},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 422


def test_blank_translation_is_stored_as_blank(client, auth_cookies, csrf_token):
    """The admin's input is preserved verbatim; fallback happens on render."""
    client.put(
        "/api/schedule/0",
        json={"title_en": "Only English", "title_es": "", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": False},
        headers={"X-CSRF-Token": csrf_token},
    )
    sunday = next(d for d in client.get("/api/schedule").json() if d["day"] == 0)
    assert sunday["title_en"] == "Only English"
    assert sunday["title_es"] == ""


def test_marking_a_day_closed_disables_its_hours(client, auth_cookies, csrf_token):
    client.put(
        "/api/schedule/1",
        json={"title_en": "Closed", "title_es": "Cerrado", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": True},
        headers={"X-CSRF-Token": csrf_token},
    )
    monday = next(d for d in client.get("/api/schedule").json() if d["day"] == 1)
    assert monday["is_closed"] is True