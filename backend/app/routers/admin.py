"""Admin panel HTML page routes.

These pages are intentionally unlinked from the public site; they are reachable
only by typing the URL directly. Everything except the login page requires an
admin session.
"""

import re
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app import auth
from app.admin_i18n import SUPPORTED, strings_for
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_admin, get_current_session
from app.models import Admin, Submission

router = APIRouter()

# Usernames appear inside a JSON attribute in the admin header, and are shown in
# the logs. Keep them to letters (Unicode included), digits, spaces, dot, hyphen
# and underscore: no quotes, angle brackets or backslashes to escape.
USERNAME_RE = re.compile(r"^[\w .-]{3,128}$")

# Query-string error codes are mapped to translation keys here, so a crafted
# `?error=...` can never put arbitrary text on the page.
ACCOUNT_ERRORS = {
    "invalid_current": "account_error_invalid_current",
    "password_mismatch": "account_error_password_mismatch",
    "password_weak": "account_error_password_weak",
    "password_same": "account_error_password_same",
    "username_required": "account_error_username_required",
    "username_taken": "account_error_username_taken",
    "username_invalid": "account_error_username_invalid",
}

templates = Jinja2Templates(directory="app/templates")

# Bilingual helper script. Mounted under /admin/static rather than served from
# the templates directory, so template source is never exposed over HTTP.
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
router.mount("/admin/static", StaticFiles(directory=str(_STATIC_DIR)), name="admin-static")


def _i18n_payload() -> dict:
    """All languages, so the client can switch without a page reload."""
    return {
        "__ADMIN_STRINGS__": {lang: strings_for(lang) for lang in SUPPORTED},
        "__ADMIN_SUPPORTED__": list(SUPPORTED),
    }


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error or "", **_i18n_payload()},
    )


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    """The dashboard, with the shared inbox's unread count on its card.

    Server-rendered rather than fetched: the count is one cheap query, and a
    badge that appears a moment after the page does is easy to miss. The inbox
    page itself refreshes the list, so the number cannot go stale while someone
    is reading messages.
    """
    unread = db.scalar(
        select(func.count(Submission.id)).where(Submission.is_read.is_(False))
    ) or 0
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "admin": admin,
            "unread_submissions": unread,
            **_i18n_payload(),
        },
    )


@router.get("/admin/schedule", response_class=HTMLResponse)
async def admin_schedule(request: Request, admin=Depends(get_current_admin)):
    return templates.TemplateResponse(
        request=request,
        name="admin/schedule.html",
        context={"admin": admin, **_i18n_payload()},
    )


@router.get("/admin/menu", response_class=HTMLResponse)
async def admin_menu(request: Request, admin=Depends(get_current_admin)):
    """The drinks menu: add, edit, reorder and remove categories and items."""
    return templates.TemplateResponse(
        request=request,
        name="admin/menu.html",
        context={"admin": admin, **_i18n_payload()},
    )


@router.get("/admin/notices", response_class=HTMLResponse)
async def admin_notices(request: Request, admin=Depends(get_current_admin)):
    """Emergency banner control: add, pause, resume and delete notices.

    The rows come from ``/api/notices/all`` so the list includes paused and
    scheduled notices, which the public read hides.
    """
    return templates.TemplateResponse(
        request=request,
        name="admin/notices.html",
        context={"admin": admin, **_i18n_payload()},
    )


@router.get("/admin/events", response_class=HTMLResponse)
async def admin_events(request: Request, admin=Depends(get_current_admin)):
    """Dated-event control: add one-off parties alongside the weekly schedule.

    The rows come from ``/api/special-events/all`` so past and switched-off
    events stay editable, which the public read hides.
    """
    return templates.TemplateResponse(
        request=request,
        name="admin/events.html",
        context={"admin": admin, **_i18n_payload()},
    )


@router.get("/admin/inbox", response_class=HTMLResponse)
async def admin_inbox(request: Request, admin=Depends(get_current_admin)):
    """The shared contact-form inbox, visible to every signed-in admin.

    The rows come from ``/api/submissions``, which is session-guarded and shared
    rather than per-admin. Marking read and deleting go through the same API, so
    the page has no write path of its own.
    """
    return templates.TemplateResponse(
        request=request,
        name="admin/inbox.html",
        context={"admin": admin, **_i18n_payload()},
    )


@router.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs(request: Request, admin=Depends(get_current_admin)):
    """Read-only: login attempts, and every menu and schedule change.

    The rows come from the JSON endpoints in ``routers.logs``, which are GET-only
    and session-guarded. Nothing on this page can be edited or deleted, because
    there is no route that would accept it.
    """
    return templates.TemplateResponse(
        request=request,
        name="admin/logs.html",
        context={
            "admin": admin,
            # Shown on the page so the retention window is not a secret: it is
            # the same setting the daily purge and the CLI use.
            "log_retention_days": settings.LOG_RETENTION_DAYS,
            **_i18n_payload(),
        },
    )


# --- Account and second admin (ticket #54) ---------------------------------
#
# Two paths to lockout are closed here: the owner can change their own password
# without SSH access, and they can create a second admin without the CLI. Both
# forms are same-origin POSTs guarded by the session and by the CSRF token that
# is already in the session row, not only in the readable cookie.


def _check_form_csrf(token: str, session: DBSession) -> None:
    """Reject a form whose hidden token does not match the session."""
    if not token or not secrets.compare_digest(token, session.csrf_token):
        raise HTTPException(status_code=403, detail="CSRF token mismatch")


@router.get("/admin/account", response_class=HTMLResponse)
async def admin_account(
    request: Request,
    error: str | None = None,
    changed: str | None = None,
    created: str | None = None,
    session: DBSession = Depends(get_current_session),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/account.html",
        context={
            "admin": session.admin,
            "csrf_token": session.csrf_token,
            "error": ACCOUNT_ERRORS.get(error or ""),
            "changed": changed == "1",
            "created": created == "1",
            **_i18n_payload(),
        },
    )


@router.post("/admin/account/password")
async def admin_change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(""),
    session: DBSession = Depends(get_current_session),
    db: DBSession = Depends(get_db),
):
    """Change the signed-in admin's password and sign out their other sessions.

    The current password is required even though the session is already valid: a
    stolen cookie should not be enough to take the account over permanently.
    """
    _check_form_csrf(csrf_token, session)

    if not auth.verify_password(current_password, session.admin.password_hash):
        return RedirectResponse("/admin/account?error=invalid_current", status_code=303)

    if new_password != confirm_password:
        return RedirectResponse("/admin/account?error=password_mismatch", status_code=303)

    if auth.verify_password(new_password, session.admin.password_hash):
        return RedirectResponse("/admin/account?error=password_same", status_code=303)

    if auth.password_problem(new_password) is not None:
        return RedirectResponse("/admin/account?error=password_weak", status_code=303)

    session.admin.password_hash = auth.hash_password(new_password)
    # This commits the new hash and the revocation in one transaction; the
    # session that made the change is deliberately kept.
    auth.delete_other_sessions(db, session.admin_id, session.token)
    return RedirectResponse("/admin/account?changed=1", status_code=303)


@router.post("/admin/account/admins")
async def admin_create_account(
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(""),
    session: DBSession = Depends(get_current_session),
    db: DBSession = Depends(get_db),
):
    """Create another admin. The creator stays signed in as themselves."""
    _check_form_csrf(csrf_token, session)

    username = username.strip()
    if not username:
        return RedirectResponse("/admin/account?error=username_required", status_code=303)
    if not USERNAME_RE.match(username):
        return RedirectResponse("/admin/account?error=username_invalid", status_code=303)

    if password != confirm_password:
        return RedirectResponse("/admin/account?error=password_mismatch", status_code=303)
    if auth.password_problem(password) is not None:
        return RedirectResponse("/admin/account?error=password_weak", status_code=303)

    existing = db.execute(
        select(Admin).where(Admin.username == username)
    ).scalar_one_or_none()
    if existing is not None:
        return RedirectResponse("/admin/account?error=username_taken", status_code=303)

    db.add(Admin(username=username, password_hash=auth.hash_password(password)))
    try:
        db.commit()
    except IntegrityError:
        # The check above loses a race with a simultaneous create; the unique
        # constraint is the real guard.
        db.rollback()
        return RedirectResponse("/admin/account?error=username_taken", status_code=303)

    return RedirectResponse("/admin/account?created=1", status_code=303)
