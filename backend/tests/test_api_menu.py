"""Tests for the drinks menu API (ticket #1).

Two things are worth guarding here. First, the menu is the one endpoint the
public site reads that the admin panel must be able to *hide* rows from — so the
split between the public read and the admin read is the part most likely to rot.
Second, promos are replaced rather than merged, because the panel edits the whole
set in one request; a bug there would silently delete an offer.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import MenuItem, MenuItemPromo
from app.ssr import load_menu, promo_is_live


@pytest.fixture()
def edit_as_admin(client, auth_cookies, csrf_token):
    """Return a helper that performs an authenticated admin write."""

    def _edit(method, url, **kwargs):
        return client.request(method, url, headers={"X-CSRF-Token": csrf_token}, **kwargs)

    return _edit


def categories(client):
    return client.get("/api/menu").json()["categories"]


def find_item(client, name_en):
    for category in categories(client):
        for item in category["items"]:
            if item["name_en"] == name_en:
                return category, item
    raise AssertionError(f"{name_en!r} is not on the menu")


# --- The public read -------------------------------------------------------


def test_menu_is_public(client):
    """The site fetches this with no session, like the schedule."""
    resp = client.get("/api/menu")
    assert resp.status_code == 200
    assert resp.json()["categories"]


def test_menu_is_not_cached(client):
    """An admin edit has to reach a crawler on its next visit."""
    assert client.get("/api/menu").headers["cache-control"] == "no-cache"


def test_menu_carries_both_languages(client):
    _, beer = find_item(client, "Pilsener Can")
    assert beer["name_en"] == "Pilsener Can"
    assert beer["name_es"] == "Pilsener Lata"


def test_seeded_prices_and_promos_reach_visitors(client):
    """docs/bar_menu.md, transcribed: main price first, promo underneath."""
    _, can = find_item(client, "Pilsener Can")
    assert can["price"] == "1.50"
    assert [p["label_en"] for p in can["promos"]] == ["6x $7.00"]
    assert can["promos"][0]["label_es"] == "6 por $7.00"


def test_cocktail_seeded_with_its_ingredients(client):
    category, cuba = find_item(client, "Cuba Libre")
    assert category["name_en"] == "Cocktails"
    assert cuba["price"] == "4.00"
    assert cuba["ingredients_en"] == "Rum, Coca-Cola, Lime juice, Ice"
    assert cuba["ingredients_es"] == "Ron, Coca-Cola, Jugo de limón, Hielo"


def test_empty_categories_are_not_published(client):
    """Wine and liquor are seeded empty; a bare heading is worse than nothing."""
    assert "vinos" not in [c["slug"] for c in categories(client)]


def test_menu_is_ordered(client):
    slugs = [c["slug"] for c in categories(client)]
    assert slugs == ["cerveza", "otras-bebidas", "cigarrillos", "cocteles"]


# --- Availability ----------------------------------------------------------


def test_hidden_item_is_withdrawn_from_the_public_menu(client, edit_as_admin):
    """The reversible alternative to deleting a sold-out drink."""
    _, item = find_item(client, "Corona")
    edit_as_admin(
        "PUT",
        f"/api/menu/items/{item['id']}",
        json={**item, "is_available": False, "promos": []},
    )
    with pytest.raises(AssertionError):
        find_item(client, "Corona")


def test_hidden_item_is_still_editable_by_an_admin(client, edit_as_admin):
    """If the panel could not see it, it could never be switched back on."""
    _, item = find_item(client, "Corona")
    edit_as_admin(
        "PUT",
        f"/api/menu/items/{item['id']}",
        json={**item, "is_available": False, "promos": []},
    )

    everything = client.get("/api/menu/all").json()["categories"]
    hidden = next(i for c in everything for i in c["items"] if i["name_en"] == "Corona")
    assert hidden["is_available"] is False


def test_hidden_category_is_withdrawn(client, edit_as_admin):
    category = categories(client)[0]
    edit_as_admin(
        "PATCH",
        f"/api/menu/categories/{category['id']}",
        json={"name_en": category["name_en"], "name_es": category["name_es"],
              "slug": category["slug"], "is_available": False},
    )
    assert "cerveza" not in [c["slug"] for c in categories(client)]


def test_the_admin_read_needs_a_session(client):
    assert client.get("/api/menu/all").status_code == 401


# --- Writes are guarded ----------------------------------------------------


def test_writes_are_closed_to_anonymous_callers(client):
    assert client.post("/api/menu/items", json={"category_id": 1, "name_en": "x"}).status_code == 401
    assert client.post("/api/menu/categories", json={"name_en": "x"}).status_code == 401


def test_writes_are_closed_without_a_csrf_token(client, auth_cookies):
    """A logged-in session is not enough; the token is the second half."""
    assert client.post(
        "/api/menu/categories", json={"name_en": "x", "name_es": "y"}
    ).status_code == 403


def test_writes_reject_an_unknown_category(client, edit_as_admin):
    resp = edit_as_admin("POST", "/api/menu/items", json={"category_id": 9999, "name_en": "x"})
    assert resp.status_code == 400


def test_writes_reject_an_item_with_no_english_name(client, edit_as_admin):
    resp = edit_as_admin("POST", "/api/menu/items", json={"category_id": 1, "name_es": "Sin nombre"})
    assert resp.status_code == 422


def test_editing_an_unknown_item_is_a_404(client, edit_as_admin):
    assert edit_as_admin("PUT", "/api/menu/items/4242", json={"category_id": 1, "name_en": "x"}).status_code == 404


def test_editing_an_unknown_category_is_a_404(client, edit_as_admin):
    assert edit_as_admin("PATCH", "/api/menu/categories/4242", json={"name_en": "x"}).status_code == 404


# --- Category lifecycle ----------------------------------------------------


def test_adding_a_category(client, edit_as_admin):
    resp = edit_as_admin(
        "POST",
        "/api/menu/categories",
        json={"name_en": "Food", "name_es": "Comida", "slug": "", "is_available": True},
    )
    assert resp.status_code == 201
    # A blank slug is derived from the name, so the anchor always exists.
    assert resp.json()["slug"] == "food"

    resp = edit_as_admin(
        "POST",
        "/api/menu/items",
        json={"category_id": resp.json()["id"], "name_en": "Ceviche", "price": "6.00"},
    )
    assert resp.status_code == 201
    assert find_item(client, "Ceviche")[0]["slug"] == "food"


def test_a_duplicate_slug_is_refused(client, edit_as_admin):
    resp = edit_as_admin("POST", "/api/menu/categories", json={"name_en": "Beer", "slug": "cerveza"})
    assert resp.status_code == 409


def test_renaming_a_category_reaches_visitors(client, edit_as_admin):
    category = categories(client)[0]
    resp = edit_as_admin(
        "PATCH",
        f"/api/menu/categories/{category['id']}",
        json={"name_en": "Cold Beer", "name_es": "Cerveza fría",
              "slug": category["slug"], "is_available": True},
    )
    assert resp.status_code == 200
    assert categories(client)[0]["name_en"] == "Cold Beer"
    assert categories(client)[0]["name_es"] == "Cerveza fría"


def test_deleting_a_category_takes_its_drinks_with_it(client, edit_as_admin, db_session):
    category = categories(client)[-1]
    drink_ids = [i["id"] for i in category["items"]]

    assert edit_as_admin("DELETE", f"/api/menu/categories/{category['id']}").status_code == 204

    assert "cocteles" not in [c["slug"] for c in categories(client)]
    # And the rows are really gone, not just unlinked.
    assert db_session.execute(select(MenuItem).where(MenuItem.id.in_(drink_ids))).scalars().all() == []
    # The beer promos are untouched: the cascade stops at the deleted category.
    assert db_session.execute(select(MenuItemPromo)).scalars().all() != []
    assert edit_as_admin("DELETE", f"/api/menu/categories/{category['id']}").status_code == 404


def test_categories_can_be_reordered(client, edit_as_admin):
    """The panel swaps both rows, which is what makes the new order stick."""
    first, second = categories(client)[0], categories(client)[1]

    def move(cat, order):
        return edit_as_admin(
            "PATCH",
            f"/api/menu/categories/{cat['id']}",
            json={"name_en": cat["name_en"], "name_es": cat["name_es"],
                  "slug": cat["slug"], "is_available": True, "sort_order": order},
        )

    assert move(first, second["sort_order"]).status_code == 200
    assert move(second, first["sort_order"]).status_code == 200

    assert [c["id"] for c in categories(client)][:2] == [second["id"], first["id"]]


def test_renaming_a_category_leaves_its_position_alone(client, edit_as_admin):
    """Sort order is optional on a write, so a rename cannot resequence the menu."""
    before = [c["id"] for c in categories(client)]
    category = categories(client)[0]
    edit_as_admin(
        "PATCH",
        f"/api/menu/categories/{category['id']}",
        json={"name_en": "Renamed", "name_es": "Renombrada", "slug": category["slug"],
              "is_available": True},
    )
    assert [c["id"] for c in categories(client)] == before


# --- Item lifecycle --------------------------------------------------------


def test_adding_a_drink(client, edit_as_admin):
    category = categories(client)[-1]
    resp = edit_as_admin(
        "POST",
        "/api/menu/items",
        json={
            "category_id": category["id"],
            "name_en": "Margarita",
            "name_es": "Margarita",
            "price": "5.00",
            "ingredients_en": "Tequila, Lime, Triple sec",
            "ingredients_es": "Tequila, Limón, Triple seco",
            "promos": [{"label_en": "2x1 Tuesdays", "label_es": "2x1 martes"}],
        },
    )
    assert resp.status_code == 201

    _, margarita = find_item(client, "Margarita")
    assert margarita["price"] == "5.00"
    assert margarita["ingredients_es"] == "Tequila, Limón, Triple seco"
    assert [p["label_en"] for p in margarita["promos"]] == ["2x1 Tuesdays"]


def test_editing_a_drink_reaches_visitors(client, edit_as_admin):
    _, item = find_item(client, "Corona")
    edit_as_admin(
        "PUT",
        f"/api/menu/items/{item['id']}",
        json={**item, "name_es": "Corona chica", "price": "4.50", "promos": []},
    )
    _, edited = find_item(client, "Corona")
    assert edited["name_es"] == "Corona chica"
    assert edited["price"] == "4.50"


def test_a_drink_can_move_between_categories(client, edit_as_admin):
    cocktails = categories(client)[-1]
    _, item = find_item(client, "Lemonade")
    edit_as_admin(
        "PUT", f"/api/menu/items/{item['id']}", json={**item, "category_id": cocktails["id"]}
    )
    assert find_item(client, "Lemonade")[0]["slug"] == "cocteles"


def test_editing_a_price_leaves_its_promos_alone(client, edit_as_admin):
    """An ordinary save must not drop the offers sitting under the price."""
    before = [i["name_en"] for i in categories(client)[0]["items"]]
    _, item = find_item(client, "Corona")
    edit_as_admin("PUT", f"/api/menu/items/{item['id']}", json={**item, "price": "4.50"})
    assert [i["name_en"] for i in categories(client)[0]["items"]] == before


def test_promos_are_replaced_not_merged(client, edit_as_admin):
    """The panel sends the whole set, so removing the last one has to work."""
    _, can = find_item(client, "Pilsener Can")
    edit_as_admin("PUT", f"/api/menu/items/{can['id']}", json={**can, "promos": []})
    assert find_item(client, "Pilsener Can")[1]["promos"] == []


def test_an_item_can_carry_several_promos(client, edit_as_admin):
    _, item = find_item(client, "Corona")
    edit_as_admin(
        "PUT",
        f"/api/menu/items/{item['id']}",
        json={**item, "promos": [
            {"label_en": "3x $10.00", "label_es": "3 por $10.00"},
            {"label_en": "Bucket $18.00", "label_es": "Caneca $18.00"},
        ]},
    )
    promos = find_item(client, "Corona")[1]["promos"]
    assert [p["label_en"] for p in promos] == ["3x $10.00", "Bucket $18.00"]


def test_removing_a_drink(client, edit_as_admin):
    _, item = find_item(client, "Corona")
    assert edit_as_admin("DELETE", f"/api/menu/items/{item['id']}").status_code == 204
    with pytest.raises(AssertionError):
        find_item(client, "Corona")
    assert edit_as_admin("DELETE", f"/api/menu/items/{item['id']}").status_code == 404


# --- The admin page --------------------------------------------------------


def test_the_menu_page_needs_a_session(client):
    assert client.get("/admin/menu").status_code == 401


def test_the_menu_page_renders_for_a_signed_in_admin(client, auth_cookies):
    resp = client.get("/admin/menu")
    assert resp.status_code == 200
    body = resp.text
    # It has to be wired to the admin read, or it would show the public one and
    # never see a drink that has been switched off.
    assert "/api/menu/all" in body
    assert 'id="add-category"' in body


def test_the_dashboard_offers_the_menu(client, auth_cookies):
    body = client.get("/admin").text
    assert 'href="/admin/menu"' in body
    assert "card_menu_title" in body


# --- The loader the rendered pages share -----------------------------------


def test_the_api_and_the_loader_agree(db_session):
    """`/api/menu` and the crawler-visible HTML cannot publish different menus."""
    menu = load_menu(db_session)
    assert [c["slug"] for c in menu] == ["cerveza", "otras-bebidas", "cigarrillos", "cocteles"]
    assert len(menu[0]["items"]) == 7


# --- Happy-hour windows ----------------------------------------------------
#
# Promos are now offers that can be scheduled. The bar clock is injectable so
# these tests pin a Friday afternoon instead of depending on when the suite runs.
# 2026-11-06 is a Friday.

BAR_TZ = timezone(timedelta(hours=-5))


def at(value):
    return datetime.fromisoformat(value).replace(tzinfo=BAR_TZ)


def promo(**over):
    fields = {
        "menu_item_id": 1,
        "label_en": "Offer",
        "label_es": "Oferta",
        "days": "",
        "start_time": "",
        "end_time": "",
        "starts_on": "",
        "ends_on": "",
        "is_active": True,
    }
    fields.update(over)
    return MenuItemPromo(**fields)


def find_admin_item(client, name_en):
    for category in client.get("/api/menu/all").json()["categories"]:
        for item in category["items"]:
            if item["name_en"] == name_en:
                return item
    raise AssertionError(f"{name_en!r} is not on the admin menu")


def test_a_promo_with_no_window_is_always_live():
    """The pre-happy-hour shape: every blank window means "on the menu"."""
    assert promo_is_live(promo(), at("2026-11-06T12:00"))


def test_an_inactive_promo_is_never_live():
    assert not promo_is_live(promo(is_active=False), at("2026-11-06T12:00"))


def test_a_weekday_window_uses_the_bar_calendar():
    fridays = promo(days="5")
    assert promo_is_live(fridays, at("2026-11-06T12:00"))  # Friday
    assert not promo_is_live(fridays, at("2026-11-07T12:00"))  # Saturday


def test_a_happy_hour_is_live_only_inside_its_times():
    happy_hour = promo(start_time="18:00", end_time="20:00")
    assert not promo_is_live(happy_hour, at("2026-11-06T17:59"))
    assert promo_is_live(happy_hour, at("2026-11-06T18:00"))
    assert promo_is_live(happy_hour, at("2026-11-06T19:59"))
    assert promo_is_live(happy_hour, at("2026-11-06T20:00"))
    assert not promo_is_live(happy_hour, at("2026-11-06T20:01"))


def test_an_overnight_window_belongs_to_the_evening_it_started():
    """A Friday 22:00–02:00 offer is live at 01:00 on Saturday, not Saturday night."""
    friday_night = promo(days="5", start_time="22:00", end_time="02:00")
    assert promo_is_live(friday_night, at("2026-11-06T23:00"))
    assert promo_is_live(friday_night, at("2026-11-07T01:00"))
    assert not promo_is_live(friday_night, at("2026-11-07T23:00"))
    assert not promo_is_live(friday_night, at("2026-11-06T12:00"))


def test_date_bounds_limit_the_offer():
    november = promo(starts_on="2026-11-01", ends_on="2026-11-30")
    assert not promo_is_live(november, at("2026-10-31T23:59"))
    assert promo_is_live(november, at("2026-11-01T00:00"))
    assert promo_is_live(november, at("2026-11-30T23:59"))
    assert not promo_is_live(november, at("2026-12-01T00:00"))


def test_the_public_read_hides_promos_outside_their_window(db_session):
    can = db_session.execute(
        select(MenuItem).where(MenuItem.name_en == "Pilsener Can")
    ).scalar_one()
    can.promos.append(
        MenuItemPromo(
            label_en="New Year",
            label_es="Año Nuevo",
            starts_on="2099-01-01",
            sort_order=99,
        )
    )
    db_session.commit()

    public = load_menu(db_session, now=at("2026-11-06T12:00"))
    public_can = next(i for c in public for i in c["items"] if i["name_en"] == "Pilsener Can")
    assert [p["label_en"] for p in public_can["promos"]] == ["6x $7.00"]

    admin = load_menu(db_session, include_unavailable=True, now=at("2026-11-06T12:00"))
    admin_can = next(i for c in admin for i in c["items"] if i["name_en"] == "Pilsener Can")
    scheduled = next(p for p in admin_can["promos"] if p["label_en"] == "New Year")
    assert scheduled["is_live"] is False


def test_a_paused_promo_disappears_from_the_public_menu(client, edit_as_admin):
    _, can = find_item(client, "Pilsener Can")
    edit_as_admin(
        "PUT",
        f"/api/menu/items/{can['id']}",
        json={**can, "promos": [
            {"label_en": "Paused", "label_es": "Pausada", "is_active": False},
        ]},
    )
    assert find_item(client, "Pilsener Can")[1]["promos"] == []

    paused = find_admin_item(client, "Pilsener Can")["promos"][0]
    assert paused["is_active"] is False
    assert paused["is_live"] is False


def test_a_happy_hour_round_trips_through_the_admin_api(client, edit_as_admin):
    _, can = find_item(client, "Pilsener Can")
    edit_as_admin(
        "PUT",
        f"/api/menu/items/{can['id']}",
        json={**can, "promos": [{
            "label_en": "Happy hour",
            "label_es": "Hora feliz",
            "days": "5,1,3,5",
            "start_time": "18:00",
            "end_time": "20:00",
            "starts_on": "2026-11-01",
            "ends_on": "2026-11-30",
            "is_active": True,
        }]},
    )

    saved = find_admin_item(client, "Pilsener Can")["promos"][0]
    assert saved["days"] == "1,3,5"
    assert saved["start_time"] == "18:00"
    assert saved["end_time"] == "20:00"
    assert saved["starts_on"] == "2026-11-01"
    assert saved["ends_on"] == "2026-11-30"
    assert saved["is_active"] is True


@pytest.mark.parametrize("window", [
    {"start_time": "18:00"},
    {"end_time": "20:00"},
    {"start_time": "25:00", "end_time": "26:00"},
    {"start_time": "18:00", "end_time": "18:00"},
    {"days": "7"},
    {"days": "1,x"},
    {"starts_on": "2026-13-01"},
    {"starts_on": "2026-11-30", "ends_on": "2026-11-01"},
])
def test_an_invalid_promo_window_is_rejected(client, edit_as_admin, window):
    _, item = find_item(client, "Corona")
    resp = edit_as_admin(
        "PUT",
        f"/api/menu/items/{item['id']}",
        json={**item, "promos": [{"label_en": "Offer", "label_es": "Oferta", **window}]},
    )
    assert resp.status_code == 422