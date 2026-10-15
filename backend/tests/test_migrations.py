"""Tests for the SQLite schema migrations.

Guards against data loss when an existing single-language database is upgraded
to the bilingual schema.
"""

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.migrate import run_migrations


@pytest.fixture()
def legacy_engine():
    """An engine holding a pre-bilingual database, as an older release left it."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE events ("
                " id INTEGER PRIMARY KEY, day INTEGER NOT NULL UNIQUE, time TEXT,"
                " title TEXT, note TEXT, created_at DATETIME, updated_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE hours ("
                " id INTEGER PRIMARY KEY, day INTEGER NOT NULL UNIQUE, open_time TEXT,"
                " close_time TEXT, is_closed BOOLEAN, created_at DATETIME, updated_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE closed_days ("
                " id INTEGER PRIMARY KEY, date TEXT NOT NULL UNIQUE, reason TEXT,"
                " created_at DATETIME, updated_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO events (day, time, title, note) VALUES "
                "(0, '8 PM - 2 AM', 'Latin Night', 'Salsa all night'),"
                "(5, '8 PM - 4 AM', 'Live Music', 'Live music')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO hours (day, open_time, close_time, is_closed) VALUES "
                "(0, '4:00 PM', '2:00 AM', 0), (2, '', '', 1)"
            )
        )
        conn.execute(text("INSERT INTO closed_days (date, reason) VALUES ('2099-12-25', 'Christmas')"))
    yield engine
    engine.dispose()


def _columns(engine, table):
    return {c["name"] for c in inspect(engine).get_columns(table)}


def test_migration_adds_bilingual_columns(legacy_engine):
    run_migrations(legacy_engine)
    events_cols = _columns(legacy_engine, "events")
    assert {"title_en", "title_es", "note_en", "note_es"} <= events_cols
    assert {"reason_en", "reason_es"} <= _columns(legacy_engine, "closed_days")


def test_migration_preserves_existing_event_text(legacy_engine):
    run_migrations(legacy_engine)
    with legacy_engine.connect() as conn:
        row = conn.execute(
            text("SELECT title_en, title_es, note_en FROM events WHERE day = 0")
        ).fetchone()
    assert row[0] == "Latin Night"
    assert row[1] == "Latin Night"  # seeded with English so Spanish is never blank
    assert row[2] == "Salsa all night"


def test_migration_preserves_closed_day_reason(legacy_engine):
    run_migrations(legacy_engine)
    with legacy_engine.connect() as conn:
        row = conn.execute(
            text("SELECT reason_en, reason_es FROM closed_days WHERE date = '2099-12-25'")
        ).fetchone()
    assert row[0] == "Christmas"
    assert row[1] == "Christmas"


def test_migration_normalises_legacy_12h_times(legacy_engine):
    """<input type='time'> only understands 24-hour values."""
    run_migrations(legacy_engine)
    with legacy_engine.connect() as conn:
        row = conn.execute(
            text("SELECT open_time, close_time FROM hours WHERE day = 0")
        ).fetchone()
    assert row[0] == "16:00"
    assert row[1] == "02:00"


def test_migration_leaves_closed_day_flags_alone(legacy_engine):
    run_migrations(legacy_engine)
    with legacy_engine.connect() as conn:
        assert conn.execute(text("SELECT is_closed FROM hours WHERE day = 2")).fetchone()[0] == 1


def test_migration_is_idempotent(legacy_engine):
    """Running twice must not double-apply or error."""
    run_migrations(legacy_engine)
    run_migrations(legacy_engine)
    with legacy_engine.connect() as conn:
        row = conn.execute(text("SELECT title_en FROM events WHERE day = 0")).fetchone()
    assert row[0] == "Latin Night"


def test_migration_tolerates_missing_tables(legacy_engine):
    """A brand-new database has no legacy tables; migration must be a no-op."""
    with legacy_engine.begin() as conn:
        conn.execute(text("DROP TABLE events"))
        conn.execute(text("DROP TABLE closed_days"))
    run_migrations(legacy_engine)  # must not raise
    assert "hours" in inspect(legacy_engine).get_table_names()