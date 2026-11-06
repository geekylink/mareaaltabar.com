"""Tests for generic content sections and items (ticket #17).

The thing worth guarding is the public/admin split: an expired row must vanish
from the site without vanishing from the panel. The rest is ordinary CRUD plus
the audit trail that every write has to leave.
"""

import pytest
from sqlalchemy import select

from app.models import ContentItem, ContentSection
from app.ssr import load_content


@pytest.fixture()
def edit_as_admin(client, auth_cookies, csrf_token):
    def _edit(method, url, **kwargs):
        return client.request(method, url, headers={"X-CSRF-Token": csrf_token}, **kwargs)

    return _edit


def make_section(edit_as_admin, **over):
    payload = {
        "slug": "",
        "title_en": "About us",
        "title_es": "Sobre nosotros",
        "body_en": "A bar on the beach.",
        "body_es": "Un bar en la playa.",
        "is_active": True,
    }
    payload.update(over)
    resp = edit_as_admin("POST", "/api/content/sections", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_item(edit_as_admin, section_id, **over):
    payload = {
        "section_id": section_id,
        "title_en": "Row",
        "title_es": "Fila",
        "body_en": "",
        "body_es": "",
        "price": "",
        "image_url": "",
        "starts_on": "",
        "ends_on": "",
        "is_active": True,
    }
    payload.update(over)
    resp = edit_as_admin("POST", "/api/content/items", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Public and admin reads ------------------------------------------------


def test_content_is_empty_until_something_is_published(client):
    resp = client.get("/api/content")
    assert resp.status_code == 200
    assert resp.json() == []


def test_a_section_with_an_item_appears_publicly(client, edit_as_admin):
    section = make_section(edit_as_admin)
    make_item(edit_as_admin, section["id"], title_en="Package", title_es="Paquete", price="25")

    public = client.get("/api/content").json()
    assert len(public) == 1
    assert public[0]["slug"] == "about-us"
    assert public[0]["items"][0]["title_en"] == "Package"
    assert public[0]["items"][0]["price"] == "25"
    assert public[0]["items"][0]["is_live"] is True


def test_an_empty_section_is_not_published(client, edit_as_admin):
    """A heading with nothing under it is worse than no heading."""
    make_section(edit_as_admin)
    assert client.get("/api/content").json() == []


def test_a_section_can_be_fetched_by_slug(client, edit_as_admin):
    section = make_section(edit_as_admin, slug="packages")
    make_item(edit_as_admin, section["id"])

    assert client.get("/api/content/packages").json()["slug"] == "packages"
    assert client.get("/api/content/nope").status_code == 404


def test_public_read_filters_inactive_sections_and_items(client, edit_as_admin):
    visible = make_section(edit_as_admin, title_en="Visible")
    hidden = make_section(edit_as_admin, title_en="Hidden", is_active=False)
    make_item(edit_as_admin, visible["id"], title_en="Show me")
    make_item(edit_as_admin, visible["id"], title_en="Hide me", is_active=False)
    make_item(edit_as_admin, hidden["id"], title_en="Under a hidden section")

    public = client.get("/api/content").json()
    assert [s["title_en"] for s in public] == ["Visible"]
    assert [i["title_en"] for i in public[0]["items"]] == ["Show me"]


def test_the_admin_read_keeps_switched_off_rows(client, edit_as_admin):
    hidden = make_section(edit_as_admin, title_en="Hidden", is_active=False)
    make_item(edit_as_admin, hidden["id"], title_en="Hide me", is_active=False)

    admin = client.get("/api/content/all").json()
    assert len(admin) == 1
    assert admin[0]["is_active"] is False
    assert len(admin[0]["items"]) == 1
    assert admin[0]["items"][0]["is_live"] is False


def test_the_admin_read_requires_a_session(client):
    assert client.get("/api/content/all").status_code == 401


# --- Date windows ----------------------------------------------------------


def test_a_future_item_is_hidden_but_an_expired_item_is_too(client, edit_as_admin):
    section = make_section(edit_as_admin)
    make_item(edit_as_admin, section["id"], title_en="Future", starts_on="2099-01-01")
    make_item(edit_as_admin, section["id"], title_en="Expired", ends_on="2000-01-01")
    make_item(edit_as_admin, section["id"], title_en="Current")

    titles = [i["title_en"] for i in client.get("/api/content").json()[0]["items"]]
    assert titles == ["Current"]


def test_a_date_window_is_inclusive(db_session):
    section = ContentSection(slug="window", title_en="Window", is_active=True)
    section.items.append(ContentItem(title_en="Edge", starts_on="2026-11-06", ends_on="2026-11-06"))
    db_session.add(section)
    db_session.commit()

    live = load_content(db_session, today="2026-11-06")
    assert live[0]["items"][0]["is_live"] is True

    # Outside the window the section has no live rows, so the public read drops
    # the heading entirely; the admin read keeps both so it stays editable.
    assert load_content(db_session, today="2026-11-05") == []
    admin = load_content(db_session, include_inactive=True, today="2026-11-05")
    assert admin[0]["items"][0]["is_live"] is False


def test_an_end_before_the_start_is_rejected(client, edit_as_admin):
    section = make_section(edit_as_admin)
    resp = edit_as_admin(
        "POST",
        "/api/content/items",
        json={
            "section_id": section["id"],
            "title_en": "Wrong",
            "starts_on": "2026-11-30",
            "ends_on": "2026-11-01",
        },
    )
    assert resp.status_code == 422


def test_an_image_must_be_an_http_or_site_relative_url(client, edit_as_admin):
    section = make_section(edit_as_admin)
    resp = edit_as_admin(
        "POST",
        "/api/content/items",
        json={"section_id": section["id"], "title_en": "Bad", "image_url": "javascript:alert(1)"},
    )
    assert resp.status_code == 422


def test_a_site_relative_image_is_accepted(client, edit_as_admin):
    section = make_section(edit_as_admin)
    item = make_item(edit_as_admin, section["id"], image_url="/icons/favicon.svg")
    assert item["image_url"] == "/icons/favicon.svg"


# --- Writes ----------------------------------------------------------------


def test_a_blank_slug_is_derived_from_the_title(client, edit_as_admin):
    section = make_section(edit_as_admin, title_en="Our Packages", title_es="")
    assert section["slug"] == "our-packages"


def test_two_sections_cannot_share_a_slug(client, edit_as_admin):
    make_section(edit_as_admin, slug="about")
    resp = edit_as_admin(
        "POST",
        "/api/content/sections",
        json={"title_en": "Other", "slug": "about"},
    )
    assert resp.status_code == 409


def test_a_section_update_keeps_its_items(client, edit_as_admin):
    section = make_section(edit_as_admin)
    make_item(edit_as_admin, section["id"], title_en="Kept")

    resp = edit_as_admin(
        "PUT",
        f"/api/content/sections/{section['id']}",
        json={**section, "title_en": "Renamed"},
    )
    assert resp.status_code == 200
    assert resp.json()["title_en"] == "Renamed"
    assert [i["title_en"] for i in resp.json()["items"]] == ["Kept"]


def test_an_item_can_move_to_another_section(client, edit_as_admin):
    first = make_section(edit_as_admin, title_en="First")
    second = make_section(edit_as_admin, title_en="Second")
    item = make_item(edit_as_admin, first["id"], title_en="Mover")

    resp = edit_as_admin(
        "PUT",
        f"/api/content/items/{item['id']}",
        json={**item, "section_id": second["id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["section_id"] == second["id"]


def test_deleting_a_section_deletes_its_items(client, edit_as_admin, db_session):
    section = make_section(edit_as_admin)
    make_item(edit_as_admin, section["id"])

    assert edit_as_admin("DELETE", f"/api/content/sections/{section['id']}").status_code == 204
    assert db_session.execute(select(ContentItem)).scalars().all() == []


def test_a_write_needs_a_csrf_token(client, auth_cookies):
    resp = client.post("/api/content/sections", json={"title_en": "No token"})
    assert resp.status_code == 403


# --- Audit -----------------------------------------------------------------


def test_content_writes_are_logged(client, edit_as_admin):
    section = make_section(edit_as_admin)
    item = make_item(edit_as_admin, section["id"])
    edit_as_admin("DELETE", f"/api/content/items/{item['id']}")

    resp = client.get("/api/logs/content")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    assert resp.json()["total"] == 3
    assert {entry["action"] for entry in entries} == {"create", "delete"}
    assert {entry["target"].split(":")[0] for entry in entries} == {"content_section", "content_item"}


# --- Admin page ------------------------------------------------------------


def test_the_content_page_needs_a_session(client):
    assert client.get("/admin/content").status_code == 401


def test_the_content_page_renders_for_an_admin(client, auth_cookies):
    body = client.get("/admin/content").text
    assert "/api/content/all" in body
    assert "admin_i18n.js" in body
    assert "content_heading" in body
