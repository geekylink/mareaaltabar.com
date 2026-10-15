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