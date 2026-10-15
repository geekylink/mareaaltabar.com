"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DBSession

from app import auth
from app.config import BACKEND_DIR, settings
from app.database import SessionLocal, engine, get_db
from app.migrate import run_migrations
from app.models import Base
from app.public_i18n import DEFAULT_LANG, resolve_lang
from app.routers import admin, api, auth as auth_router
from app.seed import seed_schedule
from app.ssr import FRONTEND_DIST, INDEX_HTML, render_index

logger = logging.getLogger(__name__)

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Bring an existing database up to the current schema before touching data
run_migrations(engine)

# Seed the default weekly schedule if the database is empty
_db = SessionLocal()
try:
    seed_schedule(_db)
finally:
    _db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: cleanup expired sessions
    db = SessionLocal()
    try:
        auth.cleanup_expired_sessions(db)
    finally:
        db.close()
    yield


# Hide docs in production
app_configs = {"title": "Marea Alta Admin", "lifespan": lifespan}
if settings.is_production:
    app_configs["openapi_url"] = None

app = FastAPI(**app_configs)

# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Include routers
app.include_router(auth_router.router)
app.include_router(admin.router)
app.include_router(api.router)

# Serve the built frontend from the same origin, so the site and the API that
# feeds it share a domain (no CORS, cookies work). Registered last so it only
# handles anything the API and admin routes did not claim.
#
# The site's index, rendered server-side so crawlers get the hours and party
# titles in the HTML instead of an empty shell they cannot execute JS against.
# Registered above the static mount below, which would otherwise serve the
# unmodified index.html.
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route(
    "/index.html", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False
)
async def index(lang: str | None = None, db: DBSession = Depends(get_db)):
    """Public: the SPA shell with the current schedule already in it.

    ``?lang=`` picks the language the HTML is rendered in. The visitor's own
    choice still wins in the browser once the app takes over.
    """
    lang = resolve_lang(lang)

    if not INDEX_HTML.is_file():
        # Dev convenience when the frontend has not been built yet.
        return JSONResponse(
            {"detail": "Frontend not built. Run `npm run build` in ../frontend."}
        )

    try:
        html = render_index(db, lang)
    except Exception:  # noqa: BLE001
        # A rendering failure must not take the homepage down. Serve the
        # un-injected shell — the SPA fills it in on mount — and leave a trace
        # for whatever error reporting the deploy has.
        logger.exception("Server-rendered schedule failed; serving the plain shell")
        html = INDEX_HTML.read_text(encoding="utf-8")

    if lang != DEFAULT_LANG:
        html = html.replace('<html lang="en">', f'<html lang="{lang}">', 1)

    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
