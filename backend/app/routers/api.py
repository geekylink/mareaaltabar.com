"""JSON API for the weekly schedule and the drinks menu.

``/api/schedule`` merges the event and its opening hours into a single resource
per weekday, so an admin edits a day's description and its times in one place
and saves them atomically. ``/api/menu`` does the same job for drinks: one
category with its items, each with its multi-buy promos.

Read endpoints are public (the website needs them). Writes require an
authenticated admin session plus a CSRF token.

Every write also writes a log row through :mod:`app.audit`, in the same
transaction as the change itself. That is why each handler below takes a
``change_author`` and compares the row before and after: the log is only useful
if it says what actually changed, and only trustworthy if it cannot be skipped.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app import audit
from app.audit import ChangeAuthor
from app.database import get_db
from app.dependencies import change_author, csrf_protect, get_current_admin
from app.models import ClosedDay, Event, Hours, MenuCategory, MenuItem, MenuItemPromo
from app.schemas import (
    ClosedDayCreate,
    ClosedDayResponse,
    ClosedDayUpdate,
    DayScheduleResponse,
    DayScheduleUpdate,
    MenuCategoryResponse,
    MenuCategoryWrite,
    MenuItemResponse,
    MenuItemWrite,
    MenuResponse,
)
from app.ssr import day_payload, load_closed_days, load_menu, load_schedule

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

# Revalidate so admin edits appear without visitors hard-refreshing.
READ_CACHE_CONTROL = {"Cache-Control": "no-cache"}

# The fields each write logs a diff of. A field left out of these tuples is a
# field nobody can find out about later.
EVENT_FIELDS = ("title_en", "title_es", "note_en", "note_es")
HOURS_FIELDS = ("open_time", "close_time", "is_closed")
CLOSED_DAY_FIELDS = ("date", "reason_en", "reason_es")
CATEGORY_FIELDS = ("slug", "name_en", "name_es", "sort_order", "is_available")
ITEM_FIELDS = (
    "category_id",
    "name_en",
    "name_es",
    "description_en",
    "description_es",
    "ingredients_en",
    "ingredients_es",
    "price",
    "sort_order",
    "is_available",
)


def _display_name(name_en: str, name_es: str) -> str:
    """A row's name for the log, English first with the Spanish as the fallback.

    Content is shown in the log exactly as it was entered — it is data, not UI
    text — so this picks the language that is most likely to be filled in.
    """
    return (name_en or "").strip() or (name_es or "").strip()


def _item_fields(item: MenuItem) -> dict:
    """A drink's logged fields, with its promos folded into one list.

    Saving a drink replaces its whole promo set, so the old rows are gone by the
    time anyone reads the log. Logging the list as it stood before and after is
    the only way "the 6-for-7 offer came off" survives as a record.
    """
    fields = audit.snapshot(item, ITEM_FIELDS)
    fields["promos"] = [
        {"label_en": promo.label_en, "label_es": promo.label_es} for promo in item.promos
    ]
    return fields


# --- Weekly schedule ---

@router.get("/api/schedule", response_model=list[DayScheduleResponse])
async def get_schedule(response: Response, db: DBSession = Depends(get_db)):
    """Public: the full week, both languages, ready for the visitor's locale."""
    response.headers.update(READ_CACHE_CONTROL)
    return load_schedule(db)


@router.put("/api/schedule/{day}", response_model=DayScheduleResponse, dependencies=write_guard)
async def update_day(
    day: int,
    data: DayScheduleUpdate,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: save a day's titles, descriptions and hours together."""
    if day < 0 or day > 6:
        raise HTTPException(status_code=400, detail="Day must be 0-6")

    event = db.execute(select(Event).where(Event.day == day)).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Day not found")

    hours = db.execute(select(Hours).where(Hours.day == day)).scalar_one_or_none()
    hours_existed = hours is not None
    if hours is None:
        hours = Hours(day=day)
        db.add(hours)

    # A day's log line is one entry covering both rows: they are saved together
    # and describe one thing. On the rare occasion a day has no hours row yet the
    # "before" side is empty, which reads as the hours having been added.
    before = {
        **audit.snapshot(event, EVENT_FIELDS),
        **(audit.snapshot(hours, HOURS_FIELDS) if hours_existed else {}),
    }

    event.title_en = data.title_en
    event.title_es = data.title_es
    event.note_en = data.note_en
    event.note_es = data.note_es

    hours.open_time = data.open_time
    hours.close_time = data.close_time
    hours.is_closed = data.is_closed

    after = {
        **audit.snapshot(event, EVENT_FIELDS),
        **audit.snapshot(hours, HOURS_FIELDS),
    }

    audit.log_change(
        db,
        area=audit.AREA_SCHEDULE,
        action=audit.ACTION_UPDATE,
        author=author,
        target=audit.format_target(audit.TARGET_SCHEDULE_DAY, day),
        details=audit.diff(before, after),
    )

    db.commit()
    db.refresh(event)
    db.refresh(hours)
    return day_payload(event, hours)


# --- Closed days (bilingual reason) ---

@router.get("/api/closed-days", response_model=list[ClosedDayResponse])
async def list_closed_days(response: Response, db: DBSession = Depends(get_db)):
    """Public: one-off date closures (holidays, private events), today and later.

    ``load_closed_days`` drops rows that have already passed, at the bar's clock
    rather than the server's, so a closure stops being published the day after it
    happens. Past rows stay in ``closed_days`` — they are simply never returned,
    which also means the admin panel's list no longer shows them.
    """
    response.headers.update(READ_CACHE_CONTROL)
    return load_closed_days(db)


@router.post(
    "/api/closed-days",
    response_model=ClosedDayResponse,
    status_code=201,
    dependencies=write_guard,
)
async def create_closed_day(
    data: ClosedDayCreate,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: add a one-off closure with a reason in both languages."""
    iso_date = data.date.isoformat()

    existing = db.execute(select(ClosedDay).where(ClosedDay.date == iso_date)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Closed day already exists for this date")

    closed_day = ClosedDay(
        date=iso_date,
        reason_en=data.reason_en,
        reason_es=data.reason_es,
    )
    db.add(closed_day)

    # The closure is named by its date, not its id, so no flush is needed here —
    # the log row and the closure are published by the one commit below.
    audit.log_change(
        db,
        area=audit.AREA_SCHEDULE,
        action=audit.ACTION_CREATE,
        author=author,
        target=audit.format_target(audit.TARGET_CLOSED_DAY, iso_date),
        target_name=_display_name(data.reason_en, data.reason_es),
        details=audit.snapshot(closed_day, CLOSED_DAY_FIELDS),
    )

    db.commit()
    db.refresh(closed_day)
    return ClosedDayResponse(
        id=closed_day.id,
        date=closed_day.date,
        reason_en=closed_day.reason_en,
        reason_es=closed_day.reason_es,
    )


@router.patch(
    "/api/closed-days/{closed_day_id}",
    response_model=ClosedDayResponse,
    dependencies=write_guard,
)
async def update_closed_day(
    closed_day_id: int,
    data: ClosedDayUpdate,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: correct the wording of a closure after the fact."""
    closed_day = db.execute(
        select(ClosedDay).where(ClosedDay.id == closed_day_id)
    ).scalar_one_or_none()
    if closed_day is None:
        raise HTTPException(status_code=404, detail="Closed day not found")

    before = audit.snapshot(closed_day, CLOSED_DAY_FIELDS)

    closed_day.reason_en = data.reason_en
    closed_day.reason_es = data.reason_es

    audit.log_change(
        db,
        area=audit.AREA_SCHEDULE,
        action=audit.ACTION_UPDATE,
        author=author,
        target=audit.format_target(audit.TARGET_CLOSED_DAY, closed_day.date),
        target_name=_display_name(closed_day.reason_en, closed_day.reason_es),
        details=audit.diff(before, audit.snapshot(closed_day, CLOSED_DAY_FIELDS)),
    )

    db.commit()
    db.refresh(closed_day)
    return ClosedDayResponse(
        id=closed_day.id,
        date=closed_day.date,
        reason_en=closed_day.reason_en,
        reason_es=closed_day.reason_es,
    )


@router.delete("/api/closed-days/{closed_day_id}", status_code=204, dependencies=write_guard)
async def delete_closed_day(
    closed_day_id: int,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: remove a one-off closure."""
    closed_day = db.execute(
        select(ClosedDay).where(ClosedDay.id == closed_day_id)
    ).scalar_one_or_none()
    if closed_day is None:
        raise HTTPException(status_code=404, detail="Closed day not found")

    audit.log_change(
        db,
        area=audit.AREA_SCHEDULE,
        action=audit.ACTION_DELETE,
        author=author,
        target=audit.format_target(audit.TARGET_CLOSED_DAY, closed_day.date),
        target_name=_display_name(closed_day.reason_en, closed_day.reason_es),
        details=audit.snapshot(closed_day, CLOSED_DAY_FIELDS),
    )

    db.delete(closed_day)
    db.commit()


# --- Drinks menu ---
#
# Reads go through `load_menu`, the same loader the server-rendered pages use, so
# the crawler-visible HTML and this endpoint cannot publish different menus.
# `include_unavailable` is the difference between the two reads: the public one
# drops anything an admin has switched off, the admin one keeps it so it can be
# switched back on.

def _menu_responses(db: DBSession, include_unavailable: bool = False) -> list[MenuCategoryResponse]:
    """The menu as response models, in display order."""
    return [
        MenuCategoryResponse(
            id=category["id"],
            slug=category["slug"],
            name_en=category["name_en"],
            name_es=category["name_es"],
            sort_order=category["sort_order"],
            is_available=category["is_available"],
            items=[MenuItemResponse(**item) for item in category["items"]],
        )
        for category in load_menu(db, include_unavailable)
    ]


def _item_response(item: MenuItem) -> MenuItemResponse:
    """One saved drink, for the response to a write."""
    return MenuItemResponse(
        id=item.id,
        category_id=item.category_id,
        name_en=item.name_en,
        name_es=item.name_es,
        description_en=item.description_en,
        description_es=item.description_es,
        ingredients_en=item.ingredients_en,
        ingredients_es=item.ingredients_es,
        price=item.price,
        sort_order=item.sort_order,
        is_available=bool(item.is_available),
        promos=[
            {
                "id": promo.id,
                "label_en": promo.label_en,
                "label_es": promo.label_es,
                "sort_order": promo.sort_order,
            }
            for promo in item.promos
        ],
    )


def _category_response(
    category: MenuCategory, items: list[MenuItem] | None = None
) -> MenuCategoryResponse:
    """One saved category with its drinks, in display order."""
    rows = category.items if items is None else items
    return MenuCategoryResponse(
        id=category.id,
        slug=category.slug,
        name_en=category.name_en,
        name_es=category.name_es,
        sort_order=category.sort_order,
        is_available=bool(category.is_available),
        items=[_item_response(item) for item in rows],
    )


@router.get("/api/menu", response_model=MenuResponse)
async def get_menu(response: Response, db: DBSession = Depends(get_db)):
    """Public: every drink currently on offer, both languages, in order."""
    response.headers.update(READ_CACHE_CONTROL)
    return MenuResponse(categories=_menu_responses(db))


@router.get(
    "/api/menu/all",
    response_model=MenuResponse,
    dependencies=[Depends(get_current_admin)],
)
async def get_menu_including_unavailable(
    response: Response, db: DBSession = Depends(get_db)
):
    """Admin: the same menu plus unavailable items and empty categories.

    The panel loads from here rather than the public read, because a sold-out
    drink hidden from `/api/menu` would otherwise be invisible in the panel too —
    with no way to bring it back except by guessing its id.
    """
    response.headers.update(READ_CACHE_CONTROL)
    return MenuResponse(categories=_menu_responses(db, include_unavailable=True))


@router.post(
    "/api/menu/categories",
    response_model=MenuCategoryResponse,
    status_code=201,
    dependencies=write_guard,
)
async def create_menu_category(
    data: MenuCategoryWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: add a section — Beer, Wine, Cocktails, a food menu later."""
    if db.execute(select(MenuCategory).where(MenuCategory.slug == data.slug)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A category with this slug already exists")

    # New sections go to the end of the menu rather than jumping to the top.
    last = db.execute(select(MenuCategory.sort_order).order_by(MenuCategory.sort_order.desc())).first()
    category = MenuCategory(
        slug=data.slug,
        name_en=data.name_en,
        name_es=data.name_es,
        sort_order=(last[0] + 1) if last else 0,
        is_available=data.is_available,
    )
    db.add(category)

    # Flushed first so the log can name the section by its id, not just its title.
    db.flush()

    audit.log_change(
        db,
        area=audit.AREA_MENU,
        action=audit.ACTION_CREATE,
        author=author,
        target=audit.format_target(audit.TARGET_MENU_CATEGORY, category.id),
        target_name=_display_name(category.name_en, category.name_es),
        details=audit.snapshot(category, CATEGORY_FIELDS),
    )

    db.commit()
    db.refresh(category)
    return _category_response(category, [])


@router.patch(
    "/api/menu/categories/{category_id}",
    response_model=MenuCategoryResponse,
    dependencies=write_guard,
)
async def update_menu_category(
    category_id: int,
    data: MenuCategoryWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: rename a section, retitle it, or take it off the menu for now."""
    category = db.execute(
        select(MenuCategory).where(MenuCategory.id == category_id)
    ).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    if data.slug != category.slug:
        clash = db.execute(
            select(MenuCategory).where(MenuCategory.slug == data.slug)
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(status_code=409, detail="A category with this slug already exists")

    before = audit.snapshot(category, CATEGORY_FIELDS)

    category.slug = data.slug
    category.name_en = data.name_en
    category.name_es = data.name_es
    category.is_available = data.is_available
    if data.sort_order is not None:
        category.sort_order = data.sort_order

    audit.log_change(
        db,
        area=audit.AREA_MENU,
        action=audit.ACTION_UPDATE,
        author=author,
        target=audit.format_target(audit.TARGET_MENU_CATEGORY, category.id),
        target_name=_display_name(category.name_en, category.name_es),
        details=audit.diff(before, audit.snapshot(category, CATEGORY_FIELDS)),
    )

    db.commit()
    db.refresh(category)
    return _category_response(category)


@router.delete("/api/menu/categories/{category_id}", status_code=204, dependencies=write_guard)
async def delete_menu_category(
    category_id: int,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: remove a section and every drink in it.

    Deleting rather than switching off is destructive, so the panel confirms
    first. Switching ``is_available`` off is the reversible version of this.
    """
    category = db.execute(
        select(MenuCategory).where(MenuCategory.id == category_id)
    ).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    # `MenuCategory.items` cascades, and each item cascades to its promos.
    details = audit.snapshot(category, CATEGORY_FIELDS)
    # The drinks going with it are the part that cannot be recovered afterwards,
    # so how many went is in the log even though the rows themselves are not.
    details["items_removed"] = len(category.items)

    audit.log_change(
        db,
        area=audit.AREA_MENU,
        action=audit.ACTION_DELETE,
        author=author,
        target=audit.format_target(audit.TARGET_MENU_CATEGORY, category.id),
        target_name=_display_name(category.name_en, category.name_es),
        details=details,
    )

    db.delete(category)
    db.commit()


def _get_category(db: DBSession, category_id: int) -> MenuCategory:
    category = db.execute(
        select(MenuCategory).where(MenuCategory.id == category_id)
    ).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=400, detail="Category not found")
    return category


def _get_item(db: DBSession, item_id: int) -> MenuItem:
    item = db.execute(select(MenuItem).where(MenuItem.id == item_id)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def _apply_promos(item: MenuItem, promos: list) -> None:
    """Replace an item's promos with exactly the list that was submitted.

    The write payload carries the whole set rather than a delta, so adding and
    removing promo rows in the panel is the same save as editing the price, and
    the two can never disagree about what the item offers.
    """
    item.promos.clear()  # delete-orphan cascade removes the old rows
    for order, promo in enumerate(promos):
        item.promos.append(
            MenuItemPromo(
                label_en=promo.label_en,
                label_es=promo.label_es,
                sort_order=order,
            )
        )


@router.post(
    "/api/menu/items",
    response_model=MenuItemResponse,
    status_code=201,
    dependencies=write_guard,
)
async def create_menu_item(
    data: MenuItemWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: add a drink, with its promos, to a category."""
    category = _get_category(db, data.category_id)

    # New drinks land at the end of their section.
    last = db.execute(
        select(MenuItem.sort_order)
        .where(MenuItem.category_id == category.id)
        .order_by(MenuItem.sort_order.desc())
    ).first()

    item = MenuItem(
        category_id=category.id,
        name_en=data.name_en,
        name_es=data.name_es,
        description_en=data.description_en,
        description_es=data.description_es,
        ingredients_en=data.ingredients_en,
        ingredients_es=data.ingredients_es,
        price=data.price,
        sort_order=(last[0] + 1) if last else 0,
        is_available=data.is_available,
    )
    _apply_promos(item, data.promos)
    db.add(item)

    # Flushed first so the log can name the drink by its id, and so the promos
    # have their rows before the snapshot below reads them back.
    db.flush()

    audit.log_change(
        db,
        area=audit.AREA_MENU,
        action=audit.ACTION_CREATE,
        author=author,
        target=audit.format_target(audit.TARGET_MENU_ITEM, item.id),
        target_name=_display_name(item.name_en, item.name_es),
        details=_item_fields(item),
    )

    db.commit()
    db.refresh(item)
    return _item_response(item)


@router.put("/api/menu/items/{item_id}", response_model=MenuItemResponse, dependencies=write_guard)
async def update_menu_item(
    item_id: int,
    data: MenuItemWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: save a drink — copy, price, ingredients, promos and availability.

    A full save rather than a patch, so a drink can be moved to another section
    in the same request. Promos are replaced by the submitted list.
    """
    item = _get_item(db, item_id)
    _get_category(db, data.category_id)

    before = _item_fields(item)

    item.category_id = data.category_id
    item.name_en = data.name_en
    item.name_es = data.name_es
    item.description_en = data.description_en
    item.description_es = data.description_es
    item.ingredients_en = data.ingredients_en
    item.ingredients_es = data.ingredients_es
    item.price = data.price
    item.is_available = data.is_available
    if data.sort_order is not None:
        item.sort_order = data.sort_order
    _apply_promos(item, data.promos)

    audit.log_change(
        db,
        area=audit.AREA_MENU,
        action=audit.ACTION_UPDATE,
        author=author,
        target=audit.format_target(audit.TARGET_MENU_ITEM, item.id),
        target_name=_display_name(item.name_en, item.name_es),
        # Read back after the promos were replaced, so the diff shows the set the
        # save actually produced against the one that was there before.
        details=audit.diff(before, _item_fields(item)),
    )

    db.commit()
    db.refresh(item)
    return _item_response(item)


@router.delete("/api/menu/items/{item_id}", status_code=204, dependencies=write_guard)
async def delete_menu_item(
    item_id: int,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: take a drink off the menu. Its promos go with it."""
    item = _get_item(db, item_id)

    audit.log_change(
        db,
        area=audit.AREA_MENU,
        action=audit.ACTION_DELETE,
        author=author,
        target=audit.format_target(audit.TARGET_MENU_ITEM, item.id),
        target_name=_display_name(item.name_en, item.name_es),
        details=_item_fields(item),
    )

    db.delete(item)
    db.commit()