"""Password hashing, session token generation, and session CRUD."""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import Admin, Session


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def generate_session_token() -> str:
    return secrets.token_hex(32)


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def create_session(db: DBSession, admin_id: int) -> Session:
    """Create a new server-side session and return it."""
    csrf = generate_csrf_token()
    token = generate_session_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)

    session = Session(
        token=token,
        admin_id=admin_id,
        csrf_token=csrf,
        expires_at=expires,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, token: str) -> Session | None:
    """Look up a session by token; return None if not found or expired."""
    result = db.execute(select(Session).where(Session.token == token))
    session = result.scalar_one_or_none()
    if session is None:
        return None
    # SQLite stores datetimes as naive UTC strings; normalize for comparison
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return session


def delete_session(db: DBSession, token: str) -> None:
    db.execute(delete(Session).where(Session.token == token))
    db.commit()


def cleanup_expired_sessions(db: DBSession) -> int:
    """Delete all expired sessions. Returns count deleted."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = db.execute(
        delete(Session).where(Session.expires_at < now)
    )
    db.commit()
    return result.rowcount or 0


def authenticate_admin(db: DBSession, username: str, password: str) -> Admin | None:
    """Verify credentials; return Admin on success, None on failure."""
    result = db.execute(select(Admin).where(Admin.username == username))
    admin = result.scalar_one_or_none()
    if admin is None:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin
