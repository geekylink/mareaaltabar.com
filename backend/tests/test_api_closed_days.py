"""Tests for the closed-days API endpoints."""


def test_list_closed_days_is_public(client):
    """The website reads this without a session, so it must not require auth."""
    resp = client.get("/api/closed-days")
    assert resp.status_code == 200


def test_list_closed_days_empty(client):
    resp = client.get("/api/closed-days")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_closed_day_requires_auth(client):
    """Writes must stay locked down."""
    resp = client.post(
        "/api/closed-days",
        json={"date": "2099-01-01", "reason": "Nope"},
        headers={"X-CSRF-Token": "forged-token"},
    )
    assert resp.status_code == 401


def test_create_closed_day(client, auth_cookies, csrf_token):
    resp = client.post(
        "/api/closed-days",
        json={"date": "2026-12-25", "reason": "Christmas"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["date"] == "2026-12-25"
    assert data["reason"] == "Christmas"
    assert "id" in data


def test_create_closed_day_duplicate(client, auth_cookies, csrf_token):
    payload = {"date": "2026-12-25", "reason": "Christmas"}
    # First creation
    client.post(
        "/api/closed-days",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
    )
    # Duplicate should fail
    resp = client.post(
        "/api/closed-days",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 409


def test_create_closed_day_requires_csrf(client, auth_cookies):
    resp = client.post(
        "/api/closed-days",
        json={"date": "2026-12-25", "reason": "Christmas"},
    )
    assert resp.status_code == 403


def test_delete_closed_day(client, auth_cookies, csrf_token):
    # Create one first
    resp = client.post(
        "/api/closed-days",
        json={"date": "2026-12-25", "reason": "Christmas"},
        headers={"X-CSRF-Token": csrf_token},
    )
    day_id = resp.json()["id"]

    # Delete it
    resp = client.delete(
        f"/api/closed-days/{day_id}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 204

    # Verify it's gone
    resp = client.get("/api/closed-days")
    assert resp.json() == []


def test_delete_closed_day_not_found(client, auth_cookies, csrf_token):
    resp = client.delete(
        "/api/closed-days/9999",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 404


def test_create_closed_day_invalid_date_format(client, auth_cookies, csrf_token):
    """A non-ISO date must be rejected with a 422."""
    resp = client.post(
        "/api/closed-days",
        json={"date": "25-12-2026", "reason": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 422


def test_create_closed_day_rejects_past_date(client, auth_cookies, csrf_token):
    """Past dates are a data-entry mistake and should be rejected."""
    resp = client.post(
        "/api/closed-days",
        json={"date": "2020-01-01", "reason": "long gone"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 422
