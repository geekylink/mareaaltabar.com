"""Bilingual UI strings for the admin panel.

Served to the browser as JSON and applied client-side. Keeping one dictionary
means a new language is a single new entry here plus one line in ``SUPPORTED``,
rather than edits scattered across three templates.

Placeholders use ``{name}`` and are substituted by ``format``-style replacement
in ``admin_i18n.js``.
"""

SUPPORTED = ("en", "es")
DEFAULT_LANG = "en"

# Keyed by language, then by string id.
STRINGS = {
    "en": {
        "app_title": "Marea Alta Admin",
        "nav_schedule": "Party Schedule",
        "lang_label": "Language",
        "logged_in_as": "Signed in as {username}",
        "logout": "Log out",
        "sign_in": "Sign in",
        "username": "Username",
        "password": "Password",
        "invalid_login": "Invalid username or password.",
        "rate_limited": "Too many attempts. Please wait a few minutes and try again.",
        "dashboard_title": "Dashboard",
        "dashboard_intro": "Choose a section to manage.",
        "card_schedule_title": "Party Schedule",
        "card_schedule_body": "Edit each day's party in English and Spanish, set opening hours, and add closed days.",
        "schedule_heading": "Weekly schedule",
        "schedule_intro": "Fill in both languages. Leave a translation blank to fall back to English on the site.",
        "col_day": "Day",
        "col_open": "Opens",
        "col_close": "Closes",
        "col_closed": "Closed",
        "col_titles": "Party title (EN / ES)",
        "col_notes": "Description (EN / ES)",
        "save_day": "Save",
        "save_all": "Save all days",
        "saving": "Saving...",
        "saved": "Saved",
        "save_failed": "Could not save. Reload the page and try again.",
        "closed_days_heading": "Closed days",
        "closed_days_intro": "Dates the bar is closed for a one-off, such as a holiday or a private booking.",
        "closed_date": "Date",
        "closed_reason_en": "Reason (English)",
        "closed_reason_es": "Reason (Spanish)",
        "add_closed": "Add closed day",
        "remove": "Remove",
        "no_closed_days": "No closed days yet.",
        "edit_reason": "Edit reason",
        "back": "Back to dashboard",
        "loading": "Loading...",
        "required_field": "Required",
        "fix_errors": "Please fix the highlighted fields.",
    },
    "es": {
        "app_title": "Administración Marea Alta",
        "nav_schedule": "Programación de Fiestas",
        "lang_label": "Idioma",
        "logged_in_as": "Sesión iniciada como {username}",
        "logout": "Cerrar sesión",
        "sign_in": "Iniciar sesión",
        "username": "Usuario",
        "password": "Contraseña",
        "invalid_login": "Usuario o contraseña incorrectos.",
        "rate_limited": "Demasiados intentos. Espera unos minutos e inténtalo de nuevo.",
        "dashboard_title": "Panel",
        "dashboard_intro": "Elige una sección para administrar.",
        "card_schedule_title": "Programación de Fiestas",
        "card_schedule_body": "Edita la fiesta de cada día en inglés y español, define los horarios y agrega días cerrados.",
        "schedule_heading": "Programación semanal",
        "schedule_intro": "Completa ambos idiomas. Deja una traducción en blanco para que el sitio use el inglés.",
        "col_day": "Día",
        "col_open": "Abre",
        "col_close": "Cierra",
        "col_closed": "Cerrado",
        "col_titles": "Título de la fiesta (EN / ES)",
        "col_notes": "Descripción (EN / ES)",
        "save_day": "Guardar",
        "save_all": "Guardar todos los días",
        "saving": "Guardando...",
        "saved": "Guardado",
        "save_failed": "No se pudo guardar. Recarga la página e inténtalo de nuevo.",
        "closed_days_heading": "Días cerrados",
        "closed_days_intro": "Fechas en las que el bar está cerrado por una ocasión, como un feriado o un evento privado.",
        "closed_date": "Fecha",
        "closed_reason_en": "Motivo (inglés)",
        "closed_reason_es": "Motivo (español)",
        "add_closed": "Agregar día cerrado",
        "remove": "Quitar",
        "no_closed_days": "Todavía no hay días cerrados.",
        "edit_reason": "Editar motivo",
        "back": "Volver al panel",
        "loading": "Cargando...",
        "required_field": "Obligatorio",
        "fix_errors": "Corrige los campos marcados.",
    },
}


def strings_for(lang: str) -> dict[str, str]:
    """Return the string table for ``lang``, always including English fallbacks."""
    table = dict(STRINGS[DEFAULT_LANG])
    if lang in STRINGS:
        table.update(STRINGS[lang])
    return table