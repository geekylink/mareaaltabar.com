"""Tests for the server-rendered schedule (ticket #46).

The point of the feature is that a crawler receives the hours and party titles
in the HTML, so most of these assert on the *text* of ``GET /`` rather than on
a parsed structure — if the template stops emitting the day names, that is the
bug these should catch.
"""

import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from app import main as main_module
from app.models import ClosedDay, MenuItem
from app.ssr import (
    bar_today,
    build_payload,
    format_hours,
    format_price,
    format_time,
    json_ld_price,
    load_closed_days,
    load_menu,
    pick,
    render_index_html,
    render_menu_html,
)

# The shape Vite emits, and the two anchors `ssr.render_index` injects against.
BUILT_INDEX = (
    "<!doctype html>\n<html lang=\"en\">\n  <head>\n    <title>Marea Alta</title>\n"
    "  </head>\n  <body>\n    <div id=\"app\"></div>\n"
    "    <script type=\"module\" crossorigin src=\"/assets/index-abc.js\"></script>\n"
    "  </body>\n</html>\n"
)

# The second Vite entry point. Same anchors, its own bundle.
BUILT_MENU = (
    "<!doctype html>\n<html lang=\"en\">\n  <head>\n    <title>Menu</title>\n"
    "  </head>\n  <body>\n    <div id=\"app\"></div>\n"
    "    <script type=\"module\" crossorigin src=\"/assets/menu-xyz.js\"></script>\n"
    "  </body>\n</html>\n"
)


@pytest.fixture()
def site(client, monkeypatch, tmp_path):
    """The test client with a built index.html in place.

    `frontend/dist` is gitignored, so the route tests point the server at a
    fixture shell rather than requiring a build. Both documents are needed: the
    menu is a second Vite entry point with its own route.
    """
    index = tmp_path / "index.html"
    index.write_text(BUILT_INDEX, encoding="utf-8")
    menu = tmp_path / "menu.html"
    menu.write_text(BUILT_MENU, encoding="utf-8")
    monkeypatch.setattr(main_module, "INDEX_HTML", index)
    monkeypatch.setattr(main_module, "MENU_HTML", menu)
    return client


# --- The bar's clock -------------------------------------------------------


def test_bar_today_uses_the_bar_timezone_not_utc():
    """Ecuador is UTC-5, so 02:30 UTC on Sunday is still Saturday night there."""
    assert (6, "2026-01-03") == bar_today(datetime(2026, 1, 4, 2, 30, tzinfo=timezone.utc))


def test_bar_today_rolls_over_at_local_midnight():
    """02:30 UTC on Monday is Sunday evening in Montanita, not Monday."""
    assert (0, "2026-01-04") == bar_today(datetime(2026, 1, 5, 2, 30, tzinfo=timezone.utc))
    assert (1, "2026-01-05") == bar_today(datetime(2026, 1, 5, 5, 30, tzinfo=timezone.utc))


def test_bar_today_treats_naive_timestamps_as_utc():
    assert (6, "2026-01-03") == bar_today(datetime(2026, 1, 4, 2, 30))


def test_bar_today_without_an_argument_is_today():
    day, iso = bar_today()
    assert 0 <= day <= 6
    assert len(iso) == 10


# --- Display helpers mirror the frontend -----------------------------------


def test_format_time_matches_the_frontend_renderer():
    assert format_time("18:00", "en") == "6:00 PM"
    assert format_time("03:00", "en") == "3:00 AM"
    assert format_time("00:00", "en") == "12:00 AM"
    assert format_time("12:00", "en") == "12:00 PM"
    assert format_time("18:00", "es") == "6:00 p. m."
    assert format_time("03:00", "es") == "3:00 a. m."


def test_format_time_passes_through_malformed_values():
    assert format_time("", "en") == ""
    assert format_time(None, "en") == ""
    assert format_time("whenever", "en") == "whenever"


def test_format_hours_shows_the_closed_label():
    assert format_hours({"open_time": "16:00", "close_time": "04:00", "is_closed": True},
                        "en", "Closed today") == "Closed today"
    assert format_hours({"is_closed": False}, "en", "Closed today") == ""
    assert format_hours(None, "en", "Closed today") == ""


def test_pick_falls_back_to_english():
    row = {"title_en": "Latin Night", "title_es": "  "}
    assert pick(row, "es", "title") == "Latin Night"
    assert pick(row, "en", "title") == "Latin Night"
    assert pick(None, "en", "title") == ""


# --- Payload ---------------------------------------------------------------


def test_payload_marks_exactly_one_row_as_today(db_session):
    payload = build_payload(db_session, "en")
    today_rows = [d for d in payload["days"] if d["is_today"]]
    assert len(today_rows) == 1
    assert today_rows[0] is payload["tonight"]
    assert payload["today"] == today_rows[0]["day"]


def test_payload_marks_a_day_titled_closed_as_closed(db_session):
    """Mirrors App.svelte: a title of "Closed" closes the day, hours or not."""
    wednesday = build_payload(db_session, "en")["days"][3]
    assert wednesday["closed"] is True
    assert wednesday["title"] == ""
    assert wednesday["note"] == ""
    assert wednesday["hours"] == "Closed today"


def test_payload_seed_carries_both_languages(db_session):
    seed = build_payload(db_session, "en")["seed"]
    assert [d["day"] for d in seed["schedule"]] == list(range(7))
    assert seed["schedule"][5]["title_en"] == "Live Music"
    assert seed["schedule"][5]["title_es"] == "Música en Vivo"
    assert seed["closedDays"] == []


def test_payload_renders_the_other_language(db_session):
    payload = build_payload(db_session, "es")
    assert payload["days"][0]["day_name"] == "Domingo"
    assert payload["days"][0]["title"] == "Noche Latina"


# --- Closed days ------------------------------------------------------------


def test_load_closed_days_drops_rows_that_have_passed(db_session):
    db_session.add(ClosedDay(date="2001-12-25", reason_en="New Year", reason_es="Año Nuevo"))
    db_session.commit()
    assert load_closed_days(db_session, from_date="2002-01-01") == []
    assert [d["date"] for d in load_closed_days(db_session, from_date="2000-01-01")] == [
        "2001-12-25"
    ]


def test_load_closed_days_keeps_the_from_date_itself(db_session):
    """`>=`, not `>`: today is the date the frontend needs in order to know it is shut."""
    today = bar_today()[1]
    db_session.add(ClosedDay(date=today, reason_en="Holiday", reason_es="Feriado"))
    db_session.commit()
    assert [d["date"] for d in load_closed_days(db_session)] == [today]


def test_load_closed_days_defaults_to_today_at_the_bar(db_session):
    """No argument means the real bar clock, so a 2001 holiday is never published."""
    db_session.add(ClosedDay(date="2001-12-25", reason_en="New Year", reason_es="Año Nuevo"))
    db_session.commit()
    assert load_closed_days(db_session) == []


def test_payload_closes_today_when_a_closure_dates_it(db_session):
    """Mirrors App.svelte: a closure dated today closes the day as `is_closed` does.

    Without this the crawler-visible HTML promises tonight's party on a public
    holiday, and the page visibly changes the moment the SPA mounts over it.
    """
    db_session.add(ClosedDay(date=bar_today()[1], reason_en="Holiday", reason_es="Feriado"))
    db_session.commit()

    tonight = build_payload(db_session, "en")["tonight"]

    assert tonight["closed"] is True
    assert tonight["title"] == ""
    assert tonight["note"] == ""
    assert tonight["hours"] == "Closed today"


def test_payload_leaves_other_days_alone_when_today_is_closed(db_session):
    """One closure is one date: the weekly schedule behind it is untouched."""
    db_session.add(ClosedDay(date=bar_today()[1], reason_en="Holiday", reason_es="Feriado"))
    db_session.commit()

    days = build_payload(db_session, "en")["days"]
    tomorrow = next(d for d in days if not d["is_today"] and not d["closed"])

    assert tomorrow["hours"] != "Closed today"
    assert tomorrow["title"] != ""


def test_payload_carries_todays_closure_in_the_seed(db_session):
    """The SPA reads the seed, so the closure has to be in it or the first paint disagrees."""
    db_session.add(ClosedDay(date=bar_today()[1], reason_en="Holiday", reason_es="Feriado"))
    db_session.commit()

    seed = build_payload(db_session, "en")["seed"]

    assert [d["date"] for d in seed["closedDays"]] == [bar_today()[1]]


# --- Injection -------------------------------------------------------------


def test_render_index_injects_inside_the_mount_point(db_session):
    html = render_index_html(BUILT_INDEX, build_payload(db_session, "en"))
    assert '<div id="app"><div id="marea-schedule">' in html
    assert html.count('<div id="app">') == 1
    assert html.index("marea-schedule") < html.index("index-abc.js")


def test_rendered_html_is_balanced(db_session):
    """Injecting into a shell means owning its structure, not just its text.

    A stray closing tag does not fail a test, a browser or a crawler — it just
    quietly changes what the rest of the document means.
    """
    html = render_index_html(BUILT_INDEX, build_payload(db_session, "en"))
    assert tags_are_balanced(html)


def tags_are_balanced(html: str) -> bool:
    """True when every non-void element in ``html`` is closed in the right order."""
    void = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}
    stack: list[str] = []
    for event, tag in re.findall(r"<(/?)(\w+)[^>]*>", html):
        if tag in void:
            continue
        if event:
            if not stack or stack.pop() != tag:
                return False
        else:
            stack.append(tag)
    return not stack


def test_render_index_puts_the_styles_in_the_head(db_session):
    html = render_index_html(BUILT_INDEX, build_payload(db_session, "en"))
    assert html.index("#marea-schedule") < html.index("</head>")


def test_render_index_refuses_a_shell_it_cannot_find(db_session):
    """A silently empty schedule is worse than a loud failure."""
    with pytest.raises(RuntimeError):
        render_index_html("<html><body><div id=app></div></body></html>",
                          build_payload(db_session, "en"))
    with pytest.raises(RuntimeError):
        render_index_html('<div id="app"></div>', build_payload(db_session, "en"))


def test_seed_json_cannot_close_its_own_script_tag(db_session):
    """An admin-entered `</script>` must not break out of the seed element."""
    payload = build_payload(db_session, "en")
    payload["seed"] = {"title": "</script><script>alert(1)</script>"}

    html = render_index_html(BUILT_INDEX, payload)
    # Non-greedy: stops at the real closing tag, so this only matches if the
    # payload cannot smuggle one in.
    seed = re.search(r"__MAREA_ALTA_DATA__=(.*?)</script>", html, re.DOTALL)
    assert seed
    assert "</script>" not in seed.group(1)
    assert "<" not in seed.group(1)
    # The escape is legal in both JSON and JavaScript, so the value round-trips.
    assert json.loads(seed.group(1))["title"] == "</script><script>alert(1)</script>"


def test_seed_json_stays_parseable_with_markup_in_it(db_session):
    """`<!--` puts the HTML parser into a state that swallows the closing tag."""
    nasty = "<!-- comment --> & < > ' \" back\\slash é"
    payload = build_payload(db_session, "en")
    payload["seed"] = {"note": nasty}

    html = render_index_html(BUILT_INDEX, payload)
    seed = re.search(r"__MAREA_ALTA_DATA__=(.*?)</script>", html, re.DOTALL)
    assert "<!--" not in seed.group(1)
    assert json.loads(seed.group(1))["note"] == nasty


# --- The route -------------------------------------------------------------


def schedule_block(html: str) -> str:
    """Just the rendered schedule markup, without the head styles, the menu or
    the JSON seed.

    The seed carries both languages on purpose (so the SPA can switch language
    without a request), so language assertions have to look at the block alone.
    """
    start = html.index('<div id="marea-schedule">')
    for marker in ('<div id="marea-menu">', "<script>window.__MAREA_ALTA_DATA__"):
        end = html.find(marker, start)
        if end != -1:
            return html[start:end]
    return html[start:]


def test_root_renders_the_week_for_a_crawler(site):
    html = site.get("/").text
    for day in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
        assert day in html, day
    assert "Latin Night" in html
    assert "Singles Night" in html
    assert "Live Music" in html


def test_root_renders_the_opening_hours(site):
    html = site.get("/").text
    assert "4:00 PM - 2:00 AM" in html  # Sunday
    assert "4:00 PM - 4:00 AM" in html  # Monday
    assert "Closed today" in html


def test_root_highlights_tonights_party(site, db_session):
    """Tonight's title is the one thing the ticket names explicitly."""
    tonight = build_payload(db_session, "en")["tonight"]
    block = schedule_block(site.get("/").text)
    if tonight["closed"]:
        assert '<div class="ms-tonight">' not in block
    else:
        highlight = block[block.index('<div class="ms-tonight">'): block.index("ms-eyebrow")]
        assert tonight["title"] in highlight
        assert tonight["hours"] in highlight


def test_root_renders_closure_notices(site, db_session):
    db_session.add(ClosedDay(date="2030-12-25", reason_en="Christmas", reason_es="Navidad"))
    db_session.commit()
    block = schedule_block(site.get("/").text)
    assert "2030-12-25" in block
    assert "Christmas" in block


def test_root_does_not_publish_a_closure_that_has_passed(site, db_session):
    """The rendered HTML and the JSON endpoint both stop at today-and-later."""
    db_session.add(ClosedDay(date="2001-12-25", reason_en="New Year", reason_es="Año Nuevo"))
    db_session.commit()
    html = site.get("/").text
    assert "2001-12-25" not in html
    assert "New Year" not in html


def test_root_hides_tonights_party_when_today_is_closed(site, db_session):
    db_session.add(ClosedDay(date=bar_today()[1], reason_en="Holiday", reason_es="Feriado"))
    db_session.commit()
    block = schedule_block(site.get("/").text)
    assert '<div class="ms-tonight">' not in block


def test_root_is_not_cached(site):
    """An admin edit has to be visible to a crawler on its next visit."""
    assert site.get("/").headers["cache-control"] == "no-cache"


def test_root_defaults_to_english(site):
    html = site.get("/").text
    block = schedule_block(html)
    assert '<html lang="en">' in html
    assert "Latin Night" in block
    assert "Noche Latina" not in block


def test_root_can_render_spanish(site):
    html = site.get("/?lang=es").text
    block = schedule_block(html)
    assert '<html lang="es">' in html
    assert "Domingo" in block
    assert "Noche Latina" in block
    assert "Latin Night" not in block


def test_root_falls_back_to_english_for_an_unknown_language(site):
    html = site.get("/?lang=zz").text
    assert '<html lang="en">' in html
    assert "Latin Night" in schedule_block(html)


def test_index_html_is_rendered_too(site):
    assert "Latin Night" in site.get("/index.html").text


def test_head_returns_the_same_document_as_get(site):
    """Without HEAD registered, it falls through to the static mount and a
    crawler gets the un-rendered shell — a different document under the same URL."""
    assert site.head("/").headers["content-length"] == str(
        len(site.get("/").text.encode())
    )


def test_root_reports_a_missing_build(client, monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "INDEX_HTML", tmp_path / "nope.html")
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["detail"].startswith("Frontend not built")


def test_root_survives_a_render_failure(site, monkeypatch, caplog):
    """A broken template must not take the homepage down."""

    def boom(*_args, **_kwargs):
        raise RuntimeError("template exploded")

    monkeypatch.setattr(main_module, "render_index", boom)
    with caplog.at_level("ERROR"):
        resp = site.get("/")

    assert resp.status_code == 200
    assert "marea-schedule" not in resp.text
    assert 'id="app"' in resp.text
    assert "template exploded" in caplog.text


def test_static_paths_are_left_to_the_mount(client):
    """The rendered index must not swallow hashed assets."""
    assert client.get("/assets/does-not-exist.js").status_code == 404


# --- Admin edits reach the rendered HTML -----------------------------------


def test_an_admin_edit_is_visible_in_the_next_render(site, auth_cookies, csrf_token):
    assert "Reggae Night" not in site.get("/").text
    site.put(
        "/api/schedule/5",
        json={
            "title_en": "Reggae Night", "title_es": "Noche de Reggae",
            "note_en": "Roots and dub.", "note_es": "Roots y dub.",
            "open_time": "18:00", "close_time": "03:00", "is_closed": False,
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    html = site.get("/").text
    assert "Reggae Night" in html
    assert "6:00 PM - 3:00 AM" in html
    assert "Roots and dub." in html


def test_a_new_closure_is_visible_in_the_next_render(site, auth_cookies, csrf_token):
    site.post(
        "/api/closed-days",
        json={"date": "2031-01-01", "reason_en": "Storm", "reason_es": "Tormenta"},
        headers={"X-CSRF-Token": csrf_token},
    )
    html = site.get("/").text
    assert "2031-01-01" in html
    assert "Storm" in html


def test_admin_entered_markup_is_escaped(site, auth_cookies, csrf_token):
    site.put(
        "/api/schedule/4",
        json={
            "title_en": "<script>alert('xss')</script>", "title_es": "",
            "note_en": "onerror=alert(1)", "note_es": "",
            "open_time": "16:00", "close_time": "04:00", "is_closed": False,
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    html = site.get("/").text
    assert "<script>alert('xss')</script>" not in html
    assert "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in html


def test_the_api_and_the_rendered_html_agree(site):
    """One loader feeds both, so they can never describe different weeks."""
    from_api = site.get("/api/schedule").json()
    in_html = site.get("/").text
    for row in from_api:
        if row["title_en"] and not row["is_closed"]:
            assert row["title_en"] in in_html


# --- The menu (ticket #1) ---------------------------------------------------


def menu_block(html: str) -> str:
    """The rendered menu only, without the seed that carries both languages."""
    start = html.index('<div id="marea-menu">')
    end = html.find("<script>window.__MAREA_ALTA_DATA__", start)
    return html[start:end] if end != -1 else html[start:]


def test_format_price_mirrors_the_frontend_renderer():
    assert format_price("2.50") == "$2.50"
    assert format_price("0.25") == "$0.25"
    # A drink with no price yet must not read as free.
    assert format_price("") == ""
    assert format_price(None) == ""


def test_the_homepage_renders_the_menu_for_a_crawler(site):
    html = site.get("/").text
    block = menu_block(html)
    assert "Beer" in block
    assert "Cocktails" in block
    # Prices are the point of a menu, so they must not be behind a fetch.
    assert "$2.50" in block
    assert "$4.00" in block


def test_the_homepage_renders_the_menu_after_the_schedule(site):
    """Both blocks sit in #app; the schedule comes first, as before."""
    html = site.get("/").text
    assert html.index('<div id="marea-schedule">') < html.index('<div id="marea-menu">')


def test_the_homepage_menu_has_its_own_styles(site):
    html = site.get("/").text
    assert html.index("#marea-menu") < html.index("</head>")


def test_promos_render_under_the_price(site):
    block = menu_block(site.get("/").text)
    assert "$1.50" in block
    assert "Promo: 6x $7.00" in block


def test_ingredients_render_for_a_cocktail(site):
    block = menu_block(site.get("/").text)
    assert "Cuba Libre" in block
    assert "Rum, Coca-Cola, Lime juice, Ice" in block
    assert "Ingredients" in block


def test_the_homepage_can_render_the_menu_in_spanish(site):
    block = menu_block(site.get("/?lang=es").text)
    assert "Cócteles" in block
    assert "Cerveza" in block
    assert "Ron, Coca-Cola, Jugo de limón, Hielo" in block


def test_the_menu_route_renders_the_whole_menu(site):
    """A standalone document, so the URL can be shared and indexed on its own."""
    html = site.get("/menu").text
    block = menu_block(html)
    assert '<div id="marea-menu">' in html
    # The menu route is the menu alone — no schedule block.
    assert '<div id="marea-schedule">' not in html
    assert "Beer" in block
    assert "Cuba Libre" in block
    assert "$2.50" in block


def test_the_menu_route_is_answered_as_html(site):
    resp = site.get("/menu")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert resp.headers["cache-control"] == "no-cache"


def test_menu_html_is_rendered_too(site):
    """An old inbound link must not fall through to the raw shell."""
    assert "Cuba Libre" in site.get("/menu.html").text


def test_the_menu_route_defaults_to_english_and_can_switch(site):
    assert "Cocktails" in menu_block(site.get("/menu").text)
    spanish = site.get("/menu?lang=es")
    assert '<html lang="es">' in spanish.text
    assert "Cócteles" in menu_block(spanish.text)


def test_the_menu_route_falls_back_for_an_unknown_language(site):
    assert "Cocktails" in menu_block(site.get("/menu?lang=zz").text)


def test_the_menu_seed_carries_both_languages(db_session):
    """The SPA picks a language from the seed, so both must be in it."""
    seed = build_payload(db_session, "en")["seed"]
    cuba = next(
        item
        for category in seed["menu"]
        for item in category["items"]
        if item["name_en"] == "Cuba Libre"
    )
    assert cuba["ingredients_en"].startswith("Rum")
    assert cuba["ingredients_es"].startswith("Ron")


def test_a_menu_edit_is_visible_in_the_next_render(site, auth_cookies, csrf_token):
    cocktails = site.get("/api/menu").json()["categories"][-1]
    assert "Mojito" not in site.get("/menu").text

    site.post(
        "/api/menu/items",
        json={
            "category_id": cocktails["id"],
            "name_en": "Mojito",
            "name_es": "Mojito",
            "price": "5.00",
            "ingredients_en": "Rum, Mint, Lime, Soda",
            "ingredients_es": "Ron, Menta, Limón, Soda",
            "promos": [{"label_en": "2x1", "label_es": "2x1"}],
        },
        headers={"X-CSRF-Token": csrf_token},
    )

    block = menu_block(site.get("/menu").text)
    assert "Mojito" in block
    assert "$5.00" in block
    assert "Rum, Mint, Lime, Soda" in block
    assert "Promo: 2x1" in block


def test_a_hidden_drink_is_not_rendered(site, auth_cookies, csrf_token):
    menu = site.get("/api/menu").json()["categories"]
    beer = menu[0]["items"][2]
    site.put(
        f"/api/menu/items/{beer['id']}",
        json={**beer, "is_available": False},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert "Corona" not in menu_block(site.get("/menu").text)


def test_admin_entered_menu_markup_is_escaped(site, auth_cookies, csrf_token):
    cocktails = site.get("/api/menu").json()["categories"][-1]
    site.post(
        "/api/menu/items",
        json={
            "category_id": cocktails["id"],
            "name_en": "<script>alert('xss')</script>",
            "price": "4.00",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    html = site.get("/menu").text
    assert "<script>alert('xss')</script>" not in html
    assert "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in html


def test_the_menu_route_survives_a_render_failure(site, monkeypatch, caplog):
    """A broken template must not take the menu page down."""

    def boom(*_args, **_kwargs):
        raise RuntimeError("menu template exploded")

    monkeypatch.setattr(main_module, "render_menu", boom)
    with caplog.at_level("ERROR"):
        resp = site.get("/menu")

    assert resp.status_code == 200
    assert "marea-menu" not in resp.text
    assert 'id="app"' in resp.text
    assert "menu template exploded" in caplog.text


def test_the_menu_route_reports_a_missing_build(client, monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "MENU_HTML", tmp_path / "nope.html")
    resp = client.get("/menu")
    assert resp.status_code == 200
    assert resp.json()["detail"].startswith("Frontend not built")


def test_render_menu_refuses_a_shell_it_cannot_find(db_session):
    """A silently empty menu is worse than a loud failure."""
    with pytest.raises(RuntimeError):
        render_menu_html("<html><body></body></html>", build_payload(db_session, "en"))


def test_render_menu_injects_inside_the_mount_point(db_session):
    html = render_menu_html(BUILT_MENU, build_payload(db_session, "en"))
    assert '<div id="app"><div id="marea-menu">' in html
    assert html.count('<div id="app">') == 1
    assert tags_are_balanced(html)


def test_load_menu_hides_what_the_public_may_not_see(db_session):
    """One loader, two answers: the public read drops rows, the admin read keeps them."""
    cuba = next(i for c in load_menu(db_session) for i in c["items"] if i["name_en"] == "Cuba Libre")
    db_session.get(MenuItem, cuba["id"]).is_available = False
    db_session.commit()

    assert "cocteles" not in [c["slug"] for c in load_menu(db_session)]
    assert "cocteles" in [c["slug"] for c in load_menu(db_session, include_unavailable=True)]


# --- Menu structured data (ticket #49) -------------------------------------


def json_ld_block(html: str) -> dict:
    """The ``Menu`` graph, decoded from the document Google will read."""
    match = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    assert match is not None, "the menu route emitted no JSON-LD"
    return json.loads(match.group(1))


def menu_item(data: dict, section_name: str, item_name: str) -> dict:
    section = next(s for s in data["hasMenuSection"] if s["name"] == section_name)
    return next(i for i in section["hasMenuItem"] if i["name"] == item_name)


def test_json_ld_price_only_accepts_a_plain_amount():
    """A price Google cannot trust is worse than no price at all."""
    assert json_ld_price("2.50") == "2.50"
    assert json_ld_price("2.5") == "2.50"
    assert json_ld_price("$5") == "5.00"
    assert json_ld_price(" 3.00 ") == "3.00"

    assert json_ld_price("") is None
    assert json_ld_price(None) is None
    assert json_ld_price("ask") is None
    assert json_ld_price("2.505") is None
    assert json_ld_price("2,50") is None


def test_the_menu_route_emits_a_complete_menu_graph(site):
    data = json_ld_block(site.get("/menu").text)

    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "Menu"
    assert data["inLanguage"] == "en"
    assert data["url"] == "https://mareaaltabar.com/menu"

    sections = {s["name"]: s for s in data["hasMenuSection"]}
    assert "Beer" in sections
    assert "Cocktails" in sections

    beer = {i["name"]: i for i in sections["Beer"]["hasMenuItem"]}
    assert beer["Club Personal"]["offers"] == {
        "@type": "Offer",
        "price": "2.50",
        "priceCurrency": "USD",
    }

    cuba = next(i for i in sections["Cocktails"]["hasMenuItem"] if i["name"] == "Cuba Libre")
    assert cuba["offers"]["price"] == "4.00"
    assert cuba["offers"]["priceCurrency"] == "USD"


def test_menu_graph_follows_the_page_language(site, auth_cookies, csrf_token):
    cocktails = site.get("/api/menu").json()["categories"][-1]
    site.post(
        "/api/menu/items",
        json={
            "category_id": cocktails["id"],
            "name_en": "Mojito",
            "name_es": "Mojito",
            "description_en": "Rum, mint and lime.",
            "description_es": "Ron, menta y limón.",
            "price": "5.5",
        },
        headers={"X-CSRF-Token": csrf_token},
    )

    english = json_ld_block(site.get("/menu").text)
    mojito = menu_item(english, "Cocktails", "Mojito")
    assert mojito["description"] == "Rum, mint and lime."
    assert mojito["offers"]["price"] == "5.50"

    spanish = json_ld_block(site.get("/menu?lang=es").text)
    assert spanish["inLanguage"] == "es"
    mojito_es = menu_item(spanish, "Cócteles", "Mojito")
    assert mojito_es["description"] == "Ron, menta y limón."
    assert mojito_es["offers"]["price"] == "5.50"


def test_menu_graph_omits_an_unparseable_price(site, db_session):
    cocktails = next(c for c in load_menu(db_session) if c["slug"] == "cocteles")
    db_session.add(
        MenuItem(category_id=cocktails["id"], name_en="Catch of the day", price="ask")
    )
    db_session.commit()

    data = json_ld_block(site.get("/menu").text)
    item = menu_item(data, "Cocktails", "Catch of the day")
    assert "offers" not in item


def test_menu_graph_cannot_close_its_own_script_tag(site, auth_cookies, csrf_token):
    """Item names are admin-entered, so the JSON-LD is another escaping boundary."""
    nasty = "</script><script>alert(1)</script>"
    cocktails = site.get("/api/menu").json()["categories"][-1]
    site.post(
        "/api/menu/items",
        json={"category_id": cocktails["id"], "name_en": nasty, "price": "4.00"},
        headers={"X-CSRF-Token": csrf_token},
    )

    html = site.get("/menu").text
    assert nasty not in html
    assert menu_item(json_ld_block(html), "Cocktails", nasty)["name"] == nasty


def test_the_homepage_does_not_duplicate_the_menu_graph(site):
    """The dedicated menu URL owns the Menu entity; the homepage has the markup."""
    html = site.get("/").text
    assert 'type="application/ld+json"' not in html