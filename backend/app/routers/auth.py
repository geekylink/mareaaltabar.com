"""Login and logout endpoints."""

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as DBSession

from app import audit, auth
from app.config import settings
from app.database import get_db

router = APIRouter()

# In-memory rate limiting: IP -> timestamps of recent FAILED login attempts.
# Only failures count, so legitimate admins are never locked out by normal use.
_failed_attempts: dict[str, list[float]] = defaultdict(list)


def reset_rate_limit() -> None:
    """Clear all recorded failed attempts. Used by the test suite."""
    _failed_attempts.clear()


def _is_rate_limited(ip: str) -> bool:
    """True if this IP has too many recent failed attempts."""
    cutoff = time.monotonic() - settings.RATE_LIMIT_WINDOW_MINUTES * 60
    attempts = _failed_attempts[ip]
    attempts[:] = [t for t in attempts if t > cutoff]
    return len(attempts) >= settings.RATE_LIMIT_ATTEMPTS


def _record_failure(ip: str) -> None:
    """Record one failed login attempt."""
    _failed_attempts[ip].append(time.monotonic())


@router.post("/admin/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: DBSession = Depends(get_db),
):
    # Every outcome is logged, the refusals included: an attempt the rate limiter
    # turned away is exactly the one an owner wants to see afterwards. `password`
    # is deliberately not passed to the logger — see `audit.log_login_attempt`.
    ip = audit.request_ip(request)
    user_agent = request.headers.get("user-agent", "")

    def record(outcome: str) -> None:
        audit.log_login_attempt(
            db, username=username, ip=ip, user_agent=user_agent, outcome=outcome
        )

    if _is_rate_limited(ip):
        record(audit.OUTCOME_RATE_LIMITED)
        return RedirectResponse(url="/admin/login?error=rate_limited", status_code=303)

    admin = auth.authenticate_admin(db, username, password)
    if admin is None:
        _record_failure(ip)
        record(audit.OUTCOME_INVALID)
        return RedirectResponse(url="/admin/login?error=1", status_code=303)

    # Success clears any prior failures for this IP
    _failed_attempts.pop(ip, None)

    session = auth.create_session(db, admin.id)

    record(audit.OUTCOME_SUCCESS)

    response = RedirectResponse(url="/admin", status_code=303)
    max_age = settings.SESSION_TTL_HOURS * 3600

    response.set_cookie(
        key="session_token",
        value=session.token,
        max_age=max_age,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="csrf_token",
        value=session.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.post("/admin/logout")
async def logout(
    request: Request,
    db: DBSession = Depends(get_db),
):
    token = request.cookies.get("session_token")
    if token:
        auth.delete_session(db, token)

    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("session_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return response