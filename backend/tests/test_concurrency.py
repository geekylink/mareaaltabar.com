"""SQLite must survive more than one writer, which is the production risk.

The engine is configured with WAL, a busy timeout and foreign keys so a second
writer waits for the lock instead of failing outright. These tests exercise the
configuration itself and then perform real concurrent writes through separate
sessions, because a pragma assertion alone would not catch a broken session
factory.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.database import SQLITE_BUSY_TIMEOUT_MS, create_db_engine
from app.models import Base, Event


def _file_engine(tmp_path):
    engine = create_db_engine(str(tmp_path / "concurrency.db"))
    Base.metadata.create_all(bind=engine)
    return engine


def test_create_db_engine_makes_the_missing_data_directory(tmp_path):
    """A fresh checkout has no backend/data; the first connect must create it."""
    database = tmp_path / "missing" / "nested" / "marea.db"
    assert not database.parent.exists()

    engine = create_db_engine(str(database))
    try:
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT 1").scalar() == 1
    finally:
        engine.dispose()

    assert database.parent.is_dir()


def test_sqlite_pragmas_are_applied_on_every_connection(tmp_path):
    engine = _file_engine(tmp_path)
    try:
        with engine.connect() as conn:
            assert conn.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
            assert conn.exec_driver_sql("PRAGMA busy_timeout").scalar() == SQLITE_BUSY_TIMEOUT_MS
            assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    finally:
        engine.dispose()


def test_concurrent_writes_from_separate_sessions(tmp_path):
    """Four writers commit at once; every row must land without a lock error."""
    engine = _file_engine(tmp_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    barrier = threading.Barrier(4)

    def write_batch(worker: int) -> None:
        barrier.wait(timeout=5)
        session = SessionLocal()
        try:
            for row in range(10):
                session.add(
                    Event(
                        day=worker * 100 + row,
                        title_en=f"Worker {worker} row {row}",
                        title_es="",
                    )
                )
                session.commit()
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(write_batch, range(4)))

        with SessionLocal() as session:
            count = len(session.execute(select(Event)).scalars().all())
        assert count == 40
    finally:
        engine.dispose()
