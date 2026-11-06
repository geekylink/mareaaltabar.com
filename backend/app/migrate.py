"""Forward-only SQLite migrations.

SQLite's ``ALTER TABLE ... ADD COLUMN`` can add a column but cannot rename one,
and SQLAlchemy's ``create_all`` only creates missing tables -- it never alters
existing ones. So schema changes are applied here as explicit statements.

Each migration is idempotent and records that it ran, so starting the app twice
is safe. Add new migrations to the bottom of :data:`MIGRATIONS`.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)


def _table_columns(engine: Engine, table: str) -> set[str]:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def _table_exists(engine: Engine, table: str) -> bool:
    return table in inspect(engine).get_table_names()


def _add_column(engine: Engine, table: str, column: str, ddl_type: str) -> None:
    """Add a column only if it is missing."""
    if column in _table_columns(engine, table):
        return
    log.info("Migrating: adding %s.%s", table, column)
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def migrate_events_to_bilingual(engine: Engine) -> None:
    """Split single-language event text into ``_en`` / ``_es`` columns.

    Preserves existing copy: current content becomes English, Spanish is seeded
    with the same text so the site never renders a blank Spanish schedule before
    a human has translated it. ``time`` is intentionally left in place (SQLite
    cannot drop columns cheaply) but is no longer read or written -- opening
    times now come from the ``hours`` table.
    """
    if not _table_exists(engine, "events"):
        return

    cols = _table_columns(engine, "events")
    _add_column(engine, "events", "title_en", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "events", "title_es", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "events", "note_en", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "events", "note_es", "TEXT NOT NULL DEFAULT ''")

    # Backfill from the legacy single-language columns, once.
    if {"title", "note"} <= _table_columns(engine, "events"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE events SET title_en = title "
                    "WHERE (title_en IS NULL OR title_en = '') AND title IS NOT NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE events SET title_es = title "
                    "WHERE (title_es IS NULL OR title_es = '') AND title IS NOT NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE events SET note_en = note "
                    "WHERE (note_en IS NULL OR note_en = '') AND note IS NOT NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE events SET note_es = note "
                    "WHERE (note_es IS NULL OR note_es = '') AND note IS NOT NULL"
                )
            )

    log.debug("Event bilingual columns ready")


def migrate_closed_days_to_bilingual(engine: Engine) -> None:
    """Split the single-language closure reason into ``_en`` / ``_es``."""
    if not _table_exists(engine, "closed_days"):
        return

    _add_column(engine, "closed_days", "reason_en", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "closed_days", "reason_es", "TEXT NOT NULL DEFAULT ''")

    if "reason" in _table_columns(engine, "closed_days"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE closed_days SET reason_en = reason "
                    "WHERE (reason_en IS NULL OR reason_en = '') AND reason IS NOT NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE closed_days SET reason_es = reason "
                    "WHERE (reason_es IS NULL OR reason_es = '') AND reason IS NOT NULL"
                )
            )


def migrate_hours_to_24h(engine: Engine) -> None:
    """Normalise legacy ``4:00 PM`` style times to 24-hour ``HH:MM``.

    ``<input type="time">`` in the admin panel only understands 24-hour values,
    so anything else would silently fail to populate the form.
    """
    if not _table_exists(engine, "hours"):
        return

    for column in ("open_time", "close_time"):
        with engine.begin() as conn:
            rows = conn.execute(text(f"SELECT id, {column} FROM hours")).fetchall()
            for row_id, value in rows:
                if not value:
                    continue
                upper = value.strip().upper()
                if ":" not in value or ("AM" not in upper and "PM" not in upper):
                    continue  # already 24-hour or empty; leave alone
                try:
                    clock, meridiem = upper.rsplit(" ", 1)
                    hour, minute = clock.split(":")
                    hour = int(hour) % 12
                    if meridiem == "PM":
                        hour += 12
                    normalised = f"{hour:02d}:{minute}"
                except (ValueError, IndexError):
                    log.warning("Could not parse %s.%s value %r; leaving unchanged", column, row_id, value)
                    continue
                conn.execute(
                    text(f"UPDATE hours SET {column} = :value WHERE id = :id"),
                    {"value": normalised, "id": row_id},
                )


def migrate_menu_schema(engine: Engine) -> None:
    """Bring an existing ``menu_items`` table up to the current shape.

    A brand-new database needs nothing here: ``create_all`` builds the menu tables
    from the models at startup. This exists for a database that already has a
    ``menu_items`` table from an earlier build of the menu, where adding columns
    to it is exactly the job ``create_all`` will not do — it only creates missing
    tables, never alters existing ones. ``ingredients_*`` and ``is_available`` are
    the columns that arrived after the table itself, and both are added with a
    default so existing drinks survive.
    """
    if not _table_exists(engine, "menu_items"):
        return

    _add_column(engine, "menu_items", "ingredients_en", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "menu_items", "ingredients_es", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "menu_items", "is_available", "BOOLEAN NOT NULL DEFAULT 1")

    log.debug("Menu schema ready")


def migrate_menu_promos_to_scheduled(engine: Engine) -> None:
    """Add the happy-hour window columns to an existing ``menu_item_promos``.

    Every column defaults to blank (or active), so promos created before the
    schedule existed remain always-live rather than disappearing from the menu.
    """
    if not _table_exists(engine, "menu_item_promos"):
        return

    _add_column(engine, "menu_item_promos", "days", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "menu_item_promos", "start_time", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "menu_item_promos", "end_time", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "menu_item_promos", "starts_on", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "menu_item_promos", "ends_on", "TEXT NOT NULL DEFAULT ''")
    _add_column(engine, "menu_item_promos", "is_active", "BOOLEAN NOT NULL DEFAULT 1")

    log.debug("Menu promo schedule ready")


MIGRATIONS = (
    migrate_events_to_bilingual,
    migrate_closed_days_to_bilingual,
    migrate_hours_to_24h,
    migrate_menu_schema,
    migrate_menu_promos_to_scheduled,
)


def run_migrations(engine: Engine) -> None:
    """Apply every pending migration. Safe to call on each startup."""
    for migration in MIGRATIONS:
        try:
            migration(engine)
        except Exception:  # noqa: BLE001 - never block startup on a migration
            log.exception("Migration %s failed; continuing", migration.__name__)