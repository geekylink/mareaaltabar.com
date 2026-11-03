"""Password hashing, session token generation, and session CRUD."""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import Admin, Session

# The account page asks for at least this much. bcrypt also refuses inputs longer
# than 72 bytes, so the upper bound is enforced here rather than turning into a
# 500 when someone pastes a passphrase.
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def password_problem(password: str) -> str | None:
    """The first rule ``password`` breaks, or ``None`` when it is acceptable.

    Returning a code rather than a sentence lets the account page translate the
    message, and keeps the rule in one place instead of repeated in the router.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return "too_short"
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "too_long"
    if not any(character.isalpha() for character in password):
        return "needs_letter"
    if not any(character.isdigit() for character in password):
        return "needs_digit"
    return None


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


def delete_other_sessions(db: DBSession, admin_id: int, keep_token: str) -> int:
    """Sign an admin out everywhere except the session making the change.

    Called after a password change. The current session is kept so the admin is
    not thrown out of the page they just used, but every other browser — or a
    stolen cookie — stops working. The delete shares the caller's transaction,
    so the new password hash and the revocation commit together.
    """
    result = db.execute(
        delete(Session).where(
            Session.admin_id == admin_id,
            Session.token != keep_token,
        )
    )
    db.commit()
    return result.rowcount or 0


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
