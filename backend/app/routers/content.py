"""Generic content sections and items (ticket #17).

The site already has one editable content pattern: the menu. This is the same
idea without the drinks-specific fields, so the About box, the package lists and
a future gallery can be filled in from the panel rather than from a deploy.

Reads follow the split used everywhere else: ``GET /api/content`` returns only
live sections and live items (the site needs those), while
``GET /api/content/all`` is session-guarded and returns every row so an expired
or switched-off item stays editable. Writes are admin + CSRF and every one is
written to the content area of the audit log in the same transaction.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app import audit
from app.audit import ChangeAuthor
from app.database import get_db
from app.dependencies import change_author, csrf_protect, get_current_admin
from app.models import ContentItem, ContentSection
from app.schemas import (
    ContentItemResponse,
    ContentItemWrite,
    ContentSectionResponse,
    ContentSectionWrite,
)
from app.ssr import load_content

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

READ_CACHE_CONTROL = {"Cache-Control": "no-cache"}

SECTION_FIELDS = ("slug", "title_en", "title_es", "body_en", "body_es", "sort_order", "is_active")
ITEM_FIELDS = (
    "section_id",
    "title_en",
    "title_es",
    "body_en",
    "body_es",
    "price",
    "image_url",
    "starts_on",
    "ends_on",
    "sort_order",
    "is_active",
)


def _display_name(name_en: str, name_es: str) -> str:
    return (name_en or "").strip() or (name_es or "").strip()


def _item_response(item: ContentItem) -> ContentItemResponse:
    return ContentItemResponse(
        id=item.id,
        section_id=item.section_id,
        title_en=item.title_en,
        title_es=item.title_es,
        body_en=item.body_en,
        body_es=item.body_es,
        price=item.price,
        image_url=item.image_url,
        starts_on=item.starts_on,
        ends_on=item.ends_on,
        sort_order=item.sort_order,
        is_active=bool(item.is_active),
        is_live=True,
    )


def _section_response(section: ContentSection, items: list[ContentItem] | None = None) -> ContentSectionResponse:
    rows = section.items if items is None else items
    return ContentSectionResponse(
        id=section.id,
        slug=section.slug,
        title_en=section.title_en,
        title_es=section.title_es,
        body_en=section.body_en,
        body_es=section.body_es,
        sort_order=section.sort_order,
        is_active=bool(section.is_active),
        items=[_item_response(item) for item in rows],
    )


def _get_section(db: DBSession, section_id: int) -> ContentSection:
    section = db.get(ContentSection, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


def _get_item(db: DBSession, item_id: int) -> ContentItem:
    item = db.get(ContentItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


# --- Public reads ----------------------------------------------------------


@router.get("/api/content", response_model=list[ContentSectionResponse])
async def list_content(response: Response, db: DBSession = Depends(get_db)):
    """Public: live sections in order, each with its live items."""
    response.headers.update(READ_CACHE_CONTROL)
    return [ContentSectionResponse(**section) for section in load_content(db)]


@router.get(
    "/api/content/all",
    response_model=list[ContentSectionResponse],
    dependencies=[Depends(get_current_admin)],
)
async def list_all_content(response: Response, db: DBSession = Depends(get_db)):
    """Admin: every section and item, including switched-off and expired rows."""
    response.headers.update(READ_CACHE_CONTROL)
    return [ContentSectionResponse(**section) for section in load_content(db, include_inactive=True)]


@router.get("/api/content/{slug}", response_model=ContentSectionResponse)
async def get_content_section(slug: str, response: Response, db: DBSession = Depends(get_db)):
    """Public: one live section by slug, for a page or component that asks for it."""
    response.headers.update(READ_CACHE_CONTROL)
    for section in load_content(db):
        if section["slug"] == slug:
            return ContentSectionResponse(**section)
    raise HTTPException(status_code=404, detail="Section not found")


# --- Section writes --------------------------------------------------------


@router.post(
    "/api/content/sections",
    response_model=ContentSectionResponse,
    status_code=201,
    dependencies=write_guard,
)
async def create_content_section(
    data: ContentSectionWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: add a content section."""
    if db.execute(select(ContentSection).where(ContentSection.slug == data.slug)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A section with this slug already exists")

    last = db.execute(
        select(ContentSection.sort_order).order_by(ContentSection.sort_order.desc())
    ).first()
    section = ContentSection(
        slug=data.slug,
        title_en=data.title_en,
        title_es=data.title_es,
        body_en=data.body_en,
        body_es=data.body_es,
        sort_order=data.sort_order if data.sort_order is not None else ((last[0] + 1) if last else 0),
        is_active=data.is_active,
    )
    db.add(section)
    db.flush()

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_CREATE,
        author=author,
        target=audit.format_target(audit.TARGET_CONTENT_SECTION, section.id),
        target_name=_display_name(section.title_en, section.title_es),
        details=audit.snapshot(section, SECTION_FIELDS),
    )

    db.commit()
    db.refresh(section)
    return _section_response(section, [])


@router.put(
    "/api/content/sections/{section_id}",
    response_model=ContentSectionResponse,
    dependencies=write_guard,
)
async def update_content_section(
    section_id: int,
    data: ContentSectionWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: edit a section, including its slug and active flag."""
    section = _get_section(db, section_id)

    if data.slug != section.slug:
        clash = db.execute(
            select(ContentSection).where(ContentSection.slug == data.slug)
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(status_code=409, detail="A section with this slug already exists")

    before = audit.snapshot(section, SECTION_FIELDS)

    section.slug = data.slug
    section.title_en = data.title_en
    section.title_es = data.title_es
    section.body_en = data.body_en
    section.body_es = data.body_es
    section.is_active = data.is_active
    if data.sort_order is not None:
        section.sort_order = data.sort_order

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_UPDATE,
        author=author,
        target=audit.format_target(audit.TARGET_CONTENT_SECTION, section.id),
        target_name=_display_name(section.title_en, section.title_es),
        details=audit.diff(before, audit.snapshot(section, SECTION_FIELDS)),
    )

    db.commit()
    db.refresh(section)
    return _section_response(section)


@router.delete("/api/content/sections/{section_id}", status_code=204, dependencies=write_guard)
async def delete_content_section(
    section_id: int,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: remove a section and every item in it."""
    section = _get_section(db, section_id)

    details = audit.snapshot(section, SECTION_FIELDS)
    details["items_removed"] = len(section.items)

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_DELETE,
        author=author,
        target=audit.format_target(audit.TARGET_CONTENT_SECTION, section.id),
        target_name=_display_name(section.title_en, section.title_es),
        details=details,
    )

    db.delete(section)
    db.commit()


# --- Item writes -----------------------------------------------------------


@router.post(
    "/api/content/items",
    response_model=ContentItemResponse,
    status_code=201,
    dependencies=write_guard,
)
async def create_content_item(
    data: ContentItemWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: add a row to a section."""
    _get_section(db, data.section_id)

    last = db.execute(
        select(ContentItem.sort_order)
        .where(ContentItem.section_id == data.section_id)
        .order_by(ContentItem.sort_order.desc())
    ).first()

    item = ContentItem(
        section_id=data.section_id,
        title_en=data.title_en,
        title_es=data.title_es,
        body_en=data.body_en,
        body_es=data.body_es,
        price=data.price,
        image_url=data.image_url,
        starts_on=data.starts_on,
        ends_on=data.ends_on,
        sort_order=data.sort_order if data.sort_order is not None else ((last[0] + 1) if last else 0),
        is_active=data.is_active,
    )
    db.add(item)
    db.flush()

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_CREATE,
        author=author,
        target=audit.format_target(audit.TARGET_CONTENT_ITEM, item.id),
        target_name=_display_name(item.title_en, item.title_es),
        details=audit.snapshot(item, ITEM_FIELDS),
    )

    db.commit()
    db.refresh(item)
    return _item_response(item)


@router.put(
    "/api/content/items/{item_id}",
    response_model=ContentItemResponse,
    dependencies=write_guard,
)
async def update_content_item(
    item_id: int,
    data: ContentItemWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: edit an item, including moving it to another section."""
    item = _get_item(db, item_id)
    _get_section(db, data.section_id)

    before = audit.snapshot(item, ITEM_FIELDS)

    item.section_id = data.section_id
    item.title_en = data.title_en
    item.title_es = data.title_es
    item.body_en = data.body_en
    item.body_es = data.body_es
    item.price = data.price
    item.image_url = data.image_url
    item.starts_on = data.starts_on
    item.ends_on = data.ends_on
    item.is_active = data.is_active
    if data.sort_order is not None:
        item.sort_order = data.sort_order

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_UPDATE,
        author=author,
        target=audit.format_target(audit.TARGET_CONTENT_ITEM, item.id),
        target_name=_display_name(item.title_en, item.title_es),
        details=audit.diff(before, audit.snapshot(item, ITEM_FIELDS)),
    )

    db.commit()
    db.refresh(item)
    return ContentItemResponse(
        id=item.id,
        section_id=item.section_id,
        title_en=item.title_en,
        title_es=item.title_es,
        body_en=item.body_en,
        body_es=item.body_es,
        price=item.price,
        image_url=item.image_url,
        starts_on=item.starts_on,
        ends_on=item.ends_on,
        sort_order=item.sort_order,
        is_active=bool(item.is_active),
        is_live=True,
    )


@router.delete("/api/content/items/{item_id}", status_code=204, dependencies=write_guard)
async def delete_content_item(
    item_id: int,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: remove one content row."""
    item = _get_item(db, item_id)

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_DELETE,
        author=author,
        target=audit.format_target(audit.TARGET_CONTENT_ITEM, item.id),
        target_name=_display_name(item.title_en, item.title_es),
        details=audit.snapshot(item, ITEM_FIELDS),
    )

    db.delete(item)
    db.commit()
