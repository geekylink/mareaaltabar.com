"""Tests for dated / special events (#53).

The weekly schedule is a repeating pattern; this table is the exception to it.
The parts most likely to rot are the split between the public and admin reads
(past and hidden rows must stay editable but never publish), the bar-clock date
comparison, and the SSR block: a crawler has to see the same one-off party a
visitor does.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import AuditEntry, SpecialEvent
from app.ssr import bar_today, build_payload, load_special_events


def future(days=30):
    return (date.fromisoformat(bar_today()[1]) + timedelta(days=days)).isoformat()


def past(days=30):
    return (date.fromisoformat(bar_today()[1]) - timedelta(days=days)).isoformat()


VALID = {
    "date": future(),
    "title_en": "DJ Sol",
    "title_es": "DJ Sol",
    "description_en": "Guest set on the terrace.",
    "description_es": "Sesión invitada en la terraza.",
    "start_time": "21:00",
    "end_time": "02:00",
    "image_url": "https://example.com/sol.jpg",
    "is_active": True,
}


def write_headers(csrf_token):
    return {"X-CSRF-Token": csrf_token}


def create(client, csrf_token, **over):
    return client.post(
        "/api/special-events",
        json={**VALID, **over},
        headers=write_headers(csrf_token),
    )


def public_events(client):
    return client.get("/api/special-events").json()


def admin_events(client):
    return client.get("/api/special-events/all").json()


def rows(db_session):
    return list(db_session.execute(select(SpecialEvent)).scalars().all())


# --- Public and admin reads ------------------------------------------------


def test_the_public_read_is_empty_before_anything_is_added(client):
    assert public_events(client) == []


def test_an_admin_can_add_a_dated_event(client, db_session, auth_cookies, csrf_token):
    resp = create(client, csrf_token)
    assert resp.status_code == 201
    body = resp.json()
    assert body["date"] == VALID["date"]
    assert body["title_en"] == "DJ Sol"
    assert body["start_time"] == "21:00"
    assert body["is_past"] is False

    stored = rows(db_session)
    assert len(stored) == 1
    assert stored[0].image_url == "https://example.com/sol.jpg"

    published = public_events(client)
    assert [event["title_en"] for event in published] == ["DJ Sol"]


def test_a_switched_off_event_stays_editable_but_does_not_publish(
    client, auth_cookies, csrf_token
):
    event_id = create(client, csrf_token, is_active=False).json()["id"]

    assert public_events(client) == []
    admin = admin_events(client)
    assert [event["id"] for event in admin] == [event_id]
    assert admin[0]["is_active"] is False


def test_a_past_event_is_hidden_publicly_but_kept_for_the_panel(
    client, auth_cookies, csrf_token, db_session
):
    event = SpecialEvent(date=past(), title_en="Old party", title_es="Fiesta vieja")
    db_session.add(event)
    db_session.commit()

    assert public_events(client) == []
    admin = admin_events(client)
    assert [(row["title_en"], row["is_past"]) for row in admin] == [("Old party", True)]


def test_the_public_read_is_soonest_first(client, auth_cookies, csrf_token):
    later = future(60)
    sooner = future(10)
    create(client, csrf_token, date=later, title_en="Later")
    create(client, csrf_token, date=sooner, title_en="Sooner")

    assert [event["title_en"] for event in public_events(client)] == ["Sooner", "Later"]


def test_the_admin_read_needs_a_session(client):
    assert client.get("/api/special-events/all").status_code == 401


# --- Writes and validation -------------------------------------------------


def test_an_admin_can_edit_an_event(client, auth_cookies, csrf_token):
    event_id = create(client, csrf_token).json()["id"]
    moved = future(45)

    resp = client.put(
        f"/api/special-events/{event_id}",
        json={
            **VALID,
            "date": moved,
            "title_en": "DJ Sol (moved)",
            "start_time": "",
            "end_time": "",
            "is_active": False,
        },
        headers=write_headers(csrf_token),
    )
    assert resp.status_code == 200
    assert resp.json()["date"] == moved
    assert resp.json()["title_en"] == "DJ Sol (moved)"
    assert resp.json()["start_time"] == ""
    assert resp.json()["is_active"] is False


def test_an_admin_can_delete_an_event(client, auth_cookies, csrf_token):
    event_id = create(client, csrf_token).json()["id"]

    resp = client.delete(
        f"/api/special-events/{event_id}", headers=write_headers(csrf_token)
    )
    assert resp.status_code == 204
    assert public_events(client) == []

    again = client.delete(
        f"/api/special-events/{event_id}", headers=write_headers(csrf_token)
    )
    assert again.status_code == 404


def test_admin_writes_need_a_session(client):
    # A write without a session is rejected before CSRF is even considered.
    assert client.post("/api/special-events", json=VALID).status_code == 401


def test_a_write_without_the_csrf_token_is_rejected(client, auth_cookies):
    assert client.post("/api/special-events", json=VALID).status_code == 403


def test_creating_an_event_is_logged(client, auth_cookies, csrf_token, db_session):
    event_id = create(client, csrf_token).json()["id"]
    entries = db_session.execute(select(AuditEntry)).scalars().all()
    assert len(entries) == 1
    assert entries[0].target == f"special_event:{event_id}"
    assert entries[0].area == "schedule"
    assert entries[0].details["title_en"] == "DJ Sol"


def test_a_past_date_is_rejected_on_create(client, auth_cookies, csrf_token):
    resp = create(client, csrf_token, date=past())
    assert resp.status_code == 422


def test_an_existing_past_event_can_still_be_edited(client, auth_cookies, csrf_token, db_session):
    event = SpecialEvent(date=past(), title_en="Old", title_es="Vieja")
    db_session.add(event)
    db_session.commit()

    resp = client.put(
        f"/api/special-events/{event.id}",
        json={**VALID, "date": past(), "title_en": "Old (fixed)"},
        headers=write_headers(csrf_token),
    )
    assert resp.status_code == 200
    assert resp.json()["title_en"] == "Old (fixed)"


@pytest.mark.parametrize("over", [
    {"title_en": "", "title_es": ""},
    {"start_time": "21:00", "end_time": ""},
    {"start_time": "", "end_time": "02:00"},
    {"start_time": "21:00", "end_time": "21:00"},
    {"start_time": "25:00", "end_time": "26:00"},
    {"image_url": "javascript:alert(1)"},
    {"image_url": "ftp://example.com/photo.jpg"},
])
def test_invalid_events_are_rejected(client, auth_cookies, csrf_token, over):
    assert create(client, csrf_token, **over).status_code == 422


def test_an_overnight_window_is_allowed(client, auth_cookies, csrf_token):
    resp = create(client, csrf_token, start_time="22:00", end_time="03:00")
    assert resp.status_code == 201


def test_a_site_relative_image_is_allowed(client, auth_cookies, csrf_token):
    resp = create(client, csrf_token, image_url="/icons/favicon.svg")
    assert resp.status_code == 201


# --- Loader and SSR --------------------------------------------------------


def test_the_loader_filters_past_and_hidden_rows(db_session):
    db_session.add_all([
        SpecialEvent(date=future(1), title_en="Public", title_es="Público"),
        SpecialEvent(date=future(2), title_en="Hidden", title_es="Oculto", is_active=False),
        SpecialEvent(date=past(1), title_en="Past", title_es="Pasado"),
    ])
    db_session.commit()

    assert [event["title_en"] for event in load_special_events(db_session)] == ["Public"]
    assert {event["title_en"] for event in load_special_events(
        db_session, include_past=True, include_inactive=True
    )} == {"Public", "Hidden", "Past"}


def test_the_ssr_block_renders_upcoming_events(db_session):
    db_session.add(
        SpecialEvent(
            date=future(5),
            title_en="Beach party",
            title_es="Fiesta en la playa",
            description_en="Bonfire at sunset.",
            description_es="Fogata al atardecer.",
            start_time="18:00",
            end_time="23:00",
        )
    )
    db_session.commit()

    payload = build_payload(db_session, "en")
    assert payload["special_events"][0]["title"] == "Beach party"
    assert payload["special_events"][0]["time"] == "6:00 PM - 11:00 PM"
    assert payload["seed"]["specialEvents"][0]["title_en"] == "Beach party"


def test_the_homepage_renders_a_special_event(client, auth_cookies, csrf_token):
    create(client, csrf_token, title_en="Beach party")

    html = client.get("/").text
    assert "Special events" in html
    assert "Beach party" in html


def test_the_homepage_does_not_render_a_hidden_event(client, auth_cookies, csrf_token):
    create(client, csrf_token, title_en="Secret party", is_active=False)

    assert "Secret party" not in client.get("/").text


# --- The admin page --------------------------------------------------------


def test_the_events_page_needs_a_session(client):
    assert client.get("/admin/events").status_code == 401


def test_the_events_page_renders_for_an_admin(client, auth_cookies):
    body = client.get("/admin/events").text
    assert "/api/special-events/all" in body
    assert "events_heading" in body
    assert "/admin/static/admin_i18n.js" in body


def test_the_dashboard_links_to_the_events_page(client, auth_cookies):
    body = client.get("/admin").text
    assert 'href="/admin/events"' in body
    assert "card_events_title" in body
