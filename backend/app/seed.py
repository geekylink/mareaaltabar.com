"""Default schedule and menu data used to seed a fresh database.

Shared by the app (on startup) and the test suite so both see the same rows.
Times are stored 24-hour so the admin panel's ``<input type="time">`` can read
them; the frontend formats them for display.

The menu is a starting point, not a finished one: it is transcribed from
``docs/bar_menu.md`` so the site has real prices from the first deploy, and the
admin panel is where the rest of it gets written.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import BlogPost, Event, Hours, MenuCategory, MenuItem, MenuItemPromo
from app.ssr import bar_today

DEFAULT_EVENTS = [
    {
        "day": 0,
        "title_en": "Latin Night",
        "title_es": "Noche Latina",
        "note_en": "Salsa, bachata and reggaeton all night.",
        "note_es": "Salsa, bachata y reggaeton toda la noche.",
    },
    {
        "day": 1,
        "title_en": "Singles Night",
        "title_es": "Noche de Solteros",
        "note_en": "Mingle with the singles.",
        "note_es": "Conoce a solteros y solteras.",
    },
    {
        "day": 2,
        "title_en": "Closed",
        "title_es": "Cerrado",
        "note_en": "",
        "note_es": "",
    },
    {
        "day": 3,
        "title_en": "Closed",
        "title_es": "Cerrado",
        "note_en": "",
        "note_es": "",
    },
    {
        "day": 4,
        "title_en": "Open Mic Night",
        "title_es": "Noche de Mic Abierto",
        "note_en": "Come play music with us, bring an instrument or sing or play one of ours.",
        "note_es": "Viene a tocar música con nosotros, trae tu instrumento o canta o toca uno de los nuestros.",
    },
    {
        "day": 5,
        "title_en": "Live Music",
        "title_es": "Música en Vivo",
        "note_en": "Live music all night.",
        "note_es": "Música en vivo toda la noche.",
    },
    {
        "day": 6,
        "title_en": "Live Music",
        "title_es": "Música en Vivo",
        "note_en": "The big one. Arrive early for a spot.",
        "note_es": "El gran día. Llega temprano para conseguir lugar.",
    },
]

DEFAULT_HOURS = [
    {"day": 0, "open_time": "16:00", "close_time": "02:00", "is_closed": False},
    {"day": 1, "open_time": "16:00", "close_time": "04:00", "is_closed": False},
    {"day": 2, "open_time": "", "close_time": "", "is_closed": True},
    {"day": 3, "open_time": "", "close_time": "", "is_closed": True},
    {"day": 4, "open_time": "16:00", "close_time": "04:00", "is_closed": False},
    {"day": 5, "open_time": "16:00", "close_time": "04:00", "is_closed": False},
    {"day": 6, "open_time": "16:00", "close_time": "04:00", "is_closed": False},
]


def seed_schedule(db: DBSession) -> None:
    """Insert the default 7-day schedule if the tables are empty.

    Idempotent: safe to call on every startup. Never overwrites admin edits,
    because it only inserts when a table has no rows.
    """
    if db.execute(select(Event).limit(1)).scalar_one_or_none() is None:
        db.add_all(Event(**row) for row in DEFAULT_EVENTS)

    if db.execute(select(Hours).limit(1)).scalar_one_or_none() is None:
        db.add_all(Hours(**row) for row in DEFAULT_HOURS)

    db.commit()


# --- Menu ------------------------------------------------------------------
#
# Transcribed from docs/bar_menu.md. Each entry is keyed by its category slug so
# the ordering and the category a drink belongs to are visible in one place.
#
# `promos` holds the multi-buy offers that the source document writes inline in
# the price column — "$1.50 (6x $7.00)" becomes price "1.50" plus a promo row, so
# the headline price stays the number people actually pay for one.

DEFAULT_MENU = [
    {
        "slug": "cerveza",
        "name_en": "Beer",
        "name_es": "Cerveza",
        "items": [
            {
                "name_en": "Club Personal",
                "name_es": "Club personal",
                "price": "2.50",
            },
            {
                "name_en": "Club Large",
                "name_es": "Club grande",
                "price": "4.00",
            },
            {
                "name_en": "Corona",
                "name_es": "Corona",
                "price": "4.00",
            },
            {
                "name_en": "Pilsener",
                "name_es": "Pilsener",
                "price": "3.00",
            },
            {
                "name_en": "Pilsener Light",
                "name_es": "Pilsener Light",
                "price": "3.00",
            },
            {
                "name_en": "Pilsener Can",
                "name_es": "Pilsener Lata",
                "price": "1.50",
                "promos": [
                    {"label_en": "6x $7.00", "label_es": "6 por $7.00"},
                ],
            },
            {
                "name_en": "Pilsener Light Can",
                "name_es": "Pilsener Light Lata",
                "price": "1.50",
                "promos": [
                    {"label_en": "6x $7.00", "label_es": "6 por $7.00"},
                ],
            },
        ],
    },
    {
        "slug": "otras-bebidas",
        "name_en": "Other Drinks",
        "name_es": "Otras Bebidas",
        "items": [
            {"name_en": "Milk Coffee", "name_es": "Cafe con Leche", "price": "1.50"},
            {"name_en": "Coffee", "name_es": "Cafe", "price": "1.00"},
            {"name_en": "Lemonade", "name_es": "Limonada", "price": "1.50"},
            {"name_en": "Natural Juice", "name_es": "Jugo Natural", "price": "2.00"},
            {"name_en": "Milkshake", "name_es": "Batidos", "price": "2.50"},
            {"name_en": "Cola, Sprite, Inca", "name_es": "Cola, Sprite, Inca", "price": "1.00"},
            {"name_en": "Water", "name_es": "Agua", "price": "1.00"},
        ],
    },
    {
        "slug": "cigarrillos",
        "name_en": "Cigarettes",
        "name_es": "Cigarrillos",
        "items": [
            {
                "name_en": "Elephant",
                "name_es": "Elephant",
                "price": "0.25",
                "promos": [
                    {"label_en": "Packet $4.00", "label_es": "Paquete $4.00"},
                ],
            },
            {
                "name_en": "Carnival",
                "name_es": "Carnival",
                "price": "0.50",
                "promos": [
                    {"label_en": "Packet $7.00", "label_es": "Paquete $7.00"},
                ],
            },
        ],
    },
    {
        "slug": "cocteles",
        "name_en": "Cocktails",
        "name_es": "Cócteles",
        "items": [
            {
                "name_en": "Cuba Libre",
                "name_es": "Cuba Libre",
                "price": "4.00",
                "ingredients_en": "Rum, Coca-Cola, Lime juice, Ice",
                "ingredients_es": "Ron, Coca-Cola, Jugo de limón, Hielo",
            },
        ],
    },
    # The bar sells wine and liquor but the source document lists neither yet.
    # Seeded empty and hidden from the public page until something is added, so
    # the rest of the menu has somewhere to go without a developer.
    {"slug": "vinos", "name_en": "Wine", "name_es": "Vinos", "items": []},
    {"slug": "licores", "name_en": "Liquor", "name_es": "Licores", "items": []},
]


DEFAULT_BLOG_POSTS = [
    {
        "slug": "website-launch",
        "title_en": "The new Marea Alta website is live",
        "title_es": "Ya está en línea el nuevo sitio de Marea Alta",
        "excerpt_en": (
            "Surf, parties, the full menu and table requests — now in one place, "
            "in English and Spanish."
        ),
        "excerpt_es": (
            "Surf, fiestas, el menú completo y solicitudes de mesa: ahora todo en "
            "un solo lugar, en inglés y español."
        ),
        "body_en": (
            "After a good run, mareaaltabar.com has a new home. The site now shows "
            "the live surf and tide report for Montañita, the week's parties and "
            "opening hours, and the full drinks menu with current prices.\n\n"
            "You can switch between English and Spanish, install the site on your "
            "phone, and keep reading the menu and schedule when the signal drops. "
            "Table requests and messages come straight to the bar.\n\n"
            "We will use this page for new drinks, upcoming parties, surf days "
            "worth planning around, and news from Montañita. See you at the bar."
        ),
        "body_es": (
            "Después de una buena temporada, mareaaltabar.com tiene un nuevo "
            "hogar. El sitio ahora muestra el reporte de surf y marea en vivo de "
            "Montañita, las fiestas y horarios de la semana, y el menú completo "
            "de bebidas con precios actuales.\n\n"
            "Puedes cambiar entre inglés y español, instalar el sitio en tu "
            "teléfono y seguir leyendo el menú y la programación cuando se caiga "
            "la señal. Las solicitudes de mesa y los mensajes llegan directo al "
            "bar.\n\n"
            "Usaremos esta página para nuevas bebidas, próximas fiestas, días de "
            "surf que vale la pena planear y noticias de Montañita. Nos vemos en "
            "el bar."
        ),
        "image_url": "",
    },
]


def seed_blog(db: DBSession) -> None:
    """Insert the launch post if the news table is empty.

    Same contract as :func:`seed_menu`: it only inserts into a genuinely fresh
    database, so the placeholder can be edited or deleted from the panel without
    being recreated on the next restart. The publication date is today at the
    bar, which is also the clock the public read filters on.
    """
    if db.execute(select(BlogPost).limit(1)).scalar_one_or_none() is not None:
        return

    today = bar_today()[1]
    for post in DEFAULT_BLOG_POSTS:
        db.add(
            BlogPost(
                slug=post["slug"],
                title_en=post["title_en"],
                title_es=post["title_es"],
                excerpt_en=post.get("excerpt_en", ""),
                excerpt_es=post.get("excerpt_es", ""),
                body_en=post.get("body_en", ""),
                body_es=post.get("body_es", ""),
                image_url=post.get("image_url", ""),
                published_on=today,
                is_active=True,
            )
        )
    db.commit()


def seed_menu(db: DBSession) -> None:
    """Insert the starting drinks menu if the table is empty.

    Idempotent in the same way as :func:`seed_schedule`: it only inserts when
    there are no categories, so it can never overwrite what the admin has since
    typed into the panel. Adding a category to ``DEFAULT_MENU`` therefore seeds
    only a genuinely fresh database, which is the intent — once the bar is
    editing the menu, the admin panel is the source of truth.
    """
    if db.execute(select(MenuCategory).limit(1)).scalar_one_or_none() is not None:
        return

    for order, category in enumerate(DEFAULT_MENU):
        row = MenuCategory(
            slug=category["slug"],
            name_en=category["name_en"],
            name_es=category["name_es"],
            sort_order=order,
        )
        for item_order, item in enumerate(category["items"]):
            promos = item.get("promos", [])
            row.items.append(
                MenuItem(
                    name_en=item.get("name_en", ""),
                    name_es=item.get("name_es", ""),
                    description_en=item.get("description_en", ""),
                    description_es=item.get("description_es", ""),
                    ingredients_en=item.get("ingredients_en", ""),
                    ingredients_es=item.get("ingredients_es", ""),
                    price=item.get("price", ""),
                    sort_order=item_order,
                )
            )
            for promo_order, promo in enumerate(promos):
                row.items[-1].promos.append(
                    MenuItemPromo(
                        label_en=promo.get("label_en", ""),
                        label_es=promo.get("label_es", ""),
                        sort_order=promo_order,
                    )
                )
        db.add(row)

    db.commit()