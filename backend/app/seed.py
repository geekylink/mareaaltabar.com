"""Default schedule data used to seed a fresh database.

Shared by the app (on startup) and the test suite so both see the same rows.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import Event, Hours

DEFAULT_EVENTS = [
    {"day": 0, "time": "8 PM - 2 AM", "title": "Latin Night", "note": "Salsa, bachata and reggaeton all night."},
    {"day": 1, "time": "8 PM - 4 AM", "title": "Singles Night", "note": "Mingle with the singles."},
    {"day": 2, "time": "", "title": "Closed", "note": ""},
    {"day": 3, "time": "", "title": "Closed", "note": ""},
    {"day": 4, "time": "8 PM - 4 AM", "title": "Open Mic Night", "note": "Come play music with us, bring an instrument or sing or play one of ours."},
    {"day": 5, "time": "8 PM - 4 AM", "title": "Live Music", "note": "Live music all night."},
    {"day": 6, "time": "8 PM - 4 AM", "title": "Live Music", "note": "The big one. Arrive early for a spot."},
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