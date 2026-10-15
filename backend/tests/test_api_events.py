"""Tests for the events API endpoints."""


def test_list_events_is_public(client):
    """The website reads this without a session, so it must not require auth."""
    resp = client.get("/api/events")
    assert resp.status_code == 200


def test_list_events(client):
    resp = client.get("/api/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 7
    days = [e["day"] for e in events]
    assert days == list(range(7))


def test_update_event(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/events/0",
        json={"title": "Test Event", "note": "Test note", "time": "9 PM - 3 AM"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Event"
    assert data["note"] == "Test note"
    assert data["time"] == "9 PM - 3 AM"


def test_update_event_requires_auth(client):
    """Writes must stay locked down even if a CSRF header is supplied."""
    resp = client.put(
        "/api/events/0",
        json={"title": "Hack", "note": "", "time": ""},
        headers={"X-CSRF-Token": "forged-token"},
    )
    assert resp.status_code == 401


def test_update_event_requires_csrf(client, auth_cookies):
    resp = client.put(
        "/api/events/0",
        json={"title": "Test", "note": "", "time": ""},
    )
    assert resp.status_code == 403


def test_update_event_invalid_day(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/events/7",
        json={"title": "Test", "note": "", "time": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 400


def test_update_event_day_not_found(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/events/99",
        json={"title": "Test", "note": "", "time": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code in (400, 404)


def test_update_event_too_long_title(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/events/0",
        json={"title": "x" * 300, "note": "", "time": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 422


def test_update_event_empty_strings_allowed(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/events/0",
        json={"title": "", "note": "", "time": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == ""
    assert data["note"] == ""
    assert data["time"] == ""
