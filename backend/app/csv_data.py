"""CSV export and import for the editable content tables (ticket #56).

The admin panel is the only place the bar's content lives, so this module is the
way out: every content table can be downloaded as CSV, edited in a spreadsheet
and uploaded back. Import is deliberately all-or-nothing. Every row is validated
before anything is written; one bad row rejects the whole file and changes
nothing. A partial import would be the worst outcome — a file that looked mostly
right would leave the live menu half-edited.

Import never deletes. A row with an existing id (or slug, for the two slug-keyed
tables) is updated; a row without one is created. Deleting stays an explicit
action in the panel, because a spreadsheet with a missing row is far more likely
to be a mistake than a decision.

The file format is the export format. Every dataset has a fixed set of columns;
extra columns are ignored so a spreadsheet can carry notes, but a missing column
is a file-level error rather than a silently blank field.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Iterable

from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app import audit
from app.audit import ChangeAuthor
from app.models import (
    ContentItem,
    ContentSection,
    MenuCategory,
    MenuItem,
    MenuItemPromo,
    Reservation,
    SpecialEvent,
)
from app.schemas import (
    ContentItemWrite,
    ContentSectionWrite,
    MenuCategoryWrite,
    MenuItemWrite,
    MenuPromoWrite,
    SpecialEventUpdate,
)

# A spreadsheet with a few thousand rows is still tiny; anything much larger is
# a wrong file, not a menu.
MAX_IMPORT_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class Dataset:
    """One downloadable/uploadable CSV shape."""

    key: str
    label: str
    description: str
    columns: tuple[str, ...]
    importable: bool = True


DATASETS: tuple[Dataset, ...] = (
    Dataset(
        key="menu-categories",
        label="Menu categories",
        description="The headings on the drinks menu, their anchors and order.",
        columns=("slug", "name_en", "name_es", "sort_order", "is_available"),
    ),
    Dataset(
        key="menu-items",
        label="Menu items",
        description="Every drink, its category (by slug), price, description and availability.",
        columns=(
            "id",
            "category_slug",
            "name_en",
            "name_es",
            "description_en",
            "description_es",
            "ingredients_en",
            "ingredients_es",
            "price",
            "sort_order",
            "is_available",
            "is_drink_of_day",
        ),
    ),
    Dataset(
        key="menu-promos",
        label="Menu promos",
        description="Multi-buy offers and happy-hour windows, attached by item id.",
        columns=(
            "id",
            "item_id",
            "label_en",
            "label_es",
            "days",
            "start_time",
            "end_time",
            "starts_on",
            "ends_on",
            "is_active",
            "sort_order",
        ),
    ),
    Dataset(
        key="content-sections",
        label="Content sections",
        description="The About box, packages and other editable blocks, keyed by slug.",
        columns=("slug", "title_en", "title_es", "body_en", "body_es", "sort_order", "is_active"),
    ),
    Dataset(
        key="content-items",
        label="Content items",
        description="Rows inside a content section, attached by section slug.",
        columns=(
            "id",
            "section_slug",
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
        ),
    ),
    Dataset(
        key="special-events",
        label="Special events",
        description="Dated one-off events, including past and switched-off rows.",
        columns=(
            "id",
            "date",
            "title_en",
            "title_es",
            "description_en",
            "description_es",
            "start_time",
            "end_time",
            "image_url",
            "is_active",
        ),
    ),
    Dataset(
        key="reservations",
        label="Reservations",
        description="A read-only export of table requests for offline records.",
        columns=(
            "id",
            "date",
            "time",
            "party_size",
            "name",
            "contact",
            "notes",
            "status",
            "created_at",
        ),
        importable=False,
    ),
)

DATASETS_BY_KEY = {dataset.key: dataset for dataset in DATASETS}

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
    "is_drink_of_day",
)
PROMO_FIELDS = (
    "menu_item_id",
    "label_en",
    "label_es",
    "days",
    "start_time",
    "end_time",
    "starts_on",
    "ends_on",
    "is_active",
    "sort_order",
)
SECTION_FIELDS = ("slug", "title_en", "title_es", "body_en", "body_es", "sort_order", "is_active")
CONTENT_ITEM_FIELDS = (
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
EVENT_FIELDS = (
    "date",
    "title_en",
    "title_es",
    "description_en",
    "description_es",
    "start_time",
    "end_time",
    "image_url",
    "is_active",
)


class CsvImportError(ValueError):
    """A problem with the file as a whole, not with one row."""


@dataclass
class RowError:
    line: int
    message: str


@dataclass
class ImportResult:
    dataset: str
    created: int = 0
    updated: int = 0
    errors: list[RowError] = field(default_factory=list)
    message: str = ""

    @property
    def ok(self) -> bool:
        return not self.errors and not self.message


# --- Small CSV helpers -----------------------------------------------------


def _text(value: str | None) -> str:
    return (value or "").strip()


def _bool(value: str | None, default: bool) -> bool:
    text = _text(value).lower()
    if not text:
        return default
    if text in {"true", "1", "yes", "y", "on", "si", "sí"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError("must be true or false")


def _int(value: str | None, default: int | None = None) -> int | None:
    text = _text(value)
    if not text:
        return default
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError("must be a whole number") from exc


def _row_error(line: int, exc: Exception) -> RowError:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first.get("loc", ()))
        message = first.get("msg", "is invalid").replace("Value error, ", "")
        if location:
            message = f"{location}: {message}"
        return RowError(line, message)
    return RowError(line, str(exc) or "is invalid")


def _read_rows(text: str, dataset: Dataset) -> list[tuple[int, dict[str, str | None]]]:
    """Parse the file and check the header before looking at any row."""
    stream = io.StringIO(text, newline="")
    reader = csv.DictReader(stream)
    if not reader.fieldnames:
        raise CsvImportError("The file is empty.")

    # Excel writes a BOM; the route decodes with utf-8-sig, but a file pasted
    # through another tool can still carry one on the first header.
    reader.fieldnames = [name.strip().lstrip("\ufeff") for name in reader.fieldnames]
    missing = [column for column in dataset.columns if column not in reader.fieldnames]
    if missing:
        raise CsvImportError(
            "Missing column(s): " + ", ".join(missing) + ". Download the current export for the header."
        )

    rows: list[tuple[int, dict[str, str | None]]] = []
    for raw in reader:
        if not any(_text(raw.get(column)) for column in dataset.columns):
            continue
        rows.append((reader.line_num, raw))
    return rows


def _write_csv(columns: Iterable[str], rows: Iterable[Iterable[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(list(columns))
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return buffer.getvalue()


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


# --- Exports ---------------------------------------------------------------


def export_dataset(db: DBSession, key: str) -> tuple[Dataset, str]:
    """Return the dataset and its CSV text, without a byte-order mark."""
    dataset = DATASETS_BY_KEY.get(key)
    if dataset is None:
        raise CsvImportError("Unknown dataset.")

    if key == "menu-categories":
        rows = db.execute(
            select(MenuCategory).order_by(MenuCategory.sort_order, MenuCategory.id)
        ).scalars().all()
        text = _write_csv(
            dataset.columns,
            (
                (row.slug, row.name_en, row.name_es, row.sort_order, _bool_text(row.is_available))
                for row in rows
            ),
        )
    elif key == "menu-items":
        categories = {row.id: row.slug for row in db.execute(select(MenuCategory)).scalars()}
        rows = db.execute(
            select(MenuItem)
            .join(MenuCategory)
            .order_by(MenuCategory.sort_order, MenuItem.sort_order, MenuItem.id)
        ).scalars().all()
        text = _write_csv(
            dataset.columns,
            (
                (
                    row.id,
                    categories.get(row.category_id, ""),
                    row.name_en,
                    row.name_es,
                    row.description_en,
                    row.description_es,
                    row.ingredients_en,
                    row.ingredients_es,
                    row.price,
                    row.sort_order,
                    _bool_text(row.is_available),
                    _bool_text(row.is_drink_of_day),
                )
                for row in rows
            ),
        )
    elif key == "menu-promos":
        rows = db.execute(
            select(MenuItemPromo)
            .join(MenuItem)
            .join(MenuCategory)
            .order_by(MenuCategory.sort_order, MenuItem.sort_order, MenuItemPromo.sort_order, MenuItemPromo.id)
        ).scalars().all()
        text = _write_csv(
            dataset.columns,
            (
                (
                    row.id,
                    row.menu_item_id,
                    row.label_en,
                    row.label_es,
                    row.days,
                    row.start_time,
                    row.end_time,
                    row.starts_on,
                    row.ends_on,
                    _bool_text(row.is_active),
                    row.sort_order,
                )
                for row in rows
            ),
        )
    elif key == "content-sections":
        rows = db.execute(
            select(ContentSection).order_by(ContentSection.sort_order, ContentSection.id)
        ).scalars().all()
        text = _write_csv(
            dataset.columns,
            (
                (
                    row.slug,
                    row.title_en,
                    row.title_es,
                    row.body_en,
                    row.body_es,
                    row.sort_order,
                    _bool_text(row.is_active),
                )
                for row in rows
            ),
        )
    elif key == "content-items":
        sections = {row.id: row.slug for row in db.execute(select(ContentSection)).scalars()}
        rows = db.execute(
            select(ContentItem)
            .join(ContentSection)
            .order_by(ContentSection.sort_order, ContentItem.sort_order, ContentItem.id)
        ).scalars().all()
        text = _write_csv(
            dataset.columns,
            (
                (
                    row.id,
                    sections.get(row.section_id, ""),
                    row.title_en,
                    row.title_es,
                    row.body_en,
                    row.body_es,
                    row.price,
                    row.image_url,
                    row.starts_on,
                    row.ends_on,
                    row.sort_order,
                    _bool_text(row.is_active),
                )
                for row in rows
            ),
        )
    elif key == "special-events":
        rows = db.execute(
            select(SpecialEvent).order_by(SpecialEvent.date, SpecialEvent.id)
        ).scalars().all()
        text = _write_csv(
            dataset.columns,
            (
                (
                    row.id,
                    row.date,
                    row.title_en,
                    row.title_es,
                    row.description_en,
                    row.description_es,
                    row.start_time,
                    row.end_time,
                    row.image_url,
                    _bool_text(row.is_active),
                )
                for row in rows
            ),
        )
    elif key == "reservations":
        rows = db.execute(
            select(Reservation).order_by(Reservation.date, Reservation.time, Reservation.id)
        ).scalars().all()
        text = _write_csv(
            dataset.columns,
            (
                (
                    row.id,
                    row.date,
                    row.time,
                    row.party_size,
                    row.name,
                    row.contact,
                    row.notes,
                    row.status,
                    row.created_at.isoformat() if row.created_at else "",
                )
                for row in rows
            ),
        )
    else:  # pragma: no cover - the registry above is the source of truth
        raise CsvImportError("Unknown dataset.")

    return dataset, text


def count_dataset(db: DBSession, key: str) -> int:
    model = {
        "menu-categories": MenuCategory,
        "menu-items": MenuItem,
        "menu-promos": MenuItemPromo,
        "content-sections": ContentSection,
        "content-items": ContentItem,
        "special-events": SpecialEvent,
        "reservations": Reservation,
    }.get(key)
    if model is None:
        return 0
    return db.scalar(select(func.count()).select_from(model)) or 0


# --- Import ----------------------------------------------------------------


def import_dataset(
    db: DBSession,
    key: str,
    text: str,
    author: ChangeAuthor,
) -> ImportResult:
    """Validate every row, then apply the whole file or nothing.

    The caller owns the response: a result with errors means no rows were
    written. A uniqueness conflict is rolled back and reported as a file-level
    failure; any other unexpected error is rolled back and re-raised rather than
    leaving a half-applied import behind.
    """
    dataset = DATASETS_BY_KEY.get(key)
    if dataset is None:
        return ImportResult(dataset=key, message="Unknown dataset.")
    if not dataset.importable:
        return ImportResult(dataset=key, message="This dataset is export-only.")

    try:
        rows = _read_rows(text, dataset)
    except CsvImportError as exc:
        return ImportResult(dataset=key, message=str(exc))

    if not rows:
        return ImportResult(dataset=key, message="The file has no data rows.")

    try:
        result = _IMPORTERS[key](db, rows, author)
    except CsvImportError as exc:
        db.rollback()
        return ImportResult(dataset=key, message=str(exc))
    except IntegrityError:
        db.rollback()
        return ImportResult(
            dataset=key,
            message="The file conflicts with an existing row. Reload the page and check the ids and slugs.",
        )
    except Exception:  # noqa: BLE001 - never leave a partial import committed
        db.rollback()
        raise

    return result


def _apply_categories(db: DBSession, rows, author: ChangeAuthor) -> ImportResult:
    actions: list[tuple[int, MenuCategoryWrite, MenuCategory | None]] = []
    errors: list[RowError] = []
    seen: set[str] = set()

    for line, raw in rows:
        try:
            data = MenuCategoryWrite(
                slug=_text(raw.get("slug")),
                name_en=_text(raw.get("name_en")),
                name_es=_text(raw.get("name_es")),
                sort_order=_int(raw.get("sort_order")),
                is_available=_bool(raw.get("is_available"), True),
            )
        except (ValueError, ValidationError) as exc:
            errors.append(_row_error(line, exc))
            continue

        if data.slug in seen:
            errors.append(RowError(line, f"slug: duplicate slug '{data.slug}' in this file"))
            continue
        seen.add(data.slug)

        existing = db.execute(
            select(MenuCategory).where(MenuCategory.slug == data.slug)
        ).scalar_one_or_none()
        actions.append((line, data, existing))

    if errors:
        return ImportResult(dataset="menu-categories", errors=errors)

    last = db.execute(select(func.max(MenuCategory.sort_order))).scalar()
    next_order = (last + 1) if last is not None else 0
    created = updated = 0

    for _line, data, existing in actions:
        if existing is None:
            sort_order = data.sort_order if data.sort_order is not None else next_order
            next_order = max(next_order, sort_order + 1)
            row = MenuCategory(
                slug=data.slug,
                name_en=data.name_en,
                name_es=data.name_es,
                sort_order=sort_order,
                is_available=data.is_available,
            )
            db.add(row)
            db.flush()
            audit.log_change(
                db,
                area=audit.AREA_MENU,
                action=audit.ACTION_CREATE,
                author=author,
                target=audit.format_target(audit.TARGET_MENU_CATEGORY, row.id),
                target_name=row.name_en or row.name_es,
                details=audit.snapshot(row, CATEGORY_FIELDS),
            )
            created += 1
            continue

        before = audit.snapshot(existing, CATEGORY_FIELDS)
        existing.name_en = data.name_en
        existing.name_es = data.name_es
        existing.is_available = data.is_available
        if data.sort_order is not None:
            existing.sort_order = data.sort_order
        details = audit.diff(before, audit.snapshot(existing, CATEGORY_FIELDS))
        if details:
            audit.log_change(
                db,
                area=audit.AREA_MENU,
                action=audit.ACTION_UPDATE,
                author=author,
                target=audit.format_target(audit.TARGET_MENU_CATEGORY, existing.id),
                target_name=existing.name_en or existing.name_es,
                details=details,
            )
            updated += 1

    db.commit()
    return ImportResult(dataset="menu-categories", created=created, updated=updated)


def _apply_items(db: DBSession, rows, author: ChangeAuthor) -> ImportResult:
    categories = {row.slug: row for row in db.execute(select(MenuCategory)).scalars()}
    actions: list[tuple[int, MenuItemWrite, MenuItem | None]] = []
    errors: list[RowError] = []
    seen_ids: set[int] = set()
    drink_of_day_rows = 0

    for line, raw in rows:
        category_slug = _text(raw.get("category_slug"))
        category = categories.get(category_slug)
        if category is None:
            errors.append(RowError(line, f"category_slug: no category with slug '{category_slug}'"))
            continue

        try:
            item_id = _int(raw.get("id"))
            data = MenuItemWrite(
                category_id=category.id,
                name_en=_text(raw.get("name_en")),
                name_es=_text(raw.get("name_es")),
                description_en=_text(raw.get("description_en")),
                description_es=_text(raw.get("description_es")),
                ingredients_en=_text(raw.get("ingredients_en")),
                ingredients_es=_text(raw.get("ingredients_es")),
                price=_text(raw.get("price")),
                sort_order=_int(raw.get("sort_order")),
                is_available=_bool(raw.get("is_available"), True),
                is_drink_of_day=_bool(raw.get("is_drink_of_day"), False),
            )
        except (ValueError, ValidationError) as exc:
            errors.append(_row_error(line, exc))
            continue

        if item_id is not None:
            if item_id in seen_ids:
                errors.append(RowError(line, f"id: duplicate id '{item_id}' in this file"))
                continue
            seen_ids.add(item_id)

        existing = db.get(MenuItem, item_id) if item_id is not None else None
        if item_id is not None and existing is None:
            errors.append(RowError(line, f"id: no menu item with id '{item_id}'"))
            continue

        if data.is_drink_of_day:
            drink_of_day_rows += 1
        actions.append((line, data, existing))

    if drink_of_day_rows > 1:
        errors.append(
            RowError(0, "is_drink_of_day: only one row can be the drink of the day")
        )
    if errors:
        return ImportResult(dataset="menu-items", errors=errors)

    last_by_category = {
        category_id: (order if order is not None else -1)
        for category_id, order in db.execute(
            select(MenuItem.category_id, func.max(MenuItem.sort_order)).group_by(MenuItem.category_id)
        )
    }
    next_by_category = {key: value + 1 for key, value in last_by_category.items()}
    created = updated = 0
    drink_of_day_ids: list[int] = []

    for _line, data, existing in actions:
        if existing is None:
            sort_order = (
                data.sort_order
                if data.sort_order is not None
                else next_by_category.get(data.category_id, 0)
            )
            next_by_category[data.category_id] = max(
                next_by_category.get(data.category_id, 0), sort_order + 1
            )
            row = MenuItem(
                category_id=data.category_id,
                name_en=data.name_en,
                name_es=data.name_es,
                description_en=data.description_en,
                description_es=data.description_es,
                ingredients_en=data.ingredients_en,
                ingredients_es=data.ingredients_es,
                price=data.price,
                sort_order=sort_order,
                is_available=data.is_available,
                is_drink_of_day=data.is_drink_of_day,
            )
            db.add(row)
            db.flush()
            audit.log_change(
                db,
                area=audit.AREA_MENU,
                action=audit.ACTION_CREATE,
                author=author,
                target=audit.format_target(audit.TARGET_MENU_ITEM, row.id),
                target_name=row.name_en or row.name_es,
                details=audit.snapshot(row, ITEM_FIELDS),
            )
            if row.is_drink_of_day:
                drink_of_day_ids.append(row.id)
            created += 1
            continue

        before = audit.snapshot(existing, ITEM_FIELDS)
        existing.category_id = data.category_id
        existing.name_en = data.name_en
        existing.name_es = data.name_es
        existing.description_en = data.description_en
        existing.description_es = data.description_es
        existing.ingredients_en = data.ingredients_en
        existing.ingredients_es = data.ingredients_es
        existing.price = data.price
        existing.is_available = data.is_available
        existing.is_drink_of_day = data.is_drink_of_day
        if data.sort_order is not None:
            existing.sort_order = data.sort_order
        details = audit.diff(before, audit.snapshot(existing, ITEM_FIELDS))
        if details:
            audit.log_change(
                db,
                area=audit.AREA_MENU,
                action=audit.ACTION_UPDATE,
                author=author,
                target=audit.format_target(audit.TARGET_MENU_ITEM, existing.id),
                target_name=existing.name_en or existing.name_es,
                details=details,
            )
            updated += 1
        if existing.is_drink_of_day:
            drink_of_day_ids.append(existing.id)

    if drink_of_day_ids:
        db.execute(
            update(MenuItem)
            .where(MenuItem.id.notin_(drink_of_day_ids))
            .values(is_drink_of_day=False)
        )

    db.commit()
    return ImportResult(dataset="menu-items", created=created, updated=updated)


def _apply_promos(db: DBSession, rows, author: ChangeAuthor) -> ImportResult:
    items = {row.id: row for row in db.execute(select(MenuItem)).scalars()}
    actions: list[tuple[int, MenuPromoWrite, int, MenuItemPromo | None]] = []
    errors: list[RowError] = []
    seen_ids: set[int] = set()

    for line, raw in rows:
        item_id = _int(raw.get("item_id"))
        item = items.get(item_id) if item_id is not None else None
        if item is None:
            errors.append(RowError(line, f"item_id: no menu item with id '{_text(raw.get('item_id'))}'"))
            continue

        try:
            promo_id = _int(raw.get("id"))
            data = MenuPromoWrite(
                label_en=_text(raw.get("label_en")),
                label_es=_text(raw.get("label_es")),
                days=_text(raw.get("days")),
                start_time=_text(raw.get("start_time")),
                end_time=_text(raw.get("end_time")),
                starts_on=_text(raw.get("starts_on")),
                ends_on=_text(raw.get("ends_on")),
                is_active=_bool(raw.get("is_active"), True),
            )
        except (ValueError, ValidationError) as exc:
            errors.append(_row_error(line, exc))
            continue

        if promo_id is not None:
            if promo_id in seen_ids:
                errors.append(RowError(line, f"id: duplicate id '{promo_id}' in this file"))
                continue
            seen_ids.add(promo_id)

        existing = db.get(MenuItemPromo, promo_id) if promo_id is not None else None
        if promo_id is not None and existing is None:
            errors.append(RowError(line, f"id: no promo with id '{promo_id}'"))
            continue

        actions.append((line, data, item.id, existing))

    if errors:
        return ImportResult(dataset="menu-promos", errors=errors)

    last_by_item = {
        item_id: (order if order is not None else -1)
        for item_id, order in db.execute(
            select(MenuItemPromo.menu_item_id, func.max(MenuItemPromo.sort_order)).group_by(
                MenuItemPromo.menu_item_id
            )
        )
    }
    next_by_item = {key: value + 1 for key, value in last_by_item.items()}
    created = updated = 0

    for _line, data, item_id, existing in actions:
        if existing is None:
            sort_order = next_by_item.get(item_id, 0)
            next_by_item[item_id] = sort_order + 1
            row = MenuItemPromo(
                menu_item_id=item_id,
                label_en=data.label_en,
                label_es=data.label_es,
                days=data.days,
                start_time=data.start_time,
                end_time=data.end_time,
                starts_on=data.starts_on,
                ends_on=data.ends_on,
                is_active=data.is_active,
                sort_order=sort_order,
            )
            db.add(row)
            db.flush()
            audit.log_change(
                db,
                area=audit.AREA_MENU,
                action=audit.ACTION_CREATE,
                author=author,
                target=audit.format_target(audit.TARGET_MENU_ITEM, item_id),
                target_name=items[item_id].name_en or items[item_id].name_es,
                details=audit.snapshot(row, PROMO_FIELDS),
            )
            created += 1
            continue

        before = audit.snapshot(existing, PROMO_FIELDS)
        existing.menu_item_id = item_id
        existing.label_en = data.label_en
        existing.label_es = data.label_es
        existing.days = data.days
        existing.start_time = data.start_time
        existing.end_time = data.end_time
        existing.starts_on = data.starts_on
        existing.ends_on = data.ends_on
        existing.is_active = data.is_active
        details = audit.diff(before, audit.snapshot(existing, PROMO_FIELDS))
        if details:
            audit.log_change(
                db,
                area=audit.AREA_MENU,
                action=audit.ACTION_UPDATE,
                author=author,
                target=audit.format_target(audit.TARGET_MENU_ITEM, item_id),
                target_name=items[item_id].name_en or items[item_id].name_es,
                details=details,
            )
            updated += 1

    db.commit()
    return ImportResult(dataset="menu-promos", created=created, updated=updated)


def _apply_sections(db: DBSession, rows, author: ChangeAuthor) -> ImportResult:
    actions: list[tuple[int, ContentSectionWrite, ContentSection | None]] = []
    errors: list[RowError] = []
    seen: set[str] = set()

    for line, raw in rows:
        try:
            data = ContentSectionWrite(
                slug=_text(raw.get("slug")),
                title_en=_text(raw.get("title_en")),
                title_es=_text(raw.get("title_es")),
                body_en=_text(raw.get("body_en")),
                body_es=_text(raw.get("body_es")),
                sort_order=_int(raw.get("sort_order")),
                is_active=_bool(raw.get("is_active"), True),
            )
        except (ValueError, ValidationError) as exc:
            errors.append(_row_error(line, exc))
            continue

        if data.slug in seen:
            errors.append(RowError(line, f"slug: duplicate slug '{data.slug}' in this file"))
            continue
        seen.add(data.slug)

        existing = db.execute(
            select(ContentSection).where(ContentSection.slug == data.slug)
        ).scalar_one_or_none()
        actions.append((line, data, existing))

    if errors:
        return ImportResult(dataset="content-sections", errors=errors)

    last = db.execute(select(func.max(ContentSection.sort_order))).scalar()
    next_order = (last + 1) if last is not None else 0
    created = updated = 0

    for _line, data, existing in actions:
        if existing is None:
            sort_order = data.sort_order if data.sort_order is not None else next_order
            next_order = max(next_order, sort_order + 1)
            row = ContentSection(
                slug=data.slug,
                title_en=data.title_en,
                title_es=data.title_es,
                body_en=data.body_en,
                body_es=data.body_es,
                sort_order=sort_order,
                is_active=data.is_active,
            )
            db.add(row)
            db.flush()
            audit.log_change(
                db,
                area=audit.AREA_CONTENT,
                action=audit.ACTION_CREATE,
                author=author,
                target=audit.format_target(audit.TARGET_CONTENT_SECTION, row.id),
                target_name=row.title_en or row.title_es,
                details=audit.snapshot(row, SECTION_FIELDS),
            )
            created += 1
            continue

        before = audit.snapshot(existing, SECTION_FIELDS)
        existing.title_en = data.title_en
        existing.title_es = data.title_es
        existing.body_en = data.body_en
        existing.body_es = data.body_es
        existing.is_active = data.is_active
        if data.sort_order is not None:
            existing.sort_order = data.sort_order
        details = audit.diff(before, audit.snapshot(existing, SECTION_FIELDS))
        if details:
            audit.log_change(
                db,
                area=audit.AREA_CONTENT,
                action=audit.ACTION_UPDATE,
                author=author,
                target=audit.format_target(audit.TARGET_CONTENT_SECTION, existing.id),
                target_name=existing.title_en or existing.title_es,
                details=details,
            )
            updated += 1

    db.commit()
    return ImportResult(dataset="content-sections", created=created, updated=updated)


def _apply_content_items(db: DBSession, rows, author: ChangeAuthor) -> ImportResult:
    sections = {row.slug: row for row in db.execute(select(ContentSection)).scalars()}
    actions: list[tuple[int, ContentItemWrite, ContentItem | None]] = []
    errors: list[RowError] = []
    seen_ids: set[int] = set()

    for line, raw in rows:
        section_slug = _text(raw.get("section_slug"))
        section = sections.get(section_slug)
        if section is None:
            errors.append(RowError(line, f"section_slug: no section with slug '{section_slug}'"))
            continue

        try:
            item_id = _int(raw.get("id"))
            data = ContentItemWrite(
                section_id=section.id,
                title_en=_text(raw.get("title_en")),
                title_es=_text(raw.get("title_es")),
                body_en=_text(raw.get("body_en")),
                body_es=_text(raw.get("body_es")),
                price=_text(raw.get("price")),
                image_url=_text(raw.get("image_url")),
                starts_on=_text(raw.get("starts_on")),
                ends_on=_text(raw.get("ends_on")),
                sort_order=_int(raw.get("sort_order")),
                is_active=_bool(raw.get("is_active"), True),
            )
        except (ValueError, ValidationError) as exc:
            errors.append(_row_error(line, exc))
            continue

        if item_id is not None:
            if item_id in seen_ids:
                errors.append(RowError(line, f"id: duplicate id '{item_id}' in this file"))
                continue
            seen_ids.add(item_id)

        existing = db.get(ContentItem, item_id) if item_id is not None else None
        if item_id is not None and existing is None:
            errors.append(RowError(line, f"id: no content item with id '{item_id}'"))
            continue

        actions.append((line, data, existing))

    if errors:
        return ImportResult(dataset="content-items", errors=errors)

    last_by_section = {
        section_id: (order if order is not None else -1)
        for section_id, order in db.execute(
            select(ContentItem.section_id, func.max(ContentItem.sort_order)).group_by(
                ContentItem.section_id
            )
        )
    }
    next_by_section = {key: value + 1 for key, value in last_by_section.items()}
    created = updated = 0

    for _line, data, existing in actions:
        if existing is None:
            sort_order = (
                data.sort_order
                if data.sort_order is not None
                else next_by_section.get(data.section_id, 0)
            )
            next_by_section[data.section_id] = max(
                next_by_section.get(data.section_id, 0), sort_order + 1
            )
            row = ContentItem(
                section_id=data.section_id,
                title_en=data.title_en,
                title_es=data.title_es,
                body_en=data.body_en,
                body_es=data.body_es,
                price=data.price,
                image_url=data.image_url,
                starts_on=data.starts_on,
                ends_on=data.ends_on,
                sort_order=sort_order,
                is_active=data.is_active,
            )
            db.add(row)
            db.flush()
            audit.log_change(
                db,
                area=audit.AREA_CONTENT,
                action=audit.ACTION_CREATE,
                author=author,
                target=audit.format_target(audit.TARGET_CONTENT_ITEM, row.id),
                target_name=row.title_en or row.title_es,
                details=audit.snapshot(row, CONTENT_ITEM_FIELDS),
            )
            created += 1
            continue

        before = audit.snapshot(existing, CONTENT_ITEM_FIELDS)
        existing.section_id = data.section_id
        existing.title_en = data.title_en
        existing.title_es = data.title_es
        existing.body_en = data.body_en
        existing.body_es = data.body_es
        existing.price = data.price
        existing.image_url = data.image_url
        existing.starts_on = data.starts_on
        existing.ends_on = data.ends_on
        existing.is_active = data.is_active
        if data.sort_order is not None:
            existing.sort_order = data.sort_order
        details = audit.diff(before, audit.snapshot(existing, CONTENT_ITEM_FIELDS))
        if details:
            audit.log_change(
                db,
                area=audit.AREA_CONTENT,
                action=audit.ACTION_UPDATE,
                author=author,
                target=audit.format_target(audit.TARGET_CONTENT_ITEM, existing.id),
                target_name=existing.title_en or existing.title_es,
                details=details,
            )
            updated += 1

    db.commit()
    return ImportResult(dataset="content-items", created=created, updated=updated)


def _apply_events(db: DBSession, rows, author: ChangeAuthor) -> ImportResult:
    actions: list[tuple[int, SpecialEventUpdate, SpecialEvent | None]] = []
    errors: list[RowError] = []
    seen_ids: set[int] = set()

    for line, raw in rows:
        try:
            event_id = _int(raw.get("id"))
            data = SpecialEventUpdate(
                date=_text(raw.get("date")),
                title_en=_text(raw.get("title_en")),
                title_es=_text(raw.get("title_es")),
                description_en=_text(raw.get("description_en")),
                description_es=_text(raw.get("description_es")),
                start_time=_text(raw.get("start_time")),
                end_time=_text(raw.get("end_time")),
                image_url=_text(raw.get("image_url")),
                is_active=_bool(raw.get("is_active"), True),
            )
        except (ValueError, ValidationError) as exc:
            errors.append(_row_error(line, exc))
            continue

        if event_id is not None:
            if event_id in seen_ids:
                errors.append(RowError(line, f"id: duplicate id '{event_id}' in this file"))
                continue
            seen_ids.add(event_id)

        existing = db.get(SpecialEvent, event_id) if event_id is not None else None
        if event_id is not None and existing is None:
            errors.append(RowError(line, f"id: no special event with id '{event_id}'"))
            continue

        actions.append((line, data, existing))

    if errors:
        return ImportResult(dataset="special-events", errors=errors)

    created = updated = 0
    for _line, data, existing in actions:
        if existing is None:
            row = SpecialEvent(
                date=data.date.isoformat(),
                title_en=data.title_en,
                title_es=data.title_es,
                description_en=data.description_en,
                description_es=data.description_es,
                start_time=data.start_time,
                end_time=data.end_time,
                image_url=data.image_url,
                is_active=data.is_active,
            )
            db.add(row)
            db.flush()
            audit.log_change(
                db,
                area=audit.AREA_SCHEDULE,
                action=audit.ACTION_CREATE,
                author=author,
                target=audit.format_target(audit.TARGET_SPECIAL_EVENT, row.id),
                target_name=row.title_en or row.title_es,
                details=audit.snapshot(row, EVENT_FIELDS),
            )
            created += 1
            continue

        before = audit.snapshot(existing, EVENT_FIELDS)
        existing.date = data.date.isoformat()
        existing.title_en = data.title_en
        existing.title_es = data.title_es
        existing.description_en = data.description_en
        existing.description_es = data.description_es
        existing.start_time = data.start_time
        existing.end_time = data.end_time
        existing.image_url = data.image_url
        existing.is_active = data.is_active
        details = audit.diff(before, audit.snapshot(existing, EVENT_FIELDS))
        if details:
            audit.log_change(
                db,
                area=audit.AREA_SCHEDULE,
                action=audit.ACTION_UPDATE,
                author=author,
                target=audit.format_target(audit.TARGET_SPECIAL_EVENT, existing.id),
                target_name=existing.title_en or existing.title_es,
                details=details,
            )
            updated += 1

    db.commit()
    return ImportResult(dataset="special-events", created=created, updated=updated)


_IMPORTERS = {
    "menu-categories": _apply_categories,
    "menu-items": _apply_items,
    "menu-promos": _apply_promos,
    "content-sections": _apply_sections,
    "content-items": _apply_content_items,
    "special-events": _apply_events,
}
