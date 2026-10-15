"""Tests for the hours API endpoints."""


def test_list_hours_is_public(client):
    """The website reads this without a session, so it must not require auth."""
    resp = client.get("/api/hours")
    assert resp.status_code == 200


def test_list_hours(client):
    resp = client.get("/api/hours")
    assert resp.status_code == 200
    hours = resp.json()
    assert len(hours) == 7
    days = [h["day"] for h in hours]
    assert days == list(range(7))


def test_update_hours_requires_auth(client):
    """Writes must stay locked down."""
    resp = client.put(
        "/api/hours/0",
        json={"open_time": "10:00", "close_time": "02:00", "is_closed": False},
        headers={"X-CSRF-Token": "forged-token"},
    )
    assert resp.status_code == 401


def test_update_hours(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/hours/0",
        json={"open_time": "10:00", "close_time": "02:00", "is_closed": False},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["open_time"] == "10:00"
    assert data["close_time"] == "02:00"
    assert data["is_closed"] is False


def test_update_hours_set_closed(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/hours/2",
        json={"open_time": "", "close_time": "", "is_closed": True},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_closed"] is True


def test_update_hours_requires_csrf(client, auth_cookies):
    resp = client.put(
        "/api/hours/0",
        json={"open_time": "10:00", "close_time": "02:00", "is_closed": False},
    )
    assert resp.status_code == 403


def test_update_hours_invalid_day(client, auth_cookies, csrf_token):
    resp = client.put(
        "/api/hours/7",
        json={"open_time": "10:00", "close_time": "02:00", "is_closed": False},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 400
