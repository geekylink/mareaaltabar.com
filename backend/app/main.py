"""FastAPI application entry point."""

import asyncio
import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DBSession

from app import audit, auth
from app.config import BACKEND_DIR, settings
from app.database import SessionLocal, engine, get_db
from app.migrate import run_migrations
from app.models import Base
from app.public_i18n import DEFAULT_LANG, resolve_lang
from app.routers import (
    admin,
    api,
    auth as auth_router,
    blog,
    contact,
    content,
    logs,
    newsletter,
    reservations,
    rsvps,
    uploads,
)
from app.seed import seed_blog, seed_menu, seed_schedule
from app.ssr import (
    FRONTEND_DIST,
    INDEX_HTML,
    MENU_HTML,
    NEWS_HTML,
    render_index,
    render_menu,
    render_news,
    render_news_not_found,
    render_news_post,
    render_sitemap,
)

logger = logging.getLogger(__name__)

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Bring an existing database up to the current schema before touching data
run_migrations(engine)

# Seed the default weekly schedule and starting drinks menu if the tables are
# empty. Both are idempotent, so this is safe on every startup.
_db = SessionLocal()
try:
    seed_schedule(_db)
    seed_menu(_db)
    seed_blog(_db)
finally:
    _db.close()

async def _daily_log_purge() -> None:
    """Delete expired log rows at 07:00 at the bar, every day, until cancelled.

    A plain sleeping task rather than a scheduler dependency: there is one job,
    it is idempotent, and a failure is logged and retried at tomorrow's run. The
    server must never go down because housekeeping did.

    The app runs one worker, but if a future deployment ran more than one
    process, every process would run this at the same minute. That is harmless —
    the second DELETE matches no rows — and it is why the purge is written to be
    idempotent rather than guarded by a lock that would need its own table.
    """
    while True:
        await asyncio.sleep(audit.seconds_until_next_purge())
        db = SessionLocal()
        try:
            removed = audit.purge_old_logs(db)
            logger.info(
                "Purged expired logs older than %s days: %s",
                settings.LOG_RETENTION_DAYS,
                ", ".join(f"{table}={count}" for table, count in removed.items()),
            )
        except Exception:  # noqa: BLE001 - housekeeping must not kill the app
            logger.exception("Daily log purge failed; will try again tomorrow")
            db.rollback()
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: cleanup expired sessions
    db = SessionLocal()
    try:
        auth.cleanup_expired_sessions(db)
    finally:
        db.close()

    purge_task = None
    if settings.DAILY_LOG_PURGE:
        purge_task = asyncio.create_task(_daily_log_purge())

    try:
        yield
    finally:
        # Cancelled on shutdown rather than left holding a session open.
        if purge_task is not None:
            purge_task.cancel()
            try:
                await purge_task
            except asyncio.CancelledError:
                pass


# Hide docs in production
app_configs = {"title": "Marea Alta Admin", "lifespan": lifespan}
if settings.is_production:
    app_configs["openapi_url"] = None

app = FastAPI(**app_configs)

# FastAPI's generated docs load Swagger UI from a CDN and bootstrap it with an
# inline script, neither of which the site's CSP allows. They are disabled in
# production (`openapi_url` is None), so they are simply left out of the policy
# in development rather than maintaining a second, permissive policy for a page
# that never ships.
DOCS_PATHS = frozenset({"/docs", "/redoc", "/docs/oauth2-redirect"})


def _content_security_policy(nonce: str) -> str:
    """The page's CSP, with a fresh nonce for its inline scripts.

    ``script-src`` deliberately has no ``'unsafe-inline'``. The site needs inline
    scripts for the server-rendered data seed and the admin panel needs them for
    its page logic, so each one carries this request's nonce instead. An injected
    ``<script>`` has no way to guess the nonce, so it does not run.

    ``style-src`` does allow ``'unsafe-inline'``: the admin templates use inline
    ``style=`` attributes throughout, and style attributes cannot carry a nonce.
    That is a much smaller surface than unrestricted script execution, and the
    Svelte bundle's CSS is a same-origin file either way.

    Google Fonts supplies the two typefaces, and ``Surf.svelte`` calls both
    Open-Meteo hosts directly from the browser, so both are named explicitly
    rather than opening ``connect-src`` to the whole internet.
    """
    return "; ".join(
        (
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data:",
            "connect-src 'self' https://api.open-meteo.com https://marine-api.open-meteo.com",
            "manifest-src 'self'",
            "worker-src 'self'",
        )
    )


# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    # Generated before the route runs: the HTML templates read it from here to
    # stamp their inline scripts, and the header is built from the same value.
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce

    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not (request.url.path in DOCS_PATHS and not settings.is_production):
        response.headers["Content-Security-Policy"] = _content_security_policy(nonce)
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )

    # HSTS only once TLS is actually live: sending it from a plain-HTTP
    # development server would poison the browser for localhost. The production
    # nginx redirect in docs/deployment.md is what makes this safe to turn on.
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response

# Include routers
app.include_router(auth_router.router)
app.include_router(admin.router)
app.include_router(api.router)
app.include_router(blog.router)
app.include_router(contact.router)
app.include_router(content.router)
app.include_router(newsletter.router)
app.include_router(reservations.router)
app.include_router(rsvps.router)
app.include_router(uploads.router)
app.include_router(logs.router)

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
async def index(request: Request, lang: str | None = None, db: DBSession = Depends(get_db)):
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
        html = render_index(db, lang, request.state.csp_nonce)
    except Exception:  # noqa: BLE001
        # A rendering failure must not take the homepage down. Serve the
        # un-injected shell — the SPA fills it in on mount — and leave a trace
        # for whatever error reporting the deploy has.
        logger.exception("Server-rendered schedule failed; serving the plain shell")
        html = INDEX_HTML.read_text(encoding="utf-8")

    if lang != DEFAULT_LANG:
        html = html.replace('<html lang="en">', f'<html lang="{lang}">', 1)

    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


# The standalone menu route. Its own document rather than a client-side view, so
# the URL can be shared on WhatsApp and Instagram and indexed on its own — and
# registered above the static mount, which would otherwise answer `/menu.html`
# with the un-rendered shell.
@app.api_route("/menu", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route(
    "/menu.html", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False
)
async def menu(request: Request, lang: str | None = None, db: DBSession = Depends(get_db)):
    """Public: the drinks menu, rendered into the HTML for crawlers."""
    lang = resolve_lang(lang)

    if not MENU_HTML.is_file():
        # Dev convenience when the second entry point has not been built yet.
        return JSONResponse(
            {"detail": "Frontend not built. Run `npm run build` in ../frontend."}
        )

    try:
        html = render_menu(db, lang, request.state.csp_nonce)
    except Exception:  # noqa: BLE001
        # Same bargain as the homepage: serve the shell rather than 500.
        logger.exception("Server-rendered menu failed; serving the plain shell")
        html = MENU_HTML.read_text(encoding="utf-8")

    if lang != DEFAULT_LANG:
        html = html.replace('<html lang="en">', f'<html lang="{lang}">', 1)

    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


# The news index and its individual articles share one Vite document. The
# backend injects the actual posts so a crawler (or a visitor without
# JavaScript) reads the article, and the SPA replaces that block on mount.
@app.api_route("/news", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route(
    "/news.html", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False
)
async def news(request: Request, lang: str | None = None, db: DBSession = Depends(get_db)):
    """Public: the news index, rendered into the HTML for crawlers."""
    lang = resolve_lang(lang)

    if not NEWS_HTML.is_file():
        return JSONResponse(
            {"detail": "Frontend not built. Run `npm run build` in ../frontend."}
        )

    try:
        html = render_news(db, lang, request.state.csp_nonce)
    except Exception:  # noqa: BLE001
        logger.exception("Server-rendered news failed; serving the plain shell")
        html = NEWS_HTML.read_text(encoding="utf-8")

    if lang != DEFAULT_LANG:
        html = html.replace('<html lang="en">', f'<html lang="{lang}">', 1)

    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


@app.api_route("/news/{slug}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def news_post(
    slug: str,
    request: Request,
    lang: str | None = None,
    db: DBSession = Depends(get_db),
):
    """Public: one published article, with per-post metadata and JSON-LD."""
    lang = resolve_lang(lang)

    if not NEWS_HTML.is_file():
        return JSONResponse(
            {"detail": "Frontend not built. Run `npm run build` in ../frontend."}
        )

    try:
        html = render_news_post(db, lang, slug, request.state.csp_nonce)
    except Exception:  # noqa: BLE001
        logger.exception("Server-rendered article failed; serving the plain shell")
        html = NEWS_HTML.read_text(encoding="utf-8")

    if html is None:
        try:
            html = render_news_not_found(db, lang, request.state.csp_nonce)
        except Exception:  # noqa: BLE001
            logger.exception("Server-rendered news 404 failed; serving the plain shell")
            html = NEWS_HTML.read_text(encoding="utf-8")
        if lang != DEFAULT_LANG:
            html = html.replace('<html lang="en">', f'<html lang="{lang}">', 1)
        return HTMLResponse(html, status_code=404, headers={"Cache-Control": "no-cache"})

    if lang != DEFAULT_LANG:
        html = html.replace('<html lang="en">', f'<html lang="{lang}">', 1)

    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


# The sitemap is dynamic so articles written in the panel are discoverable
# without a frontend rebuild. Registered before the static mount, which would
# otherwise serve public/sitemap.xml.
@app.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap(db: DBSession = Depends(get_db)):
    return Response(
        content=render_sitemap(db),
        media_type="application/xml",
        headers={"Cache-Control": "no-cache"},
    )


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
