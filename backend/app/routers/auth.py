"""Login and logout endpoints."""

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as DBSession

from app import auth
from app.config import settings
from app.database import get_db

router = APIRouter()

# In-memory rate limiting storage: IP -> list of timestamps
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    """Return True if the IP is allowed to attempt login, False if rate limited."""
    now = time.monotonic()
    window_seconds = settings.RATE_LIMIT_WINDOW_MINUTES * 60

    attempts = _login_attempts[ip]
    cutoff = now - window_seconds
    attempts[:] = [t for t in attempts if t > cutoff]

    if len(attempts) >= settings.RATE_LIMIT_ATTEMPTS:
        return False
    attempts.append(now)
    return True


@router.post("/admin/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: DBSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(ip):
        return RedirectResponse(
            url="/admin/login?error=rate_limited",
            status_code=303,
        )

    admin = auth.authenticate_admin(db, username, password)
    if admin is None:
        return RedirectResponse(
            url="/admin/login?error=1",
            status_code=303,
        )

    session = auth.create_session(db, admin.id)

    # Build redirect response
    response = RedirectResponse(url="/admin", status_code=303)

    # Set session cookie (HttpOnly)
    response.set_cookie(
        key="session_token",
        value=session.token,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    # Set CSRF cookie (NOT HttpOnly — JS must read it)
    response.set_cookie(
        key="csrf_token",
        value=session.csrf_token,
        max_age=settings.SESSION_TTL_HOURS * 3600,
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
