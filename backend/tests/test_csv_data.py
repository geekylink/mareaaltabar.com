"""CSV export and import (ticket #56).

The contract these tests pin is safety: a downloadable file must round-trip,
and a file with one bad row must change nothing. Import is not a second admin
API — it is a spreadsheet edit of the same rows, with the same validators and
the same audit trail.
"""

import csv
import io

import pytest
from sqlalchemy import select

from app.models import (
    AuditEntry,
    ContentItem,
    ContentSection,
    MenuCategory,
    MenuItem,
    MenuItemPromo,
    SpecialEvent,
)


def export(client, key):
    response = client.get(f"/admin/data/{key}.csv")
    assert response.status_code == 200, response.text
    return response.content.decode("utf-8-sig")


def read_rows(text):
    reader = csv.DictReader(io.StringIO(text))
    return list(reader.fieldnames or []), list(reader)


def write_rows(columns, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def import_csv(client, csrf_token, key, text):
    return client.post(
        "/admin/data/import",
        data={"dataset": key, "csrf_token": csrf_token},
        files={"file": ("data.csv", text.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )


def item_by_name(db, name):
    return db.execute(select(MenuItem).where(MenuItem.name_en == name)).scalar_one()


# --- Access and the page ---------------------------------------------------


def test_the_data_page_requires_a_session(client):
    assert client.get("/admin/data").status_code == 401


def test_exports_require_a_session(client):
    assert client.get("/admin/data/menu-items.csv").status_code == 401


def test_the_page_lists_every_table_with_a_download_link(client, auth_cookies):
    body = client.get("/admin/data").text

    for key in (
        "menu-categories",
        "menu-items",
        "menu-promos",
        "content-sections",
        "content-items",
        "special-events",
        "reservations",
    ):
        assert f'href="/admin/data/{key}.csv"' in body
    assert 'action="/admin/data/import"' in body
    assert 'name="csrf_token"' in body


def test_an_unknown_export_is_a_404(client, auth_cookies):
    assert client.get("/admin/data/nope.csv").status_code == 404


# --- Export shape ----------------------------------------------------------


def test_the_menu_export_has_the_expected_header_and_seeded_rows(client, auth_cookies):
    text = export(client, "menu-items")
    columns, rows = read_rows(text)

    assert columns[:4] == ["id", "category_slug", "name_en", "name_es"]
    pilsener = next(row for row in rows if row["name_en"] == "Pilsener")
    assert pilsener["category_slug"] == "cerveza"
    assert pilsener["price"] == "3.00"
    assert pilsener["is_available"] == "true"


def test_the_export_is_utf8_with_a_bom_for_excel(client, auth_cookies):
    raw = client.get("/admin/data/menu-categories.csv").content
    assert raw.startswith(b"\xef\xbb\xbf")
    assert "Cerveza" in raw.decode("utf-8-sig")


def test_reservations_are_exported_but_not_importable(client, auth_cookies, csrf_token):
    assert client.get("/admin/data/reservations.csv").status_code == 200

    response = import_csv(client, csrf_token, "reservations", "id,date,time\n")
    assert response.status_code == 400
    assert "export-only" in response.text


# --- Import behaviour ------------------------------------------------------


def test_a_round_trip_updates_a_menu_item(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "menu-items"))
    pilsener = next(row for row in rows if row["name_en"] == "Pilsener")
    pilsener["price"] = "3.75"

    response = import_csv(client, csrf_token, "menu-items", write_rows(columns, rows))

    assert response.status_code == 303
    assert item_by_name(db_session, "Pilsener").price == "3.75"
    entry = db_session.execute(
        select(AuditEntry).where(AuditEntry.area == "menu", AuditEntry.action == "update")
    ).scalars().first()
    assert entry is not None
    assert entry.details["price"] == {"from": "3.00", "to": "3.75"}


def test_a_blank_id_creates_a_new_menu_item(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "menu-items"))
    rows.append(
        {
            "id": "",
            "category_slug": "cerveza",
            "name_en": "New Lager",
            "name_es": "Cerveza Nueva",
            "description_en": "A test beer.",
            "description_es": "",
            "ingredients_en": "",
            "ingredients_es": "",
            "price": "4.25",
            "sort_order": "",
            "is_available": "true",
            "is_drink_of_day": "false",
        }
    )

    response = import_csv(client, csrf_token, "menu-items", write_rows(columns, rows))

    assert response.status_code == 303
    created = item_by_name(db_session, "New Lager")
    assert created.price == "4.25"
    assert created.category.slug == "cerveza"


def test_one_bad_row_aborts_the_whole_file(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "menu-items"))
    pilsener = next(row for row in rows if row["name_en"] == "Pilsener")
    pilsener["price"] = "9.99"
    rows.append(
        {
            "id": "",
            "category_slug": "does-not-exist",
            "name_en": "Ghost Drink",
            "name_es": "",
            "description_en": "",
            "description_es": "",
            "ingredients_en": "",
            "ingredients_es": "",
            "price": "1.00",
            "sort_order": "",
            "is_available": "true",
            "is_drink_of_day": "false",
        }
    )
    before = len(db_session.execute(select(MenuItem)).scalars().all())

    response = import_csv(client, csrf_token, "menu-items", write_rows(columns, rows))

    assert response.status_code == 400
    assert "no category with slug" in response.text
    assert "does-not-exist" in response.text
    assert item_by_name(db_session, "Pilsener").price == "3.00"
    assert len(db_session.execute(select(MenuItem)).scalars().all()) == before


def test_an_unknown_id_is_rejected(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "menu-items"))
    rows.append(
        {
            "id": "999999",
            "category_slug": "cerveza",
            "name_en": "Ghost",
            "name_es": "",
            "description_en": "",
            "description_es": "",
            "ingredients_en": "",
            "ingredients_es": "",
            "price": "",
            "sort_order": "",
            "is_available": "true",
            "is_drink_of_day": "false",
        }
    )

    response = import_csv(client, csrf_token, "menu-items", write_rows(columns, rows))

    assert response.status_code == 400
    assert "no menu item with id" in response.text
    assert "999999" in response.text


def test_removing_a_row_from_the_file_does_not_delete_it(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "menu-items"))
    rows = [row for row in rows if row["name_en"] != "Pilsener"]

    response = import_csv(client, csrf_token, "menu-items", write_rows(columns, rows))

    assert response.status_code == 303
    assert item_by_name(db_session, "Pilsener") is not None


def test_only_one_row_can_be_the_drink_of_the_day(client, auth_cookies, csrf_token):
    columns, rows = read_rows(export(client, "menu-items"))
    first, second = rows[0], rows[1]
    first["is_drink_of_day"] = "true"
    second["is_drink_of_day"] = "true"

    response = import_csv(client, csrf_token, "menu-items", write_rows(columns, rows))

    assert response.status_code == 400
    assert "only one row can be the drink of the day" in response.text


def test_setting_the_drink_of_the_day_clears_the_others(client, auth_cookies, csrf_token, db_session):
    first = db_session.execute(select(MenuItem).order_by(MenuItem.id)).scalars().first()
    first.is_drink_of_day = True
    db_session.commit()

    columns, rows = read_rows(export(client, "menu-items"))
    # Leave the old featured row out of the file entirely: importing another
    # row as the featured drink must still clear it.
    rows = [row for row in rows if row["id"] != str(first.id)]
    target = next(row for row in rows if row["name_en"] == "Pilsener")
    target["is_drink_of_day"] = "true"

    response = import_csv(client, csrf_token, "menu-items", write_rows(columns, rows))

    assert response.status_code == 303
    db_session.expire_all()
    flagged = db_session.execute(
        select(MenuItem).where(MenuItem.is_drink_of_day.is_(True))
    ).scalars().all()
    assert [row.name_en for row in flagged] == ["Pilsener"]


def test_a_missing_column_is_a_file_error(client, auth_cookies, csrf_token):
    response = import_csv(client, csrf_token, "menu-items", "id,name_en\n1,Pilsener\n")

    assert response.status_code == 400
    assert "Missing column" in response.text


def test_the_csrf_token_is_required(client, auth_cookies):
    response = client.post(
        "/admin/data/import",
        data={"dataset": "menu-items"},
        files={"file": ("data.csv", b"id\n", "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_an_empty_file_is_rejected(client, auth_cookies, csrf_token):
    response = import_csv(client, csrf_token, "menu-items", "")
    assert response.status_code == 400
    assert "empty" in response.text.lower()


# --- Categories and content ------------------------------------------------


def test_a_category_round_trip_updates_by_slug(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "menu-categories"))
    beer = next(row for row in rows if row["slug"] == "cerveza")
    beer["name_es"] = "Cervezas"

    response = import_csv(client, csrf_token, "menu-categories", write_rows(columns, rows))

    assert response.status_code == 303
    db_session.expire_all()
    assert db_session.execute(
        select(MenuCategory).where(MenuCategory.slug == "cerveza")
    ).scalar_one().name_es == "Cervezas"


def test_a_promo_round_trip_updates_by_id(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "menu-promos"))
    assert rows
    promo = rows[0]
    promo["label_en"] = "6 for $7.00"

    response = import_csv(client, csrf_token, "menu-promos", write_rows(columns, rows))

    assert response.status_code == 303
    db_session.expire_all()
    assert db_session.get(MenuItemPromo, int(promo["id"])).label_en == "6 for $7.00"


def test_a_content_section_can_be_created_by_slug(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "content-sections"))
    rows.append(
        {
            "slug": "about",
            "title_en": "About",
            "title_es": "Nosotros",
            "body_en": "Our story.",
            "body_es": "",
            "sort_order": "",
            "is_active": "true",
        }
    )

    response = import_csv(client, csrf_token, "content-sections", write_rows(columns, rows))

    assert response.status_code == 303
    section = db_session.execute(
        select(ContentSection).where(ContentSection.slug == "about")
    ).scalar_one()
    assert section.title_en == "About"


def test_a_content_item_can_be_created_by_section_slug(client, auth_cookies, csrf_token, db_session):
    section = ContentSection(slug="about", title_en="About", title_es="Nosotros")
    db_session.add(section)
    db_session.commit()

    columns = [
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
    ]
    text = write_rows(
        columns,
        [
            {
                "id": "",
                "section_slug": "about",
                "title_en": "Our story",
                "title_es": "Nuestra historia",
                "body_en": "We opened in 2019.",
                "body_es": "",
                "price": "",
                "image_url": "",
                "starts_on": "",
                "ends_on": "",
                "sort_order": "",
                "is_active": "true",
            }
        ],
    )

    response = import_csv(client, csrf_token, "content-items", text)

    assert response.status_code == 303
    created = db_session.execute(
        select(ContentItem).where(ContentItem.title_en == "Our story")
    ).scalar_one()
    assert created.section_id == section.id


def test_a_content_item_with_an_unknown_section_is_rejected(client, auth_cookies, csrf_token):
    columns = [
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
    ]
    text = write_rows(
        columns,
        [
            {
                "id": "",
                "section_slug": "nope",
                "title_en": "Story",
                "title_es": "",
                "body_en": "",
                "body_es": "",
                "price": "",
                "image_url": "",
                "starts_on": "",
                "ends_on": "",
                "sort_order": "",
                "is_active": "true",
            }
        ],
    )

    response = import_csv(client, csrf_token, "content-items", text)

    assert response.status_code == 400
    assert "no section with slug" in response.text
    assert "nope" in response.text


# --- Special events --------------------------------------------------------


def test_a_past_event_can_be_imported_for_correction(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "special-events"))
    rows.append(
        {
            "id": "",
            "date": "2000-01-01",
            "title_en": "Old Party",
            "title_es": "",
            "description_en": "",
            "description_es": "",
            "start_time": "",
            "end_time": "",
            "image_url": "",
            "is_active": "true",
        }
    )

    response = import_csv(client, csrf_token, "special-events", write_rows(columns, rows))

    assert response.status_code == 303
    assert db_session.execute(
        select(SpecialEvent).where(SpecialEvent.title_en == "Old Party")
    ).scalar_one() is not None


def test_an_event_with_only_one_time_is_rejected(client, auth_cookies, csrf_token):
    columns, rows = read_rows(export(client, "special-events"))
    rows.append(
        {
            "id": "",
            "date": "2030-01-01",
            "title_en": "Half a window",
            "title_es": "",
            "description_en": "",
            "description_es": "",
            "start_time": "21:00",
            "end_time": "",
            "image_url": "",
            "is_active": "true",
        }
    )

    response = import_csv(client, csrf_token, "special-events", write_rows(columns, rows))

    assert response.status_code == 400
    assert "set both start_time and end_time" in response.text


def test_an_event_with_a_bad_url_is_rejected(client, auth_cookies, csrf_token):
    columns, rows = read_rows(export(client, "special-events"))
    rows.append(
        {
            "id": "",
            "date": "2030-01-01",
            "title_en": "Bad image",
            "title_es": "",
            "description_en": "",
            "description_es": "",
            "start_time": "",
            "end_time": "",
            "image_url": "javascript:alert(1)",
            "is_active": "true",
        }
    )

    response = import_csv(client, csrf_token, "special-events", write_rows(columns, rows))

    assert response.status_code == 400
    assert "image_url" in response.text


# --- Audit -----------------------------------------------------------------


def test_an_import_writes_one_audit_row_per_changed_row(client, auth_cookies, csrf_token, db_session):
    columns, rows = read_rows(export(client, "menu-categories"))
    beer = next(row for row in rows if row["slug"] == "cerveza")
    beer["name_en"] = "Beers"

    before = db_session.execute(
        select(AuditEntry).where(AuditEntry.area == "menu")
    ).scalars().all()

    response = import_csv(client, csrf_token, "menu-categories", write_rows(columns, rows))

    assert response.status_code == 303
    after = db_session.execute(
        select(AuditEntry).where(AuditEntry.area == "menu")
    ).scalars().all()
    assert len(after) == len(before) + 1
    entry = after[-1]
    assert entry.action == "update"
    assert entry.details["name_en"] == {"from": "Beer", "to": "Beers"}


@pytest.mark.parametrize("value, expected", [("TRUE", "true"), ("0", "false"), ("yes", "true")])
def test_boolean_spellings_are_accepted(client, auth_cookies, csrf_token, db_session, value, expected):
    columns, rows = read_rows(export(client, "menu-categories"))
    beer = next(row for row in rows if row["slug"] == "cerveza")
    beer["is_available"] = value

    response = import_csv(client, csrf_token, "menu-categories", write_rows(columns, rows))

    assert response.status_code == 303
    db_session.expire_all()
    stored = db_session.execute(
        select(MenuCategory).where(MenuCategory.slug == "cerveza")
    ).scalar_one()
    assert ("true" if stored.is_available else "false") == expected
