"""Admin panel HTML page routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.dependencies import get_current_admin

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: DBSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={"admin": admin},
    )


@router.get("/admin/schedule", response_class=HTMLResponse)
async def admin_schedule(
    request: Request,
    db: DBSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/schedule.html",
        context={"admin": admin},
    )


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(
    request: Request,
    error: bool = False,
):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error},
    )
