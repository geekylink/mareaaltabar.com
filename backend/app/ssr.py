"""Server-side rendering of the public schedule, for crawlers.

``App.svelte`` fetches ``/api/schedule`` on mount, so the hours, party titles and
closure notices never reach the HTML a crawler sees — and for a bar in a tourist
town that data *is* the search result. This module renders the same week into
``frontend/dist/index.html`` at request time, so the served HTML always carries
the current hours rather than whatever was true when the site was last built.

Two things come out of one pass:

1. A schedule block inside ``<div id="app">`` — plain HTML a crawler (or a
   visitor with JavaScript disabled) can read.
2. ``window.__MAREA_ALTA_DATA__`` — the same payload seeded into the page so the
   SPA renders immediately instead of showing a loading state and re-fetching.
   ``src/main.js`` clears the server block before ``mount()``; Svelte appends
   rather than replacing, so without that the two copies would stack.

Deliberately not hydration. The SPA fetches its own data and picks the
visitor's language, which the server cannot know, so matching the two trees
would mean restructuring the client. The server block is replaced within the
same tick the app mounts.

Everything in here is a pure function of the database, which keeps the JSON API
and the rendered HTML from drifting: ``routers/api.py`` imports the same
loaders.
"""

import json
import re
from datetime import datetime, timedelta, timezone

from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.config import BACKEND_DIR
from app.models import ClosedDay, Event, Hours
from app.public_i18n import strings_for

FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"
TEMPLATES_DIR = BACKEND_DIR / "app" / "templates"

# The SPA's mount target, and the anchor the schedule block is injected into.
# Vite rewrites asset URLs but leaves this element's markup alone, so the exact
# string is stable — if it ever is not, the render fails loudly rather than
# silently serving an empty schedule. The whole element, not just the opening
# tag: replacing only that would leave a second, stray `</div>` behind.
APP_MOUNT = '<div id="app"></div>'
HEAD_CLOSE = "</head>"

# Ecuador is UTC-5 year-round: DST was abolished in 1992. A fixed offset is used
# instead of ZoneInfo so no tzdata package is needed on a slim container.
BAR_UTC_OFFSET = timedelta(hours=-5)

# Mirrors App.svelte: a day titled exactly "Closed"/"Cerrado" is a closure even
# if the hours row disagrees.
CLOSED_TITLE_RE = re.compile(r"^(closed|cerrado)$", re.IGNORECASE)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Keep the JSON seed from closing the script tag it lives in, or opening an
# HTML comment the parser would then swallow the rest of the page into. Every
# `<` is escaped rather than just the dangerous sequences: one rule, and the
# value survives `JSON.parse` unchanged because `<` is a legal string escape in
# both JSON and JavaScript. Admin-entered text reaches this string.
JSON_LT = "<"
JSON_LT_ESCAPED = "\\u003c"


# --- Bar-local clock -------------------------------------------------------


def bar_today(now: datetime | None = None) -> tuple[int, str]:
    """Return ``(day_of_week, iso_date)`` at the bar, 0 = Sunday.

    Day indices follow the JavaScript convention the database and the rest of
    the app already use. ``now`` is injectable purely so tests can pin a date.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(timezone(BAR_UTC_OFFSET))
    return (local.weekday() + 1) % 7, local.date().isoformat()


# --- Shared data loading ---------------------------------------------------


def day_payload(event: Event, hours: Hours | None) -> dict:
    """One weekday: its event text and its opening hours, both languages."""
    h = hours
    return {
        "day": event.day,
        "title_en": event.title_en,
        "title_es": event.title_es,
        "note_en": event.note_en,
        "note_es": event.note_es,
        "open_time": h.open_time if h else "",
        "close_time": h.close_time if h else "",
        "is_closed": bool(h.is_closed) if h else False,
    }


def load_schedule(db: DBSession) -> list[dict]:
    """The whole week, ordered Sunday first, in the shape ``/api/schedule`` returns."""
    events = db.execute(select(Event).order_by(Event.day)).scalars().all()
    hours_by_day = {h.day: h for h in db.execute(select(Hours)).scalars().all()}
    return [day_payload(e, hours_by_day.get(e.day)) for e in events]


def load_closed_days(db: DBSession, from_date: str | None = None) -> list[dict]:
    """One-off closures from ``from_date`` onward, in the shape ``/api/closed-days`` returns.

    A closure is only news on and after its date, so rows that have already
    passed are dropped: otherwise every holiday the bar has ever taken off
    renders on the site for ever. ``ClosedDay.date`` is an ISO string, which
    compares correctly in SQL, and the filter is in the query rather than in
    Python so it cannot drift between this loader and its callers.

    ``from_date`` defaults to today *at the bar*, not on the server — the two
    differ by five hours, and the row the bar shows is the row it must accept.
    It is injectable purely so tests can pin a date, as ``bar_today`` is.
    """
    if from_date is None:
        from_date = bar_today()[1]
    days = db.execute(
        select(ClosedDay).where(ClosedDay.date >= from_date).order_by(ClosedDay.date)
    ).scalars().all()
    return [
        {"id": d.id, "date": d.date, "reason_en": d.reason_en, "reason_es": d.reason_es}
        for d in days
    ]


# --- Display helpers (mirrors frontend/src/lib/api.js) ----------------------


def pick(row: dict | None, lang: str, field: str) -> str:
    """The visitor's language for ``field``, falling back to English when blank."""
    row = row or {}
    value = row.get(f"{field}_es" if lang == "es" else f"{field}_en")
    if value and value.strip():
        return value
    return row.get(f"{field}_en") or ""


def format_time(hhmm: str | None, lang: str) -> str:
    """A 24-hour ``HH:MM`` value as 12-hour text for the visitor's locale."""
    if not hhmm:
        return ""
    head, sep, minute = str(hhmm).partition(":")
    if not sep or not head.isdigit() or not minute.isdigit():
        return str(hhmm)
    hour = int(head)
    if lang == "es":
        display = "p. m." if hour >= 12 else "a. m."
    else:
        display = "PM" if hour >= 12 else "AM"
    return f"{hour % 12 or 12}:{minute} {display}"


def format_hours(day: dict | None, lang: str, closed_label: str) -> str:
    """An opening-hours range, or the closed label."""
    if not day:
        return ""
    if day.get("is_closed"):
        return closed_label
    if not day.get("open_time") or not day.get("close_time"):
        return ""
    return f"{format_time(day['open_time'], lang)} - {format_time(day['close_time'], lang)}"


# --- Template payload ------------------------------------------------------


def build_payload(db: DBSession, lang: str) -> dict:
    """Everything the schedule block renders, resolved for one language.

    A closure dated today closes the day as surely as the weekday's own
    ``is_closed`` flag does, so today's row is resolved closed when ``closedDays``
    contains it. App.svelte merges the same three sources (the flag, a title of
    "Closed"/"Cerrado", and a closure dated today) into one flag; if this side did
    not, the rendered HTML would promise a party on a public holiday and the page
    would visibly change the moment the app mounted over it.
    """
    labels = strings_for(lang)
    today, today_iso = bar_today()
    schedule = load_schedule(db)
    closed_days = load_closed_days(db)
    closed_today = any(d["date"] == today_iso for d in closed_days)

    days = []
    for row in schedule:
        title = pick(row, lang, "title")
        shut = row["day"] == today and closed_today
        closed = shut or bool(row["is_closed"]) or bool(CLOSED_TITLE_RE.match(title or ""))
        days.append(
            {
                "day": row["day"],
                "day_name": labels["days"][row["day"]],
                "is_today": row["day"] == today,
                "closed": closed,
                "title": "" if closed else (title or labels["no_event"]),
                "note": "" if closed else pick(row, lang, "note"),
                # The label is swapped for the closed one, but the raw times stay:
                # a closure is one date, not a change to that weekday's schedule.
                "hours": labels["closed_today"]
                if shut
                else format_hours(row, lang, labels["closed_today"]),
                "open_time": row["open_time"],
                "close_time": row["close_time"],
            }
        )

    return {
        "lang": lang,
        "labels": labels,
        "today": today,
        "today_iso": today_iso,
        "days": days,
        "tonight": next((d for d in days if d["is_today"]), None),
        "closed_days": [
            {"date": d["date"], "reason": pick(d, lang, "reason")}
            for d in closed_days
        ],
        # Handed to the SPA so the first paint needs no fetch.
        "seed": {"schedule": schedule, "closedDays": closed_days},
    }


# --- HTML injection --------------------------------------------------------


def _json_seed(seed: dict) -> str:
    """JSON safe to place inside a ``<script>`` element."""
    return (
        json.dumps(seed, separators=(",", ":"), ensure_ascii=False)
        .replace(JSON_LT, JSON_LT_ESCAPED)
    )


def render_schedule_block(payload: dict) -> str:
    """The crawler-readable schedule markup."""
    return templates.get_template("partials/schedule.html").render(**payload)


def render_schedule_styles() -> str:
    """The ``<style>`` the block needs; the SPA's scoped CSS does not cover it."""
    return templates.get_template("partials/schedule_style.html").render()


def render_index_html(index_html: str, payload: dict) -> str:
    """Inject the schedule styles, markup and data seed into the built index.html."""
    head = index_html.find(HEAD_CLOSE)
    start = index_html.find(APP_MOUNT)
    if head == -1 or start == -1:
        missing = HEAD_CLOSE if head == -1 else APP_MOUNT
        raise RuntimeError(
            f"Could not find {missing!r} in index.html — the server-rendered "
            "schedule cannot be injected, so it must not be served."
        )

    block = render_schedule_block(payload)
    seed = f'<script>window.__MAREA_ALTA_DATA__={_json_seed(payload["seed"])}</script>'
    filled = f'<div id="app">{block}{seed}</div>'

    html = index_html[:start] + filled + index_html[start + len(APP_MOUNT) :]
    # head < start, so inserting into the head cannot invalidate the offset.
    return html[:head] + render_schedule_styles() + html[head:]


def render_index(db: DBSession, lang: str) -> str:
    """Read the built index.html and return it with the schedule rendered in."""
    return render_index_html(INDEX_HTML.read_text(encoding="utf-8"), build_payload(db, lang))