"""Default schedule data used to seed a fresh database.

Shared by the app (on startup) and the test suite so both see the same rows.
Times are stored 24-hour so the admin panel's ``<input type="time">`` can read
them; the frontend formats them for display.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import Event, Hours

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