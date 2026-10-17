"""FastAPI dependencies: authentication, CSRF protection, rate limiting."""

import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DBSession

from app import audit, auth
from app.database import get_db
from app.models import Admin, Session

# --- Rate limiting (in-memory sliding window) ---

_login_attempts: dict[str, list[float]] = defaultdict(list)


def rate_limit_login(request: Request) -> None:
    """Block login attempts if too many from the same IP in the window."""
    now = time.monotonic()
    window_seconds = 60 * 10  # 10 minutes (from settings in real impl)
    max_attempts = 5

    ip = request.client.host if request.client else "unknown"
    attempts = _login_attempts[ip]
    cutoff = now - window_seconds
    attempts[:] = [t for t in attempts if t > cutoff]

    if len(attempts) >= max_attempts:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later.",
        )
    attempts.append(now)


# --- Authentication ---

def get_current_admin(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
) -> Admin:
    """Validate the session cookie and return the logged-in admin."""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = auth.get_session(db, token)
    if session is None:
        response.delete_cookie("session_token")
        response.delete_cookie("csrf_token")
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return session.admin


def get_current_session(
    request: Request,
    db: DBSession = Depends(get_db),
) -> Session:
    """Return the current session object (after auth check)."""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = auth.get_session(db, token)
    if session is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return session


def change_author(
    request: Request,
    admin: Admin = Depends(get_current_admin),
) -> audit.ChangeAuthor:
    """The identity and origin of whoever is making a change.

    Every write handler takes this instead of the bare admin, because a log entry
    that cannot answer "from where" is only half an audit trail — a shared or
    stolen session still names a username, but not the machine it came from. It
    authenticates exactly as :func:`get_current_admin` does, so adding it to a
    route cannot weaken the guard already in ``write_guard``.
    """
    return audit.ChangeAuthor(
        username=admin.username,
        ip=audit.request_ip(request),
        user_agent=audit.clean_user_agent(request.headers.get("user-agent")),
    )


# --- CSRF protection ---

def csrf_protect(request: Request, session: Session = Depends(get_current_session)) -> None:
    """Verify that the X-CSRF-Token header matches the session's CSRF token."""
    header_token = request.headers.get("X-CSRF-Token")
    cookie_token = request.cookies.get("csrf_token")

    if not header_token or not cookie_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")

    if header_token != cookie_token:
        raise HTTPException(status_code=403, detail="CSRF token mismatch")
