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


@pytest.fixture()
def early_menu_engine():
    """An engine whose `menu_items` table predates the ingredient and availability
    columns — what a database seeded by an earlier build of the menu looks like.

    `create_all` only creates missing tables, so it will never add these columns;
    that is what `migrate_menu_schema` is for.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE menu_categories ("
                " id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name_en TEXT, name_es TEXT,"
                " sort_order INTEGER, created_at DATETIME, updated_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE menu_items ("
                " id INTEGER PRIMARY KEY, category_id INTEGER NOT NULL, name_en TEXT, name_es TEXT,"
                " description_en TEXT, description_es TEXT, price TEXT, sort_order INTEGER,"
                " created_at DATETIME, updated_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO menu_categories (slug, name_en, name_es, sort_order)"
                " VALUES ('cocteles', 'Cocktails', 'Cócteles', 0)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO menu_items (category_id, name_en, name_es, price, sort_order)"
                " VALUES (1, 'Cuba Libre', 'Cuba Libre', '4.00', 0)"
            )
        )
    yield engine
    engine.dispose()


@pytest.fixture()
def legacy_promo_engine():
    """An engine whose promos predate the happy-hour window columns."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE menu_item_promos ("
                " id INTEGER PRIMARY KEY, menu_item_id INTEGER NOT NULL,"
                " label_en TEXT, label_es TEXT, sort_order INTEGER,"
                " created_at DATETIME, updated_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO menu_item_promos (menu_item_id, label_en, label_es, sort_order)"
                " VALUES (1, '6x $7.00', '6 por $7.00', 0)"
            )
        )
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


# --- The menu ---


def test_menu_migration_adds_the_later_columns(early_menu_engine):
    run_migrations(early_menu_engine)
    assert {"ingredients_en", "ingredients_es", "is_available"} <= _columns(
        early_menu_engine, "menu_items"
    )


def test_menu_migration_keeps_existing_drinks(early_menu_engine):
    """The added columns must default, or every seeded cocktail breaks at once."""
    run_migrations(early_menu_engine)
    with early_menu_engine.connect() as conn:
        row = conn.execute(
            text("SELECT name_en, price, ingredients_en, ingredients_es, is_available FROM menu_items")
        ).fetchone()
    assert row[0] == "Cuba Libre"
    assert row[1] == "4.00"
    assert row[2] == ""
    assert row[3] == ""
    assert row[4] == 1


def test_menu_migration_is_idempotent(early_menu_engine):
    run_migrations(early_menu_engine)
    run_migrations(early_menu_engine)
    with early_menu_engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM menu_items")).fetchone()[0] == 1


def test_menu_migration_is_a_no_op_without_a_menu(legacy_engine):
    """A database from before the menu exists must not gain an empty table here."""
    run_migrations(legacy_engine)
    assert "menu_items" not in inspect(legacy_engine).get_table_names()


# --- Happy-hour promos ---


def test_promo_migration_adds_the_window_columns(legacy_promo_engine):
    run_migrations(legacy_promo_engine)
    assert {
        "days", "start_time", "end_time", "starts_on", "ends_on", "is_active"
    } <= _columns(legacy_promo_engine, "menu_item_promos")


def test_promo_migration_leaves_existing_offers_always_live(legacy_promo_engine):
    """Blank windows mean always-on, so an upgrade must not hide the menu's offers."""
    run_migrations(legacy_promo_engine)
    with legacy_promo_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT label_en, days, start_time, end_time, starts_on, ends_on, is_active"
                " FROM menu_item_promos"
            )
        ).fetchone()
    assert row[0] == "6x $7.00"
    assert row[1:6] == ("", "", "", "", "")
    assert row[6] == 1


def test_promo_migration_is_idempotent(legacy_promo_engine):
    run_migrations(legacy_promo_engine)
    run_migrations(legacy_promo_engine)
    with legacy_promo_engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM menu_item_promos")).fetchone()[0] == 1


def test_promo_migration_is_a_no_op_without_promos(legacy_engine):
    run_migrations(legacy_engine)
    assert "menu_item_promos" not in inspect(legacy_engine).get_table_names()