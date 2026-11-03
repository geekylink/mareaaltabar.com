"""SQLite database engine, session factory, and connection helpers."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# SQLite has one writer at a time. WAL lets readers continue while a writer is
# committing, and the busy timeout makes a second writer wait for the lock
# instead of raising "database is locked" on a busy Friday night. The app still
# runs one worker: WAL improves the failure mode, it does not make SQLite a
# multi-writer database.
SQLITE_BUSY_TIMEOUT_MS = 30_000
SQLITE_CONNECT_TIMEOUT_SECONDS = 30


def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    """Apply the pragmas every connection needs, on connect rather than once.

    ``busy_timeout`` and ``foreign_keys`` are per-connection settings, and WAL
    is persisted in the database file but harmless to repeat. Running them here
    means a connection from any thread gets the same guarantees.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_db_engine(database_path: str) -> Engine:
    """Build a SQLite engine configured for the app's concurrency model.

    ``database_path`` is normally a filesystem path from ``DATABASE_PATH``. A
    caller that already holds a ``sqlite:`` URL can pass it through unchanged,
    which keeps tests and one-off scripts able to use in-memory databases.
    """
    url = (
        database_path
        if database_path.startswith("sqlite:")
        else f"sqlite:///{database_path}"
    )
    engine = create_engine(
        url,
        connect_args={
            "check_same_thread": False,
            "timeout": SQLITE_CONNECT_TIMEOUT_SECONDS,
        },
    )
    event.listen(engine, "connect", _configure_sqlite)
    return engine


engine = create_db_engine(settings.DATABASE_PATH)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
