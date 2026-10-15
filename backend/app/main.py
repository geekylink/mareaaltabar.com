"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app import auth
from app.config import BACKEND_DIR, settings
from app.database import SessionLocal, engine
from app.migrate import run_migrations
from app.models import Base
from app.routers import admin, api, auth as auth_router
from app.seed import seed_schedule

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
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
else:
    # Dev convenience when the frontend has not been built yet.
    @app.get("/")
    async def root():
        return {"detail": "Frontend not built. Run `npm run build` in ../frontend."}
