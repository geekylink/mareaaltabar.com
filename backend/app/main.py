"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import auth
from app.config import settings
from app.database import SessionLocal, engine
from app.models import Base
from app.routers import admin, api, auth as auth_router

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Seed initial data if tables are empty
def seed_data():
    from app.models import Event, Hours
    from sqlalchemy import select

    db = SessionLocal()
    try:
        # Seed events if empty
        result = db.execute(select(Event).limit(1))
        if result.scalar_one_or_none() is None:
            events = [
                Event(day=0, time="8 PM - 2 AM", title="Latin Night", note="Salsa, bachata and reggaeton all night."),
                Event(day=1, time="8 PM - 4 AM", title="Singles Night", note="Mingle with the singles."),
                Event(day=2, time="", title="Closed", note=""),
                Event(day=3, time="", title="Closed", note=""),
                Event(day=4, time="8 PM - 4 AM", title="Open Mic Night", note="Come play music with us, bring an instrument or sing or play one of ours."),
                Event(day=5, time="8 PM - 4 AM", title="Live Music", note="Live music all night."),
                Event(day=6, time="8 PM - 4 AM", title="Live Music", note="The big one. Arrive early for a spot."),
            ]
            db.add_all(events)

        # Seed hours if empty
        result = db.execute(select(Hours).limit(1))
        if result.scalar_one_or_none() is None:
            hours = [
                Hours(day=0, open_time="4:00 PM", close_time="2:00 AM"),
                Hours(day=1, open_time="4:00 PM", close_time="4:00 AM"),
                Hours(day=2, open_time="", close_time="", is_closed=True),
                Hours(day=3, open_time="", close_time="", is_closed=True),
                Hours(day=4, open_time="4:00 PM", close_time="4:00 AM"),
                Hours(day=5, open_time="4:00 PM", close_time="4:00 AM"),
                Hours(day=6, open_time="4:00 PM", close_time="4:00 AM"),
            ]
            db.add_all(hours)

        db.commit()
    finally:
        db.close()


seed_data()


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


@app.get("/")
async def root():
    return {"message": "Marea Alta API. Admin panel at /admin"}
