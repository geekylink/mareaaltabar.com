"""Admin panel HTML page routes.

These pages are intentionally unlinked from the public site; they are reachable
only by typing the URL directly.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.admin_i18n import SUPPORTED, strings_for
from app.config import settings
from app.dependencies import get_current_admin

router = APIRouter()

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
async def admin_dashboard(request: Request, admin=Depends(get_current_admin)):
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={"admin": admin, **_i18n_payload()},
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