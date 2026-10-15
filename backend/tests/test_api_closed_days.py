"""Tests for the bilingual closed-days API."""

import pytest


def test_list_closed_days_is_public(client):
    resp = client.get("/api/closed-days")
    assert resp.status_code == 200


def test_list_closed_days_empty(client):
    assert client.get("/api/closed-days").json() == []


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