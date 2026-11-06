"""Server-side rendering of the public schedule and menu, for crawlers.

``App.svelte`` fetches ``/api/schedule`` on mount, so the hours, party titles and
closure notices never reach the HTML a crawler sees — and for a bar in a tourist
town that data *is* the search result. This module renders the same week into
``frontend/dist/index.html`` at request time, so the served HTML always carries
the current hours rather than whatever was true when the site was last built.

Two things come out of one pass:

1. A schedule block inside ``<div id="app">`` — plain HTML a crawler (or a
   visitor with JavaScript disabled) can read. The menu block joins it on the
   homepage, and is the whole of ``dist/menu.html``, which ``/menu`` renders the
   same way so the standalone menu route is indexable on equal terms.
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
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.config import BACKEND_DIR
from app.models import (
    ClosedDay,
    ContentItem,
    ContentSection,
    Event,
    Hours,
    MenuCategory,
    MenuItem,
    MenuItemPromo,
    Notice,
    SpecialEvent,
)
from app.public_i18n import strings_for

FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"
MENU_HTML = FRONTEND_DIST / "menu.html"
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


def bar_now(now: datetime | None = None) -> str:
    """The bar's clock as a ``YYYY-MM-DDTHH:MM`` string.

    Notice windows are stored in that shape, which sorts and compares as text.
    ``now`` is injectable for the same reason as :func:`bar_today`.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone(BAR_UTC_OFFSET)).strftime("%Y-%m-%dT%H:%M")


def parse_promo_days(days: str) -> set[int]:
    """Weekday numbers from the stored comma-separated form, 0 = Sunday."""
    return {int(part) for part in (days or "").split(",") if part.strip().isdigit()}


def promo_is_live(promo: MenuItemPromo, now: datetime | None = None) -> bool:
    """True when a promo is switched on and inside its weekday/time/date window.

    Every window is optional, so a promo with nothing set is always live — the
    shape every row had before happy hours existed. The comparison is done in
    Python against the bar clock rather than in SQL, for the same reason as
    :func:`load_notices`: the admin's ``is_live`` and the public filter must
    never disagree.

    A window whose end is before its start crosses midnight, and the whole
    window belongs to the evening it began on. At 01:00 on Saturday, a
    Friday-only 22:00–02:00 offer is live; its weekday and date bounds are
    checked against Friday, not Saturday. This is what makes "Friday happy
    hour" survive into the small hours.
    """
    if not promo.is_active:
        return False

    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(timezone(BAR_UTC_OFFSET))
    today = local.date()
    current = local.strftime("%H:%M")

    start = (promo.start_time or "").strip()
    end = (promo.end_time or "").strip()
    overnight = bool(start and end and start > end)
    effective = today - timedelta(days=1) if overnight and current <= end else today

    if promo.starts_on and effective.isoformat() < promo.starts_on:
        return False
    if promo.ends_on and effective.isoformat() > promo.ends_on:
        return False

    days = parse_promo_days(promo.days)
    if days and ((effective.weekday() + 1) % 7) not in days:
        return False

    if start and end:
        if overnight:
            return current >= start or current <= end
        return start <= current <= end
    return True


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


def load_special_events(
    db: DBSession,
    include_past: bool = False,
    include_inactive: bool = False,
    from_date: str | None = None,
) -> list[dict]:
    """Dated events, soonest first, in the shape ``/api/special-events`` returns.

    The public read drops rows that have already happened and rows an admin has
    switched off; the admin read keeps both so an event can be edited or brought
    back. ``is_past`` is computed against the same bar date the filter uses, so
    the two cannot disagree across the five-hour gap with UTC.

    ``start_time`` sorts as text, which is why it is stored zero-padded. Blank
    times sort first, so an all-day event heads its date rather than trailing it.
    """
    if from_date is None:
        from_date = bar_today()[1]

    query = select(SpecialEvent)
    if not include_past:
        query = query.where(SpecialEvent.date >= from_date)
    if not include_inactive:
        query = query.where(SpecialEvent.is_active.is_(True))
    rows = db.execute(
        query.order_by(
            SpecialEvent.date,
            SpecialEvent.start_time,
            SpecialEvent.id,
        )
    ).scalars().all()
    return [
        {
            "id": row.id,
            "date": row.date,
            "title_en": row.title_en,
            "title_es": row.title_es,
            "description_en": row.description_en,
            "description_es": row.description_es,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "image_url": row.image_url,
            "is_active": bool(row.is_active),
            "is_past": row.date < from_date,
        }
        for row in rows
    ]


def content_item_is_live(item: ContentItem, today: str | None = None) -> bool:
    """True when a content row is switched on and inside its optional date window.

    The window is inclusive at both ends and blank at either end means open. The
    date is the bar's, not the server's, so an item that starts "today" does so
    for the people standing in the bar rather than five hours early.
    """
    if not item.is_active:
        return False
    today = today or bar_today()[1]
    if item.starts_on and today < item.starts_on:
        return False
    if item.ends_on and today > item.ends_on:
        return False
    return True


def load_content(
    db: DBSession,
    include_inactive: bool = False,
    today: str | None = None,
) -> list[dict]:
    """Content sections in order, each with its items, in the API's shape.

    ``include_inactive`` is the public/admin split used by the menu and notices:
    the site gets only live sections and live items, while the panel gets every
    row (plus ``is_live``) so an expired or switched-off item can be edited and
    brought back. A section with no visible items is dropped from the public
    read, because a heading with nothing under it is worse than no heading.
    """
    today = today or bar_today()[1]
    sections = db.execute(
        select(ContentSection).order_by(ContentSection.sort_order, ContentSection.id)
    ).scalars().all()
    items = db.execute(
        select(ContentItem).order_by(ContentItem.sort_order, ContentItem.id)
    ).scalars().all()

    items_by_section: dict[int, list[dict]] = {}
    for item in items:
        live = content_item_is_live(item, today)
        if not include_inactive and not live:
            continue
        items_by_section.setdefault(item.section_id, []).append(
            {
                "id": item.id,
                "section_id": item.section_id,
                "title_en": item.title_en,
                "title_es": item.title_es,
                "body_en": item.body_en,
                "body_es": item.body_es,
                "price": item.price,
                "image_url": item.image_url,
                "starts_on": item.starts_on,
                "ends_on": item.ends_on,
                "sort_order": item.sort_order,
                "is_active": bool(item.is_active),
                "is_live": live,
            }
        )

    result = []
    for section in sections:
        section_items = items_by_section.get(section.id, [])
        if not include_inactive and (not section.is_active or not section_items):
            continue
        result.append(
            {
                "id": section.id,
                "slug": section.slug,
                "title_en": section.title_en,
                "title_es": section.title_es,
                "body_en": section.body_en,
                "body_es": section.body_es,
                "sort_order": section.sort_order,
                "is_active": bool(section.is_active),
                "items": section_items,
            }
        )
    return result


def load_menu(
    db: DBSession,
    include_unavailable: bool = False,
    now: datetime | None = None,
) -> list[dict]:
    """The drinks menu: categories in order, each with its items and promos.

    Shared by ``GET /api/menu`` and by both server-rendered pages, so the crawler
    and the SPA cannot publish different menus.

    ``include_unavailable`` is what the admin panel asks for. The public read
    hides rows an admin has switched off — a sold-out drink or a section that is
    off for the season — but the panel has to be able to see them, or it could
    never switch them back on. Categories with nothing to show are dropped from
    the public read so an emptied section does not linger as a bare heading, and
    kept for the panel, which is the only place anything can be added to one.

    Promos follow the same split: the public read carries only offers that are
    live *now*, while the admin read carries every offer plus ``is_live`` so a
    paused or out-of-season promo stays editable. ``now`` is injectable so tests
    can pin the bar clock, as with :func:`load_notices`.
    """
    categories = db.execute(
        select(MenuCategory).order_by(MenuCategory.sort_order, MenuCategory.id)
    ).scalars().all()
    items = db.execute(
        select(MenuItem).order_by(MenuItem.sort_order, MenuItem.id)
    ).scalars().all()
    promos = db.execute(
        select(MenuItemPromo).order_by(MenuItemPromo.sort_order, MenuItemPromo.id)
    ).scalars().all()

    promos_by_item: dict[int, list[MenuItemPromo]] = {}
    for promo in promos:
        promos_by_item.setdefault(promo.menu_item_id, []).append(promo)

    items_by_category: dict[int, list[dict]] = {}
    for item in items:
        if not include_unavailable and not item.is_available:
            continue

        item_promos = []
        for promo in promos_by_item.get(item.id, []):
            live = promo_is_live(promo, now)
            if not include_unavailable and not live:
                continue
            item_promos.append(
                {
                    "id": promo.id,
                    "label_en": promo.label_en,
                    "label_es": promo.label_es,
                    "days": promo.days,
                    "start_time": promo.start_time,
                    "end_time": promo.end_time,
                    "starts_on": promo.starts_on,
                    "ends_on": promo.ends_on,
                    "is_active": bool(promo.is_active),
                    "is_live": live,
                    "sort_order": promo.sort_order,
                }
            )

        items_by_category.setdefault(item.category_id, []).append(
            {
                "id": item.id,
                "category_id": item.category_id,
                "name_en": item.name_en,
                "name_es": item.name_es,
                "description_en": item.description_en,
                "description_es": item.description_es,
                "ingredients_en": item.ingredients_en,
                "ingredients_es": item.ingredients_es,
                "price": item.price,
                "sort_order": item.sort_order,
                "is_available": bool(item.is_available),
                "is_drink_of_day": bool(item.is_drink_of_day),
                "promos": item_promos,
            }
        )

    menu = []
    for category in categories:
        if not include_unavailable and not category.is_available:
            continue
        category_items = items_by_category.get(category.id, [])
        if not category_items and not include_unavailable:
            continue
        menu.append(
            {
                "id": category.id,
                "slug": category.slug,
                "name_en": category.name_en,
                "name_es": category.name_es,
                "sort_order": category.sort_order,
                "is_available": bool(category.is_available),
                "items": category_items,
            }
        )
    return menu


def load_notices(
    db: DBSession,
    include_inactive: bool = False,
    now: datetime | None = None,
) -> list[dict]:
    """Emergency banners, newest first, with ``is_live`` resolved.

    ``include_inactive`` is the difference between the two reads, exactly as
    ``include_unavailable`` is for the menu: the public site gets only notices
    that are switched on *and* inside their window, while the admin panel gets
    every row so a paused, expired or scheduled notice remains visible and can
    be brought back.

    The window comparison is done here rather than in SQL so the admin's
    ``is_live`` and the public filter can never drift apart.
    """
    now_iso = bar_now(now)
    rows = db.execute(
        select(Notice).order_by(Notice.created_at.desc(), Notice.id.desc())
    ).scalars().all()

    notices = []
    for notice in rows:
        live = bool(notice.is_active) and (
            (not notice.starts_at or notice.starts_at <= now_iso)
            and (not notice.ends_at or notice.ends_at >= now_iso)
        )
        if not include_inactive and not live:
            continue
        notices.append(
            {
                "id": notice.id,
                "message_en": notice.message_en,
                "message_es": notice.message_es,
                "severity": notice.severity,
                "starts_at": notice.starts_at,
                "ends_at": notice.ends_at,
                "is_active": bool(notice.is_active),
                "is_live": live,
            }
        )
    return notices


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


# Short names only, and only for the two languages the site supports: the
# rendered block needs a human date, and pulling in a full locale table for six
# month abbreviations would be the wrong trade.
_WEEKDAYS_SHORT = {
    "en": ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"),
    "es": ("dom", "lun", "mar", "mié", "jue", "vie", "sáb"),
}
_MONTHS_SHORT = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"),
}


def format_event_date(iso: str, lang: str) -> str:
    """``2026-11-06`` as ``Fri 6 Nov`` (or ``vie 6 nov``), or the raw value."""
    try:
        value = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return str(iso or "")

    weekdays = _WEEKDAYS_SHORT.get(lang, _WEEKDAYS_SHORT["en"])
    months = _MONTHS_SHORT.get(lang, _MONTHS_SHORT["en"])
    # Python counts Monday as 0; the site and database count Sunday as 0.
    weekday = weekdays[(value.weekday() + 1) % 7]
    return f"{weekday} {value.day} {months[value.month - 1]}"


def format_event_time(event: dict, lang: str) -> str:
    """An event's optional time range, or blank when it has none."""
    start = format_time(event.get("start_time"), lang)
    end = format_time(event.get("end_time"), lang)
    if start and end:
        return f"{start} - {end}"
    return start


def format_hours(day: dict | None, lang: str, closed_label: str) -> str:
    """An opening-hours range, or the closed label."""
    if not day:
        return ""
    if day.get("is_closed"):
        return closed_label
    if not day.get("open_time") or not day.get("close_time"):
        return ""
    return f"{format_time(day['open_time'], lang)} - {format_time(day['close_time'], lang)}"


def format_price(price: str | None) -> str:
    """A stored price as displayed: ``"2.50"`` -> ``"$2.50"``.

    The amount is kept as the bar typed it rather than parsed into a number, so
    nothing here rounds, and a blank price (an included drink, or one still to be
    priced) renders as nothing instead of "$0.00".
    """
    text = str(price or "").strip()
    return f"${text}" if text else ""


# --- Template payload ------------------------------------------------------


def build_payload(db: DBSession, lang: str) -> dict:
    """Everything the schedule and menu blocks render, resolved for one language.

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

    menu = load_menu(db)
    notices = load_notices(db)
    special_events = load_special_events(db)
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
        "special_events": [
            {
                "id": event["id"],
                "date": event["date"],
                "date_label": format_event_date(event["date"], lang),
                "title": pick(event, lang, "title"),
                "description": pick(event, lang, "description"),
                "time": format_event_time(event, lang),
                "image_url": event["image_url"],
            }
            for event in special_events
        ],
        "menu": menu_display(menu, lang, labels),
        "notices": notice_display(notices, lang),
        # Handed to the SPA so the first paint needs no fetch.
        "seed": {
            "schedule": schedule,
            "closedDays": closed_days,
            "menu": menu,
            "notices": notices,
            "specialEvents": special_events,
        },
    }


def notice_display(notices: list[dict], lang: str) -> list[dict]:
    """The notices resolved for the server-rendered block, one message each."""
    return [
        {
            "id": notice["id"],
            "severity": notice["severity"],
            "message": pick(notice, lang, "message"),
        }
        for notice in notices
    ]


def menu_display(menu: list[dict], lang: str, labels: dict | None = None) -> list[dict]:
    """The menu resolved for one language, ready for the rendered block.

    Mirrors what ``Menu.svelte`` does with the same payload: names and copy
    through :func:`pick`, prices through :func:`format_price`, and each promo
    prefixed with the shared "Promo" label so the crawler-visible text reads the
    same as the page.
    """
    labels = labels or strings_for(lang)
    promo_label = labels.get("menu_promo", "Promo")
    displayed = []
    for category in menu:
        items = []
        for item in category["items"]:
            ingredients = pick(item, lang, "ingredients")
            items.append(
                {
                    "name": pick(item, lang, "name"),
                    "description": pick(item, lang, "description"),
                    "ingredients": [part.strip() for part in ingredients.split(",") if part.strip()],
                    "price": format_price(item["price"]),
                    "promos": [f"{promo_label}: {pick(promo, lang, 'label')}".rstrip(": ")
                               for promo in item["promos"]],
                }
            )
        displayed.append(
            {
                "id": category["id"],
                "slug": category["slug"],
                "name": pick(category, lang, "name"),
                "items": items,
            }
        )
    return displayed


# --- Structured data (ticket #49) -----------------------------------------

# The canonical menu URL and bar name used by the schema.org graph.
MENU_URL = "https://mareaaltabar.com/menu"
SITE_NAME = "Marea Alta Surf Bar"

# A stored price is a displayed amount, not a number: `menu_items.price` is text
# on purpose (no float rounding in the database). JSON-LD is the one consumer
# that needs a machine-readable value, so it is parsed here, once, and anything
# that is not a plain amount is left out rather than advertised as a wrong price.
_PRICE_RE = re.compile(r"^\$?\s*(\d+(?:\.\d{1,2})?)\s*$")


def json_ld_price(price: str | None) -> str | None:
    """Return a two-decimal amount for schema.org, or ``None`` when unparseable.

    ``"2.5"`` becomes ``"2.50"``; ``"ask"`` and ``""`` return ``None``, so the
    item gets no ``offers`` instead of a price of zero.
    """
    match = _PRICE_RE.match(str(price or ""))
    if match is None:
        return None
    try:
        amount = Decimal(match.group(1))
    except InvalidOperation:  # pragma: no cover - the regex already guarantees this
        return None
    return f"{amount:.2f}"


def menu_json_ld(payload: dict) -> dict:
    """A schema.org ``Menu`` built from the same rows the page renders.

    Google reads this to connect a drink name to its price without guessing at
    the markup. It comes from ``payload["seed"]["menu"]`` so the structured data
    and the visible menu cannot disagree — the seed is the loader's output before
    either renderer touches it, and every field is resolved for the page's
    language through :func:`pick`.
    """
    lang = payload["lang"]
    sections = []
    for category in payload["seed"]["menu"]:
        items = []
        for item in category["items"]:
            entry = {
                "@type": "MenuItem",
                "name": pick(item, lang, "name"),
            }
            description = pick(item, lang, "description")
            if description:
                entry["description"] = description

            price = json_ld_price(item.get("price"))
            if price is not None:
                entry["offers"] = {
                    "@type": "Offer",
                    "price": price,
                    "priceCurrency": "USD",
                }
            items.append(entry)

        sections.append(
            {
                "@type": "MenuSection",
                "name": pick(category, lang, "name"),
                "hasMenuItem": items,
            }
        )

    return {
        "@context": "https://schema.org",
        "@type": "Menu",
        "name": SITE_NAME,
        "url": MENU_URL,
        "inLanguage": lang,
        "hasMenuSection": sections,
    }


def render_menu_json_ld(payload: dict, nonce: str) -> str:
    """The ``<script type="application/ld+json">`` block for ``/menu``.

    Escaping goes through the same helper as the data seed: every ``<`` becomes
    ``\\u003c``, which is still valid JSON, so an admin-entered item name cannot
    close the script element early. The nonce is there for the same CSP rule that
    covers every other inline script in the document.
    """
    return (
        f'<script type="application/ld+json" nonce="{nonce}">'
        f"{_json_for_script(menu_json_ld(payload))}"
        "</script>"
    )


# --- HTML injection --------------------------------------------------------


def _json_for_script(value) -> str:
    """JSON safe to place inside a ``<script>`` element."""
    return (
        json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        .replace(JSON_LT, JSON_LT_ESCAPED)
    )


# The saved theme must be on <html> before the first paint, or a visitor who
# chose dark mode sees the light theme until the SPA mounts. The key and the
# fallback match frontend/src/lib/theme.js. The nonce is the request's CSP
# nonce, like every other inline script in the document.
THEME_SCRIPT = """(function () {
  try {
    var saved = localStorage.getItem('theme');
    var dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    var theme = saved === 'dark' || saved === 'light' ? saved : (dark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#0d1a1d' : '#0b3c49');
  } catch (e) {}
})();"""


def render_theme_script(nonce: str) -> str:
    """The head script that applies the saved (or system) theme before paint."""
    return f'<script nonce="{nonce}">{THEME_SCRIPT}</script>'


def _json_seed(seed: dict) -> str:
    """The page's data seed, escaped for its ``<script>`` element."""
    return _json_for_script(seed)


def render_schedule_block(payload: dict) -> str:
    """The crawler-readable schedule markup."""
    return templates.get_template("partials/schedule.html").render(**payload)


def render_notice_block(payload: dict) -> str:
    """The crawler-readable emergency banner, if any notice is live."""
    return templates.get_template("partials/notice.html").render(**payload)


def render_menu_block(payload: dict) -> str:
    """The crawler-readable menu markup, shared by the homepage and /menu."""
    return templates.get_template("partials/menu.html").render(**payload)


def render_schedule_styles() -> str:
    """The ``<style>`` the block needs; the SPA's scoped CSS does not cover it."""
    return templates.get_template("partials/schedule_style.html").render()


def render_notice_styles() -> str:
    """Same, for the emergency banner."""
    return templates.get_template("partials/notice_style.html").render()


def render_menu_styles() -> str:
    """Same, for the menu block."""
    return templates.get_template("partials/menu_style.html").render()


def _inject(
    html: str,
    payload: dict,
    blocks: list[str],
    styles: str,
    name: str,
    nonce: str,
    head_extra: str = "",
) -> str:
    """Put rendered blocks and the data seed inside ``<div id="app">``.

    Shared by the homepage and ``/menu`` so both documents are assembled the same
    way: find the mount point, drop the blocks in ahead of the seed script, and
    put their styles in the head. ``head_extra`` carries document-level metadata
    that has to sit in the head, currently the menu's JSON-LD. ``nonce`` is the
    request's CSP nonce: every inline ``<script>`` this function emits must carry
    it or the browser refuses to run the seed.
    """
    head = html.find(HEAD_CLOSE)
    start = html.find(APP_MOUNT)
    if head == -1 or start == -1:
        missing = HEAD_CLOSE if head == -1 else APP_MOUNT
        raise RuntimeError(
            f"Could not find {missing!r} in {name} — the server-rendered content "
            "cannot be injected, so it must not be served."
        )

    seed = (
        f'<script nonce="{nonce}">'
        f"window.__MAREA_ALTA_DATA__={_json_seed(payload['seed'])}</script>"
    )
    filled = f'<div id="app">{"".join(blocks)}{seed}</div>'

    html = html[:start] + filled + html[start + len(APP_MOUNT) :]
    # head < start, so inserting into the head cannot invalidate the offset. The
    # theme script comes first so data-theme is set before any styled content.
    return (
        html[:head]
        + render_theme_script(nonce)
        + styles
        + head_extra
        + html[head:]
    )


def render_index_html(index_html: str, payload: dict, nonce: str) -> str:
    """Inject the notice, schedule and menu blocks, styles and data seed."""
    return _inject(
        index_html,
        payload,
        [
            render_notice_block(payload),
            render_schedule_block(payload),
            render_menu_block(payload),
        ],
        render_notice_styles() + render_schedule_styles() + render_menu_styles(),
        "index.html",
        nonce,
    )


def render_menu_html(menu_html: str, payload: dict, nonce: str) -> str:
    """The same treatment for the standalone menu document, minus the schedule.

    This is the page that carries the ``Menu`` JSON-LD: it is the dedicated,
    canonical URL for the drinks list, so the structured data describes exactly
    the menu a visitor sees there.
    """
    return _inject(
        menu_html,
        payload,
        [render_notice_block(payload), render_menu_block(payload)],
        render_notice_styles() + render_menu_styles(),
        "menu.html",
        nonce,
        render_menu_json_ld(payload, nonce),
    )


def render_index(db: DBSession, lang: str, nonce: str) -> str:
    """Read the built index.html and return it with the schedule and menu rendered in."""
    return render_index_html(
        INDEX_HTML.read_text(encoding="utf-8"), build_payload(db, lang), nonce
    )


def render_menu(db: DBSession, lang: str, nonce: str) -> str:
    """Read the built menu.html and return it with the menu rendered in."""
    return render_menu_html(
        MENU_HTML.read_text(encoding="utf-8"), build_payload(db, lang), nonce
    )