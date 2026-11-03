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
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.config import BACKEND_DIR
from app.models import ClosedDay, Event, Hours, MenuCategory, MenuItem, MenuItemPromo
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


def load_menu(db: DBSession, include_unavailable: bool = False) -> list[dict]:
    """The drinks menu: categories in order, each with its items and promos.

    Shared by ``GET /api/menu`` and by both server-rendered pages, so the crawler
    and the SPA cannot publish different menus.

    ``include_unavailable`` is what the admin panel asks for. The public read
    hides rows an admin has switched off — a sold-out drink or a section that is
    off for the season — but the panel has to be able to see them, or it could
    never switch them back on. Categories with nothing to show are dropped from
    the public read so an emptied section does not linger as a bare heading, and
    kept for the panel, which is the only place anything can be added to one.
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
                "promos": [
                    {
                        "id": promo.id,
                        "label_en": promo.label_en,
                        "label_es": promo.label_es,
                        "sort_order": promo.sort_order,
                    }
                    for promo in promos_by_item.get(item.id, [])
                ],
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
        "menu": menu_display(menu, lang, labels),
        # Handed to the SPA so the first paint needs no fetch.
        "seed": {"schedule": schedule, "closedDays": closed_days, "menu": menu},
    }


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


def render_menu_json_ld(payload: dict) -> str:
    """The ``<script type="application/ld+json">`` block for ``/menu``.

    Escaping goes through the same helper as the data seed: every ``<`` becomes
    ``\\u003c``, which is still valid JSON, so an admin-entered item name cannot
    close the script element early.
    """
    return (
        '<script type="application/ld+json">'
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


def _json_seed(seed: dict) -> str:
    """The page's data seed, escaped for its ``<script>`` element."""
    return _json_for_script(seed)


def render_schedule_block(payload: dict) -> str:
    """The crawler-readable schedule markup."""
    return templates.get_template("partials/schedule.html").render(**payload)


def render_menu_block(payload: dict) -> str:
    """The crawler-readable menu markup, shared by the homepage and /menu."""
    return templates.get_template("partials/menu.html").render(**payload)


def render_schedule_styles() -> str:
    """The ``<style>`` the block needs; the SPA's scoped CSS does not cover it."""
    return templates.get_template("partials/schedule_style.html").render()


def render_menu_styles() -> str:
    """Same, for the menu block."""
    return templates.get_template("partials/menu_style.html").render()


def _inject(
    html: str,
    payload: dict,
    blocks: list[str],
    styles: str,
    name: str,
    head_extra: str = "",
) -> str:
    """Put rendered blocks and the data seed inside ``<div id="app">``.

    Shared by the homepage and ``/menu`` so both documents are assembled the same
    way: find the mount point, drop the blocks in ahead of the seed script, and
    put their styles in the head. ``head_extra`` carries document-level metadata
    that has to sit in the head, currently the menu's JSON-LD.
    """
    head = html.find(HEAD_CLOSE)
    start = html.find(APP_MOUNT)
    if head == -1 or start == -1:
        missing = HEAD_CLOSE if head == -1 else APP_MOUNT
        raise RuntimeError(
            f"Could not find {missing!r} in {name} — the server-rendered content "
            "cannot be injected, so it must not be served."
        )

    seed = f'<script>window.__MAREA_ALTA_DATA__={_json_seed(payload["seed"])}</script>'
    filled = f'<div id="app">{"".join(blocks)}{seed}</div>'

    html = html[:start] + filled + html[start + len(APP_MOUNT) :]
    # head < start, so inserting into the head cannot invalidate the offset.
    return html[:head] + styles + head_extra + html[head:]


def render_index_html(index_html: str, payload: dict) -> str:
    """Inject the schedule and menu blocks, styles and data seed into index.html."""
    return _inject(
        index_html,
        payload,
        [render_schedule_block(payload), render_menu_block(payload)],
        render_schedule_styles() + render_menu_styles(),
        "index.html",
    )


def render_menu_html(menu_html: str, payload: dict) -> str:
    """The same treatment for the standalone menu document, minus the schedule.

    This is the page that carries the ``Menu`` JSON-LD: it is the dedicated,
    canonical URL for the drinks list, so the structured data describes exactly
    the menu a visitor sees there.
    """
    return _inject(
        menu_html,
        payload,
        [render_menu_block(payload)],
        render_menu_styles(),
        "menu.html",
        render_menu_json_ld(payload),
    )


def render_index(db: DBSession, lang: str) -> str:
    """Read the built index.html and return it with the schedule and menu rendered in."""
    return render_index_html(INDEX_HTML.read_text(encoding="utf-8"), build_payload(db, lang))


def render_menu(db: DBSession, lang: str) -> str:
    """Read the built menu.html and return it with the menu rendered in."""
    return render_menu_html(MENU_HTML.read_text(encoding="utf-8"), build_payload(db, lang))