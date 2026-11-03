"""Tests for the emergency notice banner (ticket #52).

The banner is the owner's only way to tell visitors something urgent without a
deploy, so the parts that matter are the ones that decide *whether* it is shown:
the live window, the on/off switch, and the split between the public read and the
admin read. The server-rendered copy matters too — a crawler, or a visitor with
JavaScript off, must see the closure.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app import main as main_module
from app.models import AuditEntry, Notice
from app.ssr import bar_now, build_payload, load_notices

BUILT_INDEX = (
    "<!doctype html>\n<html lang=\"en\">\n  <head>\n    <title>Marea Alta</title>\n"
    "  </head>\n  <body>\n    <div id=\"app\"></div>\n"
    "    <script type=\"module\" crossorigin src=\"/assets/index-abc.js\"></script>\n"
    "  </body>\n</html>\n"
)

BUILT_MENU = (
    "<!doctype html>\n<html lang=\"en\">\n  <head>\n    <title>Menu</title>\n"
    "  </head>\n  <body>\n    <div id=\"app\"></div>\n"
    "    <script type=\"module\" crossorigin src=\"/assets/menu-xyz.js\"></script>\n"
    "  </body>\n</html>\n"
)


@pytest.fixture()
def site(client, monkeypatch, tmp_path):
    """The test client with both built documents in place."""
    index = tmp_path / "index.html"
    index.write_text(BUILT_INDEX, encoding="utf-8")
    menu = tmp_path / "menu.html"
    menu.write_text(BUILT_MENU, encoding="utf-8")
    monkeypatch.setattr(main_module, "INDEX_HTML", index)
    monkeypatch.setattr(main_module, "MENU_HTML", menu)
    return client


@pytest.fixture()
def edit_as_admin(client, auth_cookies, csrf_token):
    def _edit(method, url, **kwargs):
        return client.request(method, url, headers={"X-CSRF-Token": csrf_token}, **kwargs)

    return _edit


def notice_payload(**overrides):
    data = {
        "message_en": "Closed tonight because of the storm.",
        "message_es": "Cerrado esta noche por la tormenta.",
        "severity": "warning",
        "starts_at": "",
        "ends_at": "",
        "is_active": True,
    }
    data.update(overrides)
    return data


def add_notice(db_session, **overrides):
    data = {
        "message_en": "Notice",
        "message_es": "",
        "severity": "info",
        "starts_at": "",
        "ends_at": "",
        "is_active": True,
    }
    data.update(overrides)
    notice = Notice(**data)
    db_session.add(notice)
    db_session.commit()
    db_session.refresh(notice)
    return notice


# --- The bar clock ---------------------------------------------------------


def test_bar_now_is_bar_local_time():
    """15:00 UTC is 10:00 in Montañita, and the format matches the input."""
    assert bar_now(datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)) == "2026-11-03T10:00"


def test_bar_now_treats_naive_timestamps_as_utc():
    assert bar_now(datetime(2026, 11, 3, 15, 0)) == "2026-11-03T10:00"


# --- The live window -------------------------------------------------------


def test_load_notices_keeps_only_live_rows_by_default(db_session):
    now = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)  # 10:00 at the bar
    add_notice(db_session, message_en="open-ended")
    add_notice(db_session, message_en="inside", starts_at="2026-11-03T09:00",
               ends_at="2026-11-03T11:00")
    add_notice(db_session, message_en="future", starts_at="2026-11-03T11:00")
    add_notice(db_session, message_en="past", ends_at="2026-11-03T09:00")
    add_notice(db_session, message_en="switched off", is_active=False)

    names = [n["message_en"] for n in load_notices(db_session, now=now)]
    assert set(names) == {"open-ended", "inside"}
    assert all(n["is_live"] for n in load_notices(db_session, now=now))


def test_load_notices_can_include_everything_for_the_panel(db_session):
    now = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)
    add_notice(db_session, message_en="future", starts_at="2026-11-03T11:00")
    add_notice(db_session, message_en="off", is_active=False)

    rows = load_notices(db_session, include_inactive=True, now=now)
    by_name = {row["message_en"]: row for row in rows}
    assert set(by_name) == {"future", "off"}
    assert by_name["future"]["is_live"] is False
    assert by_name["off"]["is_live"] is False


def test_a_blank_start_means_now_and_a_blank_end_means_until_switched_off(db_session):
    notice = add_notice(db_session, message_en="always on")
    assert load_notices(db_session)[0]["id"] == notice.id


# --- The public and admin reads --------------------------------------------


def test_public_read_is_empty_until_something_is_published(client):
    resp = client.get("/api/notices")
    assert resp.status_code == 200
    assert resp.json() == []
    assert resp.headers["cache-control"] == "no-cache"


def test_public_read_hides_switched_off_and_expired_notices(client, db_session):
    live = add_notice(db_session, message_en="live", ends_at="2999-01-01T00:00")
    add_notice(db_session, message_en="off", is_active=False)
    add_notice(db_session, message_en="expired", ends_at="2000-01-01T00:00")
    add_notice(db_session, message_en="scheduled", starts_at="2999-01-01T00:00")

    body = client.get("/api/notices").json()
    assert [n["id"] for n in body] == [live.id]
    assert body[0]["message_en"] == "live"


def test_admin_read_requires_a_session(client):
    assert client.get("/api/notices/all").status_code == 401


def test_admin_read_returns_paused_and_scheduled_notices(client, auth_cookies, db_session):
    off = add_notice(db_session, message_en="off", is_active=False)
    future = add_notice(db_session, message_en="future", starts_at="2999-01-01T00:00")

    body = client.get("/api/notices/all").json()
    ids = {n["id"] for n in body}
    assert ids == {off.id, future.id}
    assert all(n["is_live"] is False for n in body)


# --- Writes ----------------------------------------------------------------


def test_create_requires_authentication(client):
    assert client.post("/api/notices", json=notice_payload()).status_code == 401


def test_create_requires_csrf(client, auth_cookies):
    assert client.post("/api/notices", json=notice_payload()).status_code == 403


def test_create_and_read_back_a_notice(client, edit_as_admin):
    resp = edit_as_admin("POST", "/api/notices", json=notice_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["message_en"] == "Closed tonight because of the storm."
    assert body["severity"] == "warning"
    assert body["is_active"] is True
    assert body["is_live"] is True

    public = client.get("/api/notices").json()
    assert [n["id"] for n in public] == [body["id"]]


def test_update_can_switch_a_notice_off_and_on(client, edit_as_admin):
    created = edit_as_admin("POST", "/api/notices", json=notice_payload()).json()

    off = edit_as_admin(
        "PUT", f"/api/notices/{created['id']}",
        json=notice_payload(is_active=False),
    )
    assert off.status_code == 200
    assert off.json()["is_live"] is False
    assert client.get("/api/notices").json() == []

    on = edit_as_admin(
        "PUT", f"/api/notices/{created['id']}",
        json=notice_payload(is_active=True),
    )
    assert on.json()["is_live"] is True
    assert len(client.get("/api/notices").json()) == 1


def test_update_unknown_notice_is_404(client, edit_as_admin):
    resp = edit_as_admin("PUT", "/api/notices/999", json=notice_payload())
    assert resp.status_code == 404


def test_delete_removes_the_notice(client, edit_as_admin):
    created = edit_as_admin("POST", "/api/notices", json=notice_payload()).json()

    assert edit_as_admin("DELETE", f"/api/notices/{created['id']}").status_code == 204
    assert client.get("/api/notices").json() == []
    assert edit_as_admin("DELETE", f"/api/notices/{created['id']}").status_code == 404


# --- Validation ------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"message_en": "", "message_es": ""},
        {"severity": "spicy"},
        {"starts_at": "2026-11-03 10:00"},
        {"starts_at": "not-a-date"},
        {"starts_at": "2026-11-03T11:00", "ends_at": "2026-11-03T10:00"},
        {"starts_at": "2026-11-03T11:00", "ends_at": "2026-11-03T11:00"},
    ],
)
def test_invalid_notices_are_refused(client, edit_as_admin, overrides):
    resp = edit_as_admin("POST", "/api/notices", json=notice_payload(**overrides))
    assert resp.status_code == 422


def test_spanish_only_notice_is_allowed(client, edit_as_admin):
    resp = edit_as_admin(
        "POST", "/api/notices",
        json=notice_payload(message_en="", message_es="Cerrado por la tormenta."),
    )
    assert resp.status_code == 201
    assert resp.json()["message_es"] == "Cerrado por la tormenta."


# --- Audit -----------------------------------------------------------------


def test_a_notice_write_is_logged_in_the_schedule_log(client, edit_as_admin):
    created = edit_as_admin("POST", "/api/notices", json=notice_payload()).json()

    entries = client.get("/api/logs/schedule").json()["entries"]
    assert entries[0]["target"] == f"notice:{created['id']}"
    assert entries[0]["target_name"] == "Closed tonight because of the storm."
    assert entries[0]["action"] == "create"
    assert entries[0]["area"] == "schedule"

    edit_as_admin(
        "PUT", f"/api/notices/{created['id']}",
        json=notice_payload(is_active=False),
    )
    entries = client.get("/api/logs/schedule").json()["entries"]
    assert entries[0]["target"] == f"notice:{created['id']}"
    assert entries[0]["details"]["is_active"] == {"from": True, "to": False}

    edit_as_admin("DELETE", f"/api/notices/{created['id']}")
    entries = client.get("/api/logs/schedule").json()["entries"]
    assert entries[0]["action"] == "delete"


def test_a_notice_and_its_log_row_commit_together(client, db_session, edit_as_admin):
    edit_as_admin("POST", "/api/notices", json=notice_payload())
    assert db_session.execute(select(Notice)).scalar_one()
    assert db_session.execute(select(AuditEntry)).scalar_one()


# --- Server-rendered copy ---------------------------------------------------


def test_the_homepage_renders_a_live_notice_for_a_crawler(site, db_session):
    add_notice(db_session, message_en="Closed tonight for a private party.")

    html = site.get("/").text
    assert "Closed tonight for a private party." in html
    assert 'id="marea-notices"' in html


def test_the_menu_page_renders_the_notice_too(site, db_session):
    add_notice(db_session, message_en="Kitchen closed, drinks still cold.")

    assert "Kitchen closed, drinks still cold." in site.get("/menu").text


def test_the_notice_is_rendered_in_the_requested_language(site, db_session):
    add_notice(
        db_session,
        message_en="Closed tonight.",
        message_es="Cerrado esta noche.",
    )

    html = site.get("/?lang=es").text
    block = html.split('<div id="marea-notices">', 1)[1].split('</div>', 1)[0]
    assert "Cerrado esta noche." in block
    assert "Closed tonight." not in block


def test_a_hidden_notice_is_not_rendered(site, db_session):
    add_notice(db_session, message_en="Do not show this", is_active=False)

    html = site.get("/").text
    assert "Do not show this" not in html
    assert 'id="marea-notices"' not in html


def test_notice_markup_is_escaped(site, db_session):
    add_notice(db_session, message_en="<script>alert('xss')</script>")

    html = site.get("/").text
    assert "<script>alert('xss')</script>" not in html
    assert "&lt;script&gt;" in html


def test_the_seed_carries_both_languages(db_session):
    add_notice(db_session, message_en="Closed", message_es="Cerrado")

    payload = build_payload(db_session, "en")
    assert payload["seed"]["notices"][0]["message_es"] == "Cerrado"
    # The rendered block is resolved for one language.
    assert payload["notices"][0]["message"] == "Closed"


# --- Admin page ------------------------------------------------------------


def test_the_notice_admin_page_requires_a_session(client):
    assert client.get("/admin/notices").status_code == 401


def test_the_notice_admin_page_renders(client, auth_cookies):
    resp = client.get("/admin/notices")
    assert resp.status_code == 200
    assert 'id="add-notice"' in resp.text
    assert "/api/notices/all" in resp.text


def test_the_dashboard_links_to_the_notice_page(client, auth_cookies):
    assert 'href="/admin/notices"' in client.get("/admin").text
