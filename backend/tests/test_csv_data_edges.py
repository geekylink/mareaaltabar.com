"""Branch coverage for the CSV import contract (ticket #56).

`test_csv_data.py` drives the admin route and pins the paths a bar owner uses.
These tests call `csv_data.import_dataset` directly to exercise the validation
and rollback branches: the ones that decide whether a bad file changes nothing,
and whether every dataset supports both create and update.
"""

import csv
import io

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import audit, csv_data
from app.audit import ChangeAuthor
from app.models import (
    ContentItem,
    ContentSection,
    MenuCategory,
    MenuItem,
    MenuItemPromo,
    SpecialEvent,
)
from app.schemas import MenuCategoryWrite

AUTHOR = ChangeAuthor(username="edge-tests", ip="127.0.0.1", user_agent="pytest")


def row_for(key, **overrides):
    """A complete row, so a test only spells out the cells it cares about."""
    return {column: "" for column in csv_data.DATASETS_BY_KEY[key].columns} | overrides


def write_rows(key, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=csv_data.DATASETS_BY_KEY[key].columns,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def import_rows(db, key, rows):
    return csv_data.import_dataset(db, key, write_rows(key, rows), AUTHOR)


def item_row(item, **overrides):
    return row_for(
        "menu-items",
        id=str(item.id),
        category_slug=item.category.slug,
        name_en=item.name_en,
        name_es=item.name_es,
        description_en=item.description_en,
        description_es=item.description_es,
        ingredients_en=item.ingredients_en,
        ingredients_es=item.ingredients_es,
        price=item.price,
        sort_order=str(item.sort_order),
        is_available="true" if item.is_available else "false",
        is_drink_of_day="true" if item.is_drink_of_day else "false",
    ) | overrides


def promo_row(promo, **overrides):
    return row_for(
        "menu-promos",
        id=str(promo.id),
        item_id=str(promo.menu_item_id),
        label_en=promo.label_en,
        label_es=promo.label_es,
        days=promo.days,
        start_time=promo.start_time,
        end_time=promo.end_time,
        starts_on=promo.starts_on,
        ends_on=promo.ends_on,
        is_active="true" if promo.is_active else "false",
        sort_order=str(promo.sort_order),
    ) | overrides


# --- File-level guards -----------------------------------------------------


def test_an_unknown_dataset_is_rejected(db_session):
    result = csv_data.import_dataset(db_session, "nope", "slug\n", AUTHOR)

    assert not result.ok
    assert result.message == "Unknown dataset."


def test_an_export_only_dataset_is_rejected(db_session):
    result = csv_data.import_dataset(db_session, "reservations", "id\n", AUTHOR)

    assert not result.ok
    assert result.message == "This dataset is export-only."


def test_a_file_with_no_header_is_a_file_error(db_session):
    result = csv_data.import_dataset(db_session, "menu-categories", "", AUTHOR)

    assert not result.ok
    assert result.message == "The file is empty."


def test_a_header_with_no_data_rows_is_a_file_error(db_session):
    result = csv_data.import_dataset(
        db_session,
        "menu-categories",
        "slug,name_en,name_es,sort_order,is_available\n",
        AUTHOR,
    )

    assert not result.ok
    assert result.message == "The file has no data rows."


def test_an_importer_file_error_rolls_back(db_session, monkeypatch):
    def reject(_db, _rows, _author):
        raise csv_data.CsvImportError("the file as a whole is wrong")

    monkeypatch.setitem(csv_data._IMPORTERS, "menu-categories", reject)

    result = import_rows(
        db_session,
        "menu-categories",
        [row_for("menu-categories", slug="food", name_en="Food")],
    )

    assert not result.ok
    assert result.message == "the file as a whole is wrong"
    assert db_session.execute(
        select(MenuCategory).where(MenuCategory.slug == "food")
    ).scalar_one_or_none() is None


def test_a_uniqueness_conflict_rolls_back(db_session, monkeypatch):
    def conflict(_db, _rows, _author):
        raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setitem(csv_data._IMPORTERS, "menu-categories", conflict)

    result = import_rows(
        db_session,
        "menu-categories",
        [row_for("menu-categories", slug="food", name_en="Food")],
    )

    assert not result.ok
    assert "conflicts with an existing row" in result.message
    assert db_session.execute(
        select(MenuCategory).where(MenuCategory.slug == "food")
    ).scalar_one_or_none() is None


def test_an_unexpected_error_rolls_back_and_propagates(db_session, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(audit, "log_change", boom)
    before = len(db_session.execute(select(MenuCategory)).scalars().all())

    with pytest.raises(RuntimeError, match="boom"):
        import_rows(
            db_session,
            "menu-categories",
            [row_for("menu-categories", slug="food", name_en="Food")],
        )

    db_session.expire_all()
    after = len(db_session.execute(select(MenuCategory)).scalars().all())
    assert after == before
    assert db_session.execute(
        select(MenuCategory).where(MenuCategory.slug == "food")
    ).scalar_one_or_none() is None


# --- Small parsers and the reader -----------------------------------------


def test_the_boolean_parser_accepts_blank_and_rejects_garbage():
    assert csv_data._bool("", True) is True
    assert csv_data._bool(None, False) is False
    assert csv_data._bool("Sí", False) is True
    assert csv_data._bool("no", True) is False

    with pytest.raises(ValueError, match="true or false"):
        csv_data._bool("sometimes", True)


def test_the_integer_parser_accepts_blank_and_rejects_garbage():
    assert csv_data._int("") is None
    assert csv_data._int(" 7 ") == 7

    with pytest.raises(ValueError, match="whole number"):
        csv_data._int("7.5")


def test_row_errors_name_the_field_and_fall_back_to_plain_errors():
    with pytest.raises(ValidationError) as caught:
        MenuCategoryWrite(name_en="", slug="")

    from_schema = csv_data._row_error(4, caught.value)
    assert from_schema.line == 4
    assert from_schema.message.startswith("name_en:")

    assert (
        csv_data._row_error(5, ValueError("must be true or false")).message
        == "must be true or false"
    )
    assert csv_data._row_error(6, ValueError()).message == "is invalid"


def test_the_reader_strips_a_bom_and_skips_an_all_blank_row():
    dataset = csv_data.DATASETS_BY_KEY["menu-categories"]
    text = (
        "\ufeffslug, name_en ,name_es,sort_order,is_available\n"
        "edge,Edge,,,\n"
        ",,,,\n"
    )

    rows = csv_data._read_rows(text, dataset)

    assert len(rows) == 1
    _line, raw = rows[0]
    assert raw["slug"] == "edge"
    assert raw["name_en"] == "Edge"


# --- Exports ---------------------------------------------------------------


def test_content_items_export_carries_the_section_slug(db_session):
    section = ContentSection(
        slug="edge-about", title_en="About", title_es="Nosotros", sort_order=0
    )
    db_session.add(section)
    db_session.flush()
    db_session.add(
        ContentItem(
            section_id=section.id,
            title_en="Our story",
            body_en="We opened in 2019.",
            sort_order=0,
        )
    )
    db_session.commit()

    dataset, text = csv_data.export_dataset(db_session, "content-items")

    assert dataset.key == "content-items"
    [row] = list(csv.DictReader(io.StringIO(text)))
    assert row["section_slug"] == "edge-about"
    assert row["title_en"] == "Our story"


def test_count_dataset_returns_zero_for_an_unknown_key(db_session):
    assert csv_data.count_dataset(db_session, "nope") == 0


# --- Menu categories -------------------------------------------------------


def test_a_category_can_be_created_by_slug(db_session):
    before = [row.sort_order for row in db_session.execute(select(MenuCategory)).scalars()]

    result = import_rows(
        db_session,
        "menu-categories",
        [
            row_for(
                "menu-categories",
                slug="food",
                name_en="Food",
                name_es="Comida",
                sort_order="",
                is_available="true",
            )
        ],
    )

    assert result.ok
    assert result.created == 1

    db_session.expire_all()
    created = db_session.execute(
        select(MenuCategory).where(MenuCategory.slug == "food")
    ).scalar_one()
    assert created.name_en == "Food"
    assert created.sort_order == max(before) + 1


def test_a_category_duplicate_slug_in_the_file_is_rejected(db_session):
    row = row_for(
        "menu-categories",
        slug="food",
        name_en="Food",
        name_es="Comida",
        sort_order="",
        is_available="true",
    )

    result = import_rows(db_session, "menu-categories", [row, row])

    assert not result.ok
    assert any("duplicate slug 'food'" in error.message for error in result.errors)
    assert db_session.execute(
        select(MenuCategory).where(MenuCategory.slug == "food")
    ).scalar_one_or_none() is None


def test_a_category_with_an_unreadable_boolean_is_rejected(db_session):
    result = import_rows(
        db_session,
        "menu-categories",
        [
            row_for(
                "menu-categories",
                slug="food",
                name_en="Food",
                sort_order="",
                is_available="sometimes",
            )
        ],
    )

    assert not result.ok
    assert any("must be true or false" in error.message for error in result.errors)


def test_a_category_update_leaves_the_order_alone_when_the_cell_is_blank(db_session):
    category = db_session.execute(
        select(MenuCategory).where(MenuCategory.slug == "cerveza")
    ).scalar_one()

    result = import_rows(
        db_session,
        "menu-categories",
        [
            row_for(
                "menu-categories",
                slug=category.slug,
                name_en=category.name_en,
                name_es=category.name_es,
                sort_order="",
                is_available="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 0

    db_session.expire_all()
    assert db_session.get(MenuCategory, category.id).sort_order == category.sort_order


# --- Menu items ------------------------------------------------------------


def test_a_menu_item_with_a_duplicate_id_is_rejected(db_session):
    item = db_session.execute(select(MenuItem).order_by(MenuItem.id)).scalars().first()
    row = item_row(item)

    result = import_rows(db_session, "menu-items", [row, row])

    assert not result.ok
    assert any("duplicate id" in error.message for error in result.errors)


def test_a_menu_item_with_an_unreadable_boolean_is_rejected(db_session):
    result = import_rows(
        db_session,
        "menu-items",
        [
            row_for(
                "menu-items",
                category_slug="cerveza",
                name_en="Bad Flag",
                price="1.00",
                is_available="sometimes",
            )
        ],
    )

    assert not result.ok
    assert any("must be true or false" in error.message for error in result.errors)


def test_a_new_drink_of_the_day_clears_the_previous_one(db_session):
    previous = db_session.execute(select(MenuItem).order_by(MenuItem.id)).scalars().first()
    previous.is_drink_of_day = True
    db_session.commit()

    result = import_rows(
        db_session,
        "menu-items",
        [
            row_for(
                "menu-items",
                category_slug="cerveza",
                name_en="New Star",
                name_es="Nueva Estrella",
                price="4.50",
                sort_order="",
                is_available="true",
                is_drink_of_day="true",
            )
        ],
    )

    assert result.ok
    assert result.created == 1

    db_session.expire_all()
    flagged = db_session.execute(
        select(MenuItem).where(MenuItem.is_drink_of_day.is_(True))
    ).scalars().all()
    assert [row.name_en for row in flagged] == ["New Star"]


def test_an_item_update_leaves_the_order_alone_when_the_cell_is_blank(db_session):
    item = db_session.execute(select(MenuItem).order_by(MenuItem.id)).scalars().first()

    result = import_rows(db_session, "menu-items", [item_row(item, sort_order="")])

    assert result.ok
    assert result.updated == 0


# --- Menu promos -----------------------------------------------------------


def test_a_promo_can_be_created_for_an_item(db_session):
    item = db_session.execute(select(MenuItem).order_by(MenuItem.id)).scalars().first()

    result = import_rows(
        db_session,
        "menu-promos",
        [
            row_for(
                "menu-promos",
                id="",
                item_id=str(item.id),
                label_en="2 for $5",
                is_active="true",
                sort_order="",
            )
        ],
    )

    assert result.ok
    assert result.created == 1

    db_session.expire_all()
    created = db_session.execute(
        select(MenuItemPromo).where(MenuItemPromo.label_en == "2 for $5")
    ).scalar_one()
    assert created.menu_item_id == item.id


def test_a_promo_for_an_unknown_item_is_rejected(db_session):
    result = import_rows(
        db_session,
        "menu-promos",
        [row_for("menu-promos", item_id="999999", label_en="Ghost")],
    )

    assert not result.ok
    assert any("no menu item with id" in error.message for error in result.errors)


def test_a_promo_with_half_a_window_is_rejected(db_session):
    item = db_session.execute(select(MenuItem).order_by(MenuItem.id)).scalars().first()

    result = import_rows(
        db_session,
        "menu-promos",
        [
            row_for(
                "menu-promos",
                item_id=str(item.id),
                label_en="Late",
                start_time="21:00",
                end_time="",
            )
        ],
    )

    assert not result.ok
    assert any("set both start_time and end_time" in error.message for error in result.errors)


def test_a_promo_with_a_duplicate_id_is_rejected(db_session):
    promo = db_session.execute(select(MenuItemPromo).order_by(MenuItemPromo.id)).scalars().first()
    row = promo_row(promo)

    result = import_rows(db_session, "menu-promos", [row, row])

    assert not result.ok
    assert any("duplicate id" in error.message for error in result.errors)


def test_a_promo_with_an_unknown_id_is_rejected(db_session):
    promo = db_session.execute(select(MenuItemPromo).order_by(MenuItemPromo.id)).scalars().first()

    result = import_rows(
        db_session,
        "menu-promos",
        [promo_row(promo, id="999999")],
    )

    assert not result.ok
    assert any("no promo with id" in error.message for error in result.errors)


# --- Content sections ------------------------------------------------------


def test_a_section_can_be_updated_by_slug(db_session):
    section = ContentSection(
        slug="edge-about",
        title_en="About",
        title_es="Nosotros",
        body_en="Old copy",
        sort_order=10,
    )
    db_session.add(section)
    db_session.commit()

    result = import_rows(
        db_session,
        "content-sections",
        [
            row_for(
                "content-sections",
                slug="edge-about",
                title_en="About us",
                title_es="Nosotros",
                body_en="New copy",
                sort_order="",
                is_active="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 1

    db_session.expire_all()
    updated = db_session.get(ContentSection, section.id)
    assert updated.title_en == "About us"
    assert updated.body_en == "New copy"
    assert updated.sort_order == 10


def test_a_section_with_no_title_is_rejected(db_session):
    result = import_rows(
        db_session,
        "content-sections",
        [row_for("content-sections", slug="edge-about", title_en="", title_es="")],
    )

    assert not result.ok
    assert any("title is required" in error.message for error in result.errors)


def test_a_section_duplicate_slug_in_the_file_is_rejected(db_session):
    row = row_for(
        "content-sections",
        slug="edge-about",
        title_en="About",
        is_active="true",
    )

    result = import_rows(db_session, "content-sections", [row, row])

    assert not result.ok
    assert any("duplicate slug 'edge-about'" in error.message for error in result.errors)


# --- Content items ---------------------------------------------------------


def test_a_content_item_can_be_updated_by_id(db_session):
    section = ContentSection(
        slug="edge-items", title_en="Packages", title_es="Paquetes", sort_order=0
    )
    db_session.add(section)
    db_session.flush()
    item = ContentItem(
        section_id=section.id,
        title_en="Old name",
        body_en="Old copy",
        sort_order=5,
    )
    db_session.add(item)
    db_session.commit()

    result = import_rows(
        db_session,
        "content-items",
        [
            row_for(
                "content-items",
                id=str(item.id),
                section_slug="edge-items",
                title_en="New name",
                body_en="New copy",
                sort_order="",
                is_active="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 1

    db_session.expire_all()
    updated = db_session.get(ContentItem, item.id)
    assert updated.title_en == "New name"
    assert updated.body_en == "New copy"
    assert updated.sort_order == 5


def test_a_content_item_with_no_title_is_rejected(db_session):
    section = ContentSection(
        slug="edge-items", title_en="Packages", title_es="Paquetes", sort_order=0
    )
    db_session.add(section)
    db_session.commit()

    result = import_rows(
        db_session,
        "content-items",
        [row_for("content-items", section_slug="edge-items", title_en="", title_es="")],
    )

    assert not result.ok
    assert any("title is required" in error.message for error in result.errors)


def test_a_content_item_with_a_duplicate_or_unknown_id_is_rejected(db_session):
    section = ContentSection(
        slug="edge-items", title_en="Packages", title_es="Paquetes", sort_order=0
    )
    db_session.add(section)
    db_session.flush()
    item = ContentItem(section_id=section.id, title_en="One", sort_order=0)
    db_session.add(item)
    db_session.commit()

    row = row_for(
        "content-items",
        id=str(item.id),
        section_slug="edge-items",
        title_en="One",
        is_active="true",
    )

    duplicate = import_rows(db_session, "content-items", [row, row])
    assert not duplicate.ok
    assert any("duplicate id" in error.message for error in duplicate.errors)

    missing = import_rows(
        db_session,
        "content-items",
        [row_for("content-items", id="999999", section_slug="edge-items", title_en="Ghost")],
    )
    assert not missing.ok
    assert any("no content item with id" in error.message for error in missing.errors)


# --- Special events --------------------------------------------------------


def test_an_event_can_be_updated_by_id(db_session):
    event = SpecialEvent(date="2030-01-01", title_en="Old Party", is_active=True)
    db_session.add(event)
    db_session.commit()

    result = import_rows(
        db_session,
        "special-events",
        [
            row_for(
                "special-events",
                id=str(event.id),
                date="2030-01-02",
                title_en="New Party",
                is_active="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 1

    db_session.expire_all()
    updated = db_session.get(SpecialEvent, event.id)
    assert updated.date == "2030-01-02"
    assert updated.title_en == "New Party"


def test_an_event_with_a_duplicate_or_unknown_id_is_rejected(db_session):
    event = SpecialEvent(date="2030-01-01", title_en="Party", is_active=True)
    db_session.add(event)
    db_session.commit()

    row = row_for(
        "special-events",
        id=str(event.id),
        date="2030-01-01",
        title_en="Party",
        is_active="true",
    )

    duplicate = import_rows(db_session, "special-events", [row, row])
    assert not duplicate.ok
    assert any("duplicate id" in error.message for error in duplicate.errors)

    missing = import_rows(
        db_session,
        "special-events",
        [row_for("special-events", id="999999", date="2030-01-01", title_en="Ghost")],
    )
    assert not missing.ok
    assert any("no special event with id" in error.message for error in missing.errors)


def test_a_section_update_can_move_the_section(db_session):
    section = ContentSection(
        slug="edge-move",
        title_en="About",
        title_es="Nosotros",
        body_en="Copy",
        sort_order=10,
    )
    db_session.add(section)
    db_session.commit()

    result = import_rows(
        db_session,
        "content-sections",
        [
            row_for(
                "content-sections",
                slug="edge-move",
                title_en="About",
                title_es="Nosotros",
                body_en="Copy",
                sort_order="3",
                is_active="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 1

    db_session.expire_all()
    assert db_session.get(ContentSection, section.id).sort_order == 3


def test_a_section_update_with_no_changes_writes_nothing(db_session):
    section = ContentSection(
        slug="edge-noop",
        title_en="About",
        title_es="Nosotros",
        body_en="Copy",
        body_es="",
        sort_order=4,
    )
    db_session.add(section)
    db_session.commit()

    result = import_rows(
        db_session,
        "content-sections",
        [
            row_for(
                "content-sections",
                slug="edge-noop",
                title_en="About",
                title_es="Nosotros",
                body_en="Copy",
                body_es="",
                sort_order="",
                is_active="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 0


def test_a_content_item_update_can_move_the_item(db_session):
    section = ContentSection(
        slug="edge-item-move", title_en="Packages", title_es="Paquetes", sort_order=0
    )
    db_session.add(section)
    db_session.flush()
    item = ContentItem(section_id=section.id, title_en="One", sort_order=5)
    db_session.add(item)
    db_session.commit()

    result = import_rows(
        db_session,
        "content-items",
        [
            row_for(
                "content-items",
                id=str(item.id),
                section_slug="edge-item-move",
                title_en="One",
                sort_order="2",
                is_active="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 1

    db_session.expire_all()
    assert db_session.get(ContentItem, item.id).sort_order == 2


def test_a_content_item_update_with_no_changes_writes_nothing(db_session):
    section = ContentSection(
        slug="edge-item-noop", title_en="Packages", title_es="Paquetes", sort_order=0
    )
    db_session.add(section)
    db_session.flush()
    item = ContentItem(
        section_id=section.id,
        title_en="One",
        title_es="",
        body_en="",
        body_es="",
        price="",
        image_url="",
        starts_on="",
        ends_on="",
        sort_order=6,
        is_active=True,
    )
    db_session.add(item)
    db_session.commit()

    result = import_rows(
        db_session,
        "content-items",
        [
            row_for(
                "content-items",
                id=str(item.id),
                section_slug="edge-item-noop",
                title_en="One",
                sort_order="",
                is_active="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 0


def test_an_event_update_with_no_changes_writes_nothing(db_session):
    event = SpecialEvent(date="2030-02-01", title_en="Party", is_active=True)
    db_session.add(event)
    db_session.commit()

    result = import_rows(
        db_session,
        "special-events",
        [
            row_for(
                "special-events",
                id=str(event.id),
                date="2030-02-01",
                title_en="Party",
                is_active="true",
            )
        ],
    )

    assert result.ok
    assert result.updated == 0
