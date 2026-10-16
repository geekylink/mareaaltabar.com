"""Bilingual labels for the server-rendered schedule and menu blocks.

The public site is a Svelte SPA whose wording lives in
``frontend/src/content/{en,es}.js``. Ticket #46 renders the schedule into the
HTML at request time for crawlers, and #1 does the same for the menu, which means
the server needs a handful of the same labels in Python.

This is a deliberate, bounded duplication: only the strings the rendered block
itself needs are here — day names and three or four labels — not the whole site
copy. ``tests/test_public_i18n.py`` parses this file and asserts every label also
exists in the frontend content modules, so a rename on one side fails CI instead
of silently drifting.

To add a language: add the code to ``SUPPORTED`` and a new table below.
"""

SUPPORTED = ("en", "es")
DEFAULT_LANG = "en"

# Keyed by language, then by string id. Mirrors the shape of `app/admin_i18n.py`.
STRINGS = {
    "en": {
        "schedule_heading": "Party schedule",
        "tonight": "Tonight",
        "closed_today": "Closed today",
        "no_event": "No event scheduled",
        "opening_hours": "Opening hours",
        "closed_days": "Closed days",
        "menu_heading": "Drinks menu",
        "menu_ingredients": "Ingredients",
        "menu_promo": "Promo",
        "menu_empty": "The menu is being updated. Ask us for today's prices.",
        "days": [
            "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
        ],
    },
    "es": {
        "schedule_heading": "Programación de fiestas",
        "tonight": "Esta noche",
        "closed_today": "Cerrado hoy",
        "no_event": "Sin evento programado",
        "opening_hours": "Horario",
        "closed_days": "Días cerrados",
        "menu_heading": "Menú de bebidas",
        "menu_ingredients": "Ingredientes",
        "menu_promo": "Promo",
        "menu_empty": "Estamos actualizando el menú. Pregúntanos los precios de hoy.",
        "days": [
            "Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"
        ],
    },
}


def strings_for(lang: str) -> dict:
    """Return the label table for ``lang``, always including English fallbacks."""
    table = dict(STRINGS[DEFAULT_LANG])
    if lang in STRINGS:
        table.update(STRINGS[lang])
    return table


def resolve_lang(requested: str | None) -> str:
    """Validate a requested language, falling back to the default.

    The served HTML is one language, so an unknown or missing ``?lang=`` gets
    the default rather than an error.
    """
    if requested in SUPPORTED:
        return requested
    return DEFAULT_LANG