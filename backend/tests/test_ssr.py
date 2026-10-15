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
from app.models import ClosedDay
from app.ssr import (
    bar_today,
    build_payload,
    format_hours,
    format_time,
    pick,
    render_index_html,
)

# The shape Vite emits, and the two anchors `ssr.render_index` injects against.
BUILT_INDEX = (
    "<!doctype html>\n<html lang=\"en\">\n  <head>\n    <title>Marea Alta</title>\n"
    "  </head>\n  <body>\n    <div id=\"app\"></div>\n"
    "    <script type=\"module\" crossorigin src=\"/assets/index-abc.js\"></script>\n"
    "  </body>\n</html>\n"
)


@pytest.fixture()
def site(client, monkeypatch, tmp_path):
    """The test client with a built index.html in place.

    `frontend/dist` is gitignored, so the route tests point the server at a
    fixture shell rather than requiring a build.
    """
    index = tmp_path / "index.html"
    index.write_text(BUILT_INDEX, encoding="utf-8")
    monkeypatch.setattr(main_module, "INDEX_HTML", index)
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
    """Just the rendered markup, without the head styles or the JSON seed.

    The seed carries both languages on purpose (so the SPA can switch language
    without a request), so language assertions have to look at the block alone.
    """
    return html[
        html.index('<div id="marea-schedule">'): html.index("<script>window.__MAREA_ALTA_DATA__")
    ]


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