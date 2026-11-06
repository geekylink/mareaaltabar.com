"""Tests for the admin logs: login attempts, and menu and schedule changes.

Two things are worth guarding here. The first is that every outcome of a login
lands in the log — a rate-limited attempt is the one an owner most wants to see,
and it is the one most easily missed. The second is that a change cannot happen
without its log row, since a log that silently skips edits is worse than no log
at all: it looks like evidence.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app import audit, main
from app.models import AuditEntry, LoginAttempt, MenuItem


# --- Helpers ---


def logins(client):
    return client.get("/api/logs/logins").json()["entries"]


def recorded_logins(db_session):
    """Login rows straight from the table.

    Used where logging in to read the log would add a row of its own — several of
    these tests are about the login that the read would otherwise contaminate.
    """
    return list(db_session.execute(select(LoginAttempt).order_by(LoginAttempt.id)).scalars())


def menu_log(client):
    return client.get("/api/logs/menu").json()["entries"]


def schedule_log(client):
    return client.get("/api/logs/schedule").json()["entries"]


def write_headers(csrf_token):
    return {"X-CSRF-Token": csrf_token}


def save_day(client, csrf_token, **overrides):
    """Save a weekday the way the panel does: the whole day, every time."""
    day = overrides.pop("day", 5)
    payload = {
        "title_en": "Reggae Night",
        "title_es": "Noche de Reggae",
        "note_en": "Roots and dub all night.",
        "note_es": "Roots y dub toda la noche.",
        "open_time": "18:00",
        "close_time": "03:00",
        "is_closed": False,
    }
    payload.update(overrides)
    return client.put(
        f"/api/schedule/{day}", json=payload, headers=write_headers(csrf_token)
    )


# --- Login attempts ---


def test_successful_login_is_logged(client, admin_user):
    client.post(
        "/admin/login",
        data={"username": admin_user["username"], "password": admin_user["password"]},
        follow_redirects=False,
    )
    entries = logins(client)
    assert len(entries) == 1
    assert entries[0]["username"] == admin_user["username"]
    assert entries[0]["outcome"] == "success"
    assert entries[0]["ip"] == "testclient"


def test_successful_login_still_needs_a_session_to_read_the_log(client, admin_user):
    """The login log holds usernames and addresses; it is not public."""
    client.post(
        "/admin/login",
        data={"username": admin_user["username"], "password": admin_user["password"]},
        follow_redirects=False,
    )
    client.cookies.clear()
    assert client.get("/api/logs/logins").status_code == 401


def test_failed_login_is_logged_with_the_username_that_was_tried(
    client, admin_user, db_session
):
    client.post(
        "/admin/login",
        data={"username": admin_user["username"], "password": "wrong"},
        follow_redirects=False,
    )
    entries = recorded_logins(db_session)
    assert len(entries) == 1
    assert entries[0].outcome == "invalid_credentials"
    assert entries[0].username == admin_user["username"]
    assert entries[0].ip == "testclient"


def test_login_for_a_username_that_does_not_exist_is_logged(client, db_session):
    """A stranger guessing at names has to show up, or the log records nothing useful."""
    client.post(
        "/admin/login",
        data={"username": "nobody", "password": "guess"},
        follow_redirects=False,
    )
    entries = recorded_logins(db_session)
    assert [e.username for e in entries] == ["nobody"]
    assert entries[0].outcome == "invalid_credentials"


def test_rate_limited_attempt_is_logged(client, admin_user, db_session):
    """The attempt the limiter turned away is the one worth seeing afterwards."""
    for _ in range(5):
        client.post(
            "/admin/login",
            data={"username": admin_user["username"], "password": "wrong"},
            follow_redirects=False,
        )
    resp = client.post(
        "/admin/login",
        data={"username": admin_user["username"], "password": "wrong"},
        follow_redirects=False,
    )
    assert "rate_limited" in resp.headers.get("location", "")

    outcomes = [e.outcome for e in recorded_logins(db_session)]
    assert outcomes[-1] == "rate_limited"
    assert outcomes.count("invalid_credentials") == 5


def test_login_log_records_the_user_agent(client, admin_user):
    client.post(
        "/admin/login",
        data={"username": admin_user["username"], "password": admin_user["password"]},
        headers={"User-Agent": "Mozilla/5.0 (test browser)"},
        follow_redirects=False,
    )
    assert logins(client)[0]["user_agent"] == "Mozilla/5.0 (test browser)"


def test_a_long_user_agent_is_truncated_rather_than_rejected(client, admin_user):
    """A client sending a 4KB user agent must still be able to log in."""
    resp = client.post(
        "/admin/login",
        data={"username": admin_user["username"], "password": admin_user["password"]},
        headers={"User-Agent": "x" * 4000},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert len(logins(client)[0]["user_agent"]) == audit.USER_AGENT_MAX


def test_the_password_is_never_stored_in_either_log(client, admin_user, db_session):
    """The strongest form of the guarantee: the value is nowhere in the database."""
    for _ in range(2):
        client.post(
            "/admin/login",
            data={"username": admin_user["username"], "password": "correcthorsebatterystaple"},
            follow_redirects=False,
        )

    dump = ""
    for table in ("login_attempts", "audit_log"):
        rows = db_session.execute(text(f"SELECT * FROM {table}")).fetchall()
        dump += " ".join(str(tuple(row)) for row in rows)

    assert "correcthorsebatterystaple" not in dump


def test_the_login_log_has_no_password_column(db_session):
    columns = {row[1] for row in db_session.execute(text("PRAGMA table_info(login_attempts)"))}
    assert columns
    assert not any("password" in name for name in columns)


# --- Schedule changes ---


def test_saving_a_day_logs_the_fields_that_changed(client, auth_cookies, csrf_token):
    save_day(client, csrf_token, day=5, open_time="20:00")

    entries = schedule_log(client)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["area"] == "schedule"
    assert entry["action"] == "update"
    assert entry["target"] == "schedule_day:5"
    assert entry["admin_username"] == "testadmin"
    assert entry["ip"] == "testclient"

    changed = entry["details"]
    assert set(changed) >= {"title_en", "open_time"}
    assert changed["open_time"] == {"from": "16:00", "to": "20:00"}
    assert changed["title_en"]["to"] == "Reggae Night"


def test_saving_a_day_unchanged_logs_nothing(client, auth_cookies, csrf_token):
    """A 'Save all days' press on an untouched week must not bury a real edit."""
    save_day(client, csrf_token, day=5, open_time="20:00")
    before = len(schedule_log(client))

    saved = client.get("/api/schedule").json()[5]
    resp = client.put(
        "/api/schedule/5",
        json={
            "title_en": saved["title_en"],
            "title_es": saved["title_es"],
            "note_en": saved["note_en"],
            "note_es": saved["note_es"],
            "open_time": saved["open_time"],
            "close_time": saved["close_time"],
            "is_closed": saved["is_closed"],
        },
        headers=write_headers(csrf_token),
    )
    assert resp.status_code == 200
    assert len(schedule_log(client)) == before


def test_closing_a_day_is_logged(client, auth_cookies, csrf_token):
    """Thursday is open in the seed data, so the flag genuinely flips."""
    save_day(client, csrf_token, day=4, is_closed=True)
    changed = schedule_log(client)[0]["details"]
    assert changed["is_closed"] == {"from": False, "to": True}
    assert schedule_log(client)[0]["target"] == "schedule_day:4"


def test_adding_a_closed_day_is_logged_in_the_schedule_log(client, auth_cookies, csrf_token):
    resp = client.post(
        "/api/closed-days",
        json={"date": "2099-12-25", "reason_en": "Christmas", "reason_es": "Navidad"},
        headers=write_headers(csrf_token),
    )
    assert resp.status_code == 201

    entries = schedule_log(client)
    assert len(entries) == 1
    assert entries[0]["action"] == "create"
    assert entries[0]["target"] == "closed_day:2099-12-25"
    assert entries[0]["target_name"] == "Christmas"
    assert entries[0]["details"]["reason_es"] == "Navidad"


def test_correcting_and_removing_a_closed_day_is_logged(client, auth_cookies, csrf_token):
    created = client.post(
        "/api/closed-days",
        json={"date": "2099-12-25", "reason_en": "Christmas", "reason_es": "Navidad"},
        headers=write_headers(csrf_token),
    ).json()

    client.patch(
        f"/api/closed-days/{created['id']}",
        json={"reason_en": "Christmas Day", "reason_es": "Navidad"},
        headers=write_headers(csrf_token),
    )
    client.delete(f"/api/closed-days/{created['id']}", headers=write_headers(csrf_token))

    actions = [e["action"] for e in schedule_log(client)]
    assert actions == ["delete", "update", "create"]
    assert schedule_log(client)[1]["details"]["reason_en"] == {
        "from": "Christmas",
        "to": "Christmas Day",
    }


def test_a_change_that_fails_validation_is_not_logged(client, auth_cookies, csrf_token):
    """A rejected write never happened, so it must not appear to have."""
    resp = client.put(
        "/api/schedule/9",
        json={"title_en": "Nope"},
        headers=write_headers(csrf_token),
    )
    assert resp.status_code == 400
    assert schedule_log(client) == []


# --- Menu changes ---


def test_adding_a_category_is_logged(client, auth_cookies, csrf_token):
    resp = client.post(
        "/api/menu/categories",
        json={"name_en": "Food", "name_es": "Comida", "slug": "comida", "is_available": True},
        headers=write_headers(csrf_token),
    )
    assert resp.status_code == 201

    entry = menu_log(client)[0]
    assert entry["action"] == "create"
    assert entry["target"] == f"menu_category:{resp.json()['id']}"
    assert entry["target_name"] == "Food"
    assert entry["details"]["slug"] == "comida"
    assert entry["admin_username"] == "testadmin"


def test_renaming_a_category_logs_the_new_title_and_nothing_else(client, auth_cookies, csrf_token):
    categories = client.get("/api/menu/all").json()["categories"]
    beer = next(c for c in categories if c["slug"] == "cerveza")

    client.patch(
        f"/api/menu/categories/{beer['id']}",
        json={"name_en": "Beers", "name_es": "Cervezas", "slug": "cerveza", "is_available": True},
        headers=write_headers(csrf_token),
    )

    changed = menu_log(client)[0]["details"]
    assert changed["name_en"] == {"from": "Beer", "to": "Beers"}
    assert "slug" not in changed, "an unchanged field must not appear in the log"


def test_hiding_a_category_is_logged(client, auth_cookies, csrf_token):
    categories = client.get("/api/menu/all").json()["categories"]
    wine = next(c for c in categories if c["slug"] == "vinos")

    client.patch(
        f"/api/menu/categories/{wine['id']}",
        json={"name_en": "Wine", "name_es": "Vinos", "slug": "vinos", "is_available": False},
        headers=write_headers(csrf_token),
    )

    assert menu_log(client)[0]["details"]["is_available"] == {"from": True, "to": False}


def test_adding_a_drink_logs_its_price_and_promos(client, auth_cookies, csrf_token):
    categories = client.get("/api/menu/all").json()["categories"]
    beer = next(c for c in categories if c["slug"] == "cerveza")

    resp = client.post(
        "/api/menu/items",
        json={
            "category_id": beer["id"],
            "name_en": "Pilsener Sixpack",
            "name_es": "Pilsener sixpack",
            "price": "9.00",
            "is_available": True,
            "promos": [{"label_en": "case $9.00", "label_es": "caja $9.00"}],
        },
        headers=write_headers(csrf_token),
    )
    assert resp.status_code == 201

    entry = menu_log(client)[0]
    assert entry["target"] == f"menu_item:{resp.json()['id']}"
    assert entry["target_name"] == "Pilsener Sixpack"
    assert entry["details"]["price"] == "9.00"
    assert entry["details"]["promos"] == [{
        "label_en": "case $9.00",
        "label_es": "caja $9.00",
        "days": "",
        "start_time": "",
        "end_time": "",
        "starts_on": "",
        "ends_on": "",
        "is_active": True,
    }]


def test_editing_a_drink_logs_only_the_price_that_moved(client, auth_cookies, csrf_token):
    items = client.get("/api/menu/all").json()["categories"][0]["items"]
    beer = items[0]

    client.put(
        f"/api/menu/items/{beer['id']}",
        json={
            "category_id": beer["category_id"],
            "name_en": beer["name_en"],
            "name_es": beer["name_es"],
            "description_en": beer["description_en"],
            "description_es": beer["description_es"],
            "ingredients_en": beer["ingredients_en"],
            "ingredients_es": beer["ingredients_es"],
            "price": "2.75",
            "is_available": beer["is_available"],
            "promos": [
                {"label_en": p["label_en"], "label_es": p["label_es"]} for p in beer["promos"]
            ],
        },
        headers=write_headers(csrf_token),
    )

    assert menu_log(client)[0]["details"] == {
        "price": {"from": beer["price"], "to": "2.75"}
    }


def test_removing_a_drink_is_logged_with_what_it_was(client, auth_cookies, csrf_token):
    categories = client.get("/api/menu/all").json()["categories"]
    cigarette = next(c for c in categories if c["slug"] == "cigarrillos")
    item = cigarette["items"][0]

    client.delete(f"/api/menu/items/{item['id']}", headers=write_headers(csrf_token))

    entry = menu_log(client)[0]
    assert entry["action"] == "delete"
    assert entry["target_name"] == item["name_en"]
    assert entry["details"]["price"] == item["price"]


def test_removing_a_category_records_how_many_drinks_went_with_it(client, auth_cookies, csrf_token):
    categories = client.get("/api/menu/all").json()["categories"]
    beer = next(c for c in categories if c["slug"] == "cerveza")

    client.delete(f"/api/menu/categories/{beer['id']}", headers=write_headers(csrf_token))

    """The drinks are gone for good, so the log at least says how many."""
    assert menu_log(client)[0]["details"]["items_removed"] == len(beer["items"])


def test_the_menu_log_does_not_swallow_schedule_changes(client, auth_cookies, csrf_token):
    save_day(client, csrf_token, day=5, open_time="20:00")
    client.post(
        "/api/menu/categories",
        json={"name_en": "Food", "name_es": "Comida", "slug": "comida"},
        headers=write_headers(csrf_token),
    )

    assert [e["area"] for e in menu_log(client)] == ["menu"]
    assert [e["area"] for e in schedule_log(client)] == ["schedule"]


def test_moving_a_drink_to_another_section_is_logged(client, auth_cookies, csrf_token):
    categories = client.get("/api/menu/all").json()["categories"]
    source = next(c for c in categories if c["slug"] == "cerveza")
    destination = next(c for c in categories if c["slug"] == "cocteles")
    item = source["items"][0]

    client.put(
        f"/api/menu/items/{item['id']}",
        json={
            "category_id": destination["id"],
            "name_en": item["name_en"],
            "name_es": item["name_es"],
            "price": item["price"],
            "is_available": item["is_available"],
            "promos": [],
        },
        headers=write_headers(csrf_token),
    )

    changed = menu_log(client)[0]["details"]
    assert changed["category_id"]["from"] == source["id"]
    assert changed["category_id"]["to"] == destination["id"]


# --- Reading the logs ---


def test_the_logs_page_needs_a_session(client):
    assert client.get("/admin/logs").status_code == 401


def test_the_logs_page_renders_for_a_signed_in_admin(client, auth_cookies):
    resp = client.get("/admin/logs")
    assert resp.status_code == 200
    assert "/api/logs/logins" in resp.text
    assert 'href="#menu"' in resp.text
    assert 'href="#schedule"' in resp.text


def test_the_dashboard_links_to_the_logs_page(client, auth_cookies):
    assert "/admin/logs" in client.get("/admin").text


def test_every_log_endpoint_needs_a_session(client, auth_cookies):
    assert client.get("/api/logs/logins").status_code == 200


@pytest.mark.parametrize("path", ["/api/logs/logins", "/api/logs/menu", "/api/logs/schedule"])
def test_anonymous_reads_are_refused(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", ["/api/logs/logins", "/api/logs/menu", "/api/logs/schedule"])
@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_the_log_endpoints_cannot_be_written_to(client, auth_cookies, csrf_token, path, method):
    """Read-only is structural: there is no route that would accept a change."""
    headers = write_headers(csrf_token)
    call = getattr(client, method)
    resp = call(path, headers=headers) if method == "delete" else call(
        path, json={}, headers=headers
    )
    assert resp.status_code == 405


def test_logs_are_newest_first(client, auth_cookies, csrf_token):
    for hour in ("18:00", "19:00", "20:00"):
        save_day(client, csrf_token, day=5, open_time=hour)

    entries = schedule_log(client)
    assert [e["details"]["open_time"]["to"] for e in entries] == ["20:00", "19:00", "18:00"]


def test_paging_returns_fresh_rows_and_a_total(client, auth_cookies, csrf_token):
    for hour in ("18:00", "19:00", "20:00"):
        save_day(client, csrf_token, day=5, open_time=hour)

    first = client.get("/api/logs/schedule?limit=2").json()
    second = client.get("/api/logs/schedule?limit=2&offset=2").json()

    assert first["total"] == 3
    assert second["total"] == 3
    assert len(first["entries"]) == 2
    ids = [e["id"] for e in first["entries"] + second["entries"]]
    assert len(set(ids)) == 3, "pages must not overlap"


def test_a_limit_beyond_the_ceiling_is_clamped(client, auth_cookies):
    """A hand-typed limit cannot ask the server for the whole table at once."""
    resp = client.get("/api/logs/logins?limit=100000")
    assert resp.status_code == 200
    assert len(resp.json()["entries"]) <= 500


def test_paging_arguments_are_clamped_before_the_query_runs():
    """The clamp itself, rather than the size of the table it protects."""
    from app.routers.logs import _page

    assert _page(0, 0) == (1, 0)
    assert _page(-5, -5) == (1, 0)
    assert _page(10_000, 0) == (500, 0)
    assert _page(200, 40) == (200, 40)


def test_an_empty_log_reports_zero_rather_than_failing(client, auth_cookies):
    payload = client.get("/api/logs/menu").json()
    assert payload["entries"] == []
    assert payload["total"] == 0


def test_timestamps_are_labelled_utc(client, admin_user):
    """A zone-less ISO string is read as local time by a browser, which would
    put every entry five hours out for a bar in Ecuador."""
    client.post(
        "/admin/login",
        data={"username": admin_user["username"], "password": admin_user["password"]},
        follow_redirects=False,
    )
    created_at = logins(client)[0]["created_at"]
    assert created_at.endswith("+00:00") or created_at.endswith("Z")


# --- Retention ---


def test_a_log_row_is_only_published_by_the_caller_s_commit(db_session):
    """The change and its log row are one transaction, so one cannot survive
    without the other: `log_change` adds, and the caller's commit publishes."""
    db_session.add(MenuItem(category_id=1, name_en="Log Test Drink", price="4.00"))
    audit.log_change(
        db_session,
        area=audit.AREA_MENU,
        action=audit.ACTION_CREATE,
        author=audit.ChangeAuthor("testadmin", "10.0.0.1", "test-agent"),
        target="menu_item:1",
        target_name="Log Test Drink",
        details={"price": "4.00"},
    )
    db_session.rollback()  # as though the write had failed

    assert db_session.execute(select(AuditEntry)).scalars().all() == []
    surviving = db_session.execute(
        select(MenuItem).where(MenuItem.name_en == "Log Test Drink")
    ).scalars().all()
    assert surviving == []


def test_the_login_log_is_written_even_though_it_commits_itself(db_session):
    """A login has no transaction of its own to join, so it commits on the spot
    — and a broken log must never turn a valid login into an error page."""
    audit.log_login_attempt(
        db_session, username="testadmin", ip="10.0.0.1", user_agent="a", outcome="success"
    )
    rows = db_session.execute(select(LoginAttempt)).scalars().all()
    assert [(r.username, r.ip, r.outcome) for r in rows] == [("testadmin", "10.0.0.1", "success")]


def _age(row, days: int) -> None:
    """Backdate a row so the purge has something to find."""
    row.created_at = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)


def test_the_purge_removes_old_rows_and_keeps_recent_ones(db_session):
    old_login = LoginAttempt(username="old", ip="1.1.1.1", outcome="success")
    new_login = LoginAttempt(username="new", ip="1.1.1.1", outcome="success")
    old_entry = AuditEntry(area="menu", action="update", admin_username="a", target="menu_item:1")
    db_session.add_all([old_login, new_login, old_entry])
    db_session.commit()
    _age(old_login, 200)
    _age(old_entry, 200)
    db_session.commit()

    removed = audit.purge_old_logs(db_session, 90)

    assert removed == {"login_attempts": 1, "audit_log": 1}
    remaining = db_session.execute(select(LoginAttempt)).scalars().all()
    assert [r.username for r in remaining] == ["new"]


def test_the_purge_is_idempotent(db_session):
    """The server and the CLI both run it; running it twice must not error."""
    db_session.add(LoginAttempt(username="old", ip="1.1.1.1", outcome="success"))
    db_session.commit()
    _age(db_session.execute(select(LoginAttempt)).scalars().one(), 200)
    db_session.commit()

    assert audit.purge_old_logs(db_session, 90)["login_attempts"] == 1
    assert audit.purge_old_logs(db_session, 90)["login_attempts"] == 0


def test_the_purge_refuses_a_zero_day_window(db_session):
    """`--days 0` reads as 'keep nothing', which is a trap rather than a feature."""
    with pytest.raises(ValueError):
        audit.purge_old_logs(db_session, 0)


def test_the_purge_defaults_to_the_configured_window(db_session):
    from app.config import settings

    db_session.add(LoginAttempt(username="x", ip="1.1.1.1", outcome="success"))
    db_session.commit()
    # Old enough for any sane window, new enough for none of them.
    _age(db_session.execute(select(LoginAttempt)).scalars().one(), settings.LOG_RETENTION_DAYS + 1)
    db_session.commit()

    assert audit.purge_old_logs(db_session)["login_attempts"] == 1


def test_the_next_purge_is_at_seven_in_the_morning_at_the_bar():
    """06:59:59 at the bar is one second away; 07:00:00 means tomorrow."""
    just_before = datetime(2026, 10, 16, 11, 59, 59, tzinfo=timezone.utc)  # 06:59:59 -05
    assert audit.seconds_until_next_purge(just_before) == pytest.approx(1, abs=1)

    exactly_seven = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)  # 07:00 -05
    assert audit.seconds_until_next_purge(exactly_seven) == pytest.approx(24 * 3600, abs=1)


def test_the_next_purge_survives_a_naive_timestamp():
    """Tests and callers may pass a naive UTC time; the same answer either way."""
    aware = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
    assert audit.seconds_until_next_purge(aware) == audit.seconds_until_next_purge(
        aware.replace(tzinfo=None)
    )


def test_the_scheduled_purge_runs_and_then_stops_cleanly(db_session, monkeypatch):
    """The daily job is a sleeping task in the lifespan: it must actually purge,
    and cancelling it on shutdown must not raise out of the app."""
    db_session.add(LoginAttempt(username="old", ip="1.1.1.1", outcome="success"))
    db_session.commit()
    _age(db_session.execute(select(LoginAttempt)).scalars().one(), 200)
    db_session.commit()

    # The real one is "seconds until 07:00"; here the wait is a blink.
    monkeypatch.setattr(audit, "seconds_until_next_purge", lambda *a, **k: 0.01)
    monkeypatch.setattr(main, "SessionLocal", lambda: db_session)

    async def scenario():
        task = asyncio.create_task(main._daily_log_purge())
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert db_session.execute(select(LoginAttempt)).scalars().all() == []


@pytest.mark.parametrize("enabled", [True, False])
def test_the_daily_purge_follows_the_setting(monkeypatch, enabled):
    """`DAILY_LOG_PURGE=false` is the switch for a deploy that purges from cron
    instead, so the server must not start the job at all."""
    from fastapi.testclient import TestClient

    started = []
    monkeypatch.setattr(main.settings, "DAILY_LOG_PURGE", enabled)

    async def stand_in():
        started.append(True)
        await asyncio.sleep(3600)  # never reached; cancelled on shutdown

    monkeypatch.setattr(main, "_daily_log_purge", stand_in)
    with TestClient(main.app):
        pass
    assert bool(started) is enabled
