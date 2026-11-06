"""Read-only endpoints for the admin logs.

Three GETs — every login attempt, every menu change, every schedule change —
feeding the ``/admin/logs`` page. They are separate endpoints rather than one
with a filter so that no caller can ask for the wrong area: the menu log and the
schedule log are different questions, and the panel shows them as different tabs.

Every route here is a GET and every one requires a session. There is no write
path to either table anywhere in the application, which is what makes the page
strictly read-only rather than read-only by convention — a POST to any of these
paths is a 405, not a rejected payload.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session as DBSession

from app import audit
from app.database import get_db
from app.dependencies import get_current_admin
from app.models import AuditEntry, LoginAttempt
from app.schemas import AuditEntryResponse, AuditLogResponse, LoginAttemptResponse, LoginLogResponse

router = APIRouter(dependencies=[Depends(get_current_admin)])

# Revalidate like the other reads, so an edit made in one tab shows up in another.
READ_CACHE_CONTROL = {"Cache-Control": "no-cache"}

# The panel asks for a screenful. A hard ceiling keeps a hand-typed
# ``?limit=100000`` from pulling the whole table into memory in one response.
DEFAULT_LIMIT = 200
MAX_LIMIT = 500


def _page(limit: int, offset: int) -> tuple[int, int]:
    """Clamp paging arguments to something a log page can actually serve."""
    return max(1, min(limit, MAX_LIMIT)), max(0, offset)


def _utc(value) -> datetime:
    """A stored timestamp, labelled as UTC.

    ``created_at`` comes from SQLite's ``CURRENT_TIMESTAMP``, so it is UTC
    already but arrives naive and would serialise without a zone. A browser
    reading a zone-less ISO string assumes *its own* offset, which would show
    every entry five hours out for a bar in Ecuador; stamping it here means the
    page can format it in the reader's locale and be right.
    """
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _login_response(row: LoginAttempt) -> LoginAttemptResponse:
    return LoginAttemptResponse(
        id=row.id,
        username=row.username,
        ip=row.ip,
        outcome=row.outcome,
        user_agent=row.user_agent,
        created_at=_utc(row.created_at),
    )


def _audit_response(row: AuditEntry) -> AuditEntryResponse:
    return AuditEntryResponse(
        id=row.id,
        area=row.area,
        action=row.action,
        admin_username=row.admin_username,
        ip=row.ip,
        user_agent=row.user_agent,
        target=row.target,
        target_name=row.target_name,
        details=row.details or {},
        created_at=_utc(row.created_at),
    )


@router.get("/api/logs/logins", response_model=LoginLogResponse)
async def get_login_log(
    response: Response,
    limit: int = Query(DEFAULT_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    """Admin: every login attempt, newest first.

    Successful and failed attempts together, because the failed ones are the
    interesting half: a run of wrong passwords from one address is the thing an
    owner needs to see, and it is invisible in a log of logins that worked.
    """
    response.headers.update(READ_CACHE_CONTROL)
    limit, offset = _page(limit, offset)
    return LoginLogResponse(
        entries=[_login_response(row) for row in audit.list_login_attempts(db, limit=limit, offset=offset)],
        total=audit.count_logins(db),
    )


@router.get("/api/logs/menu", response_model=AuditLogResponse)
async def get_menu_change_log(
    response: Response,
    limit: int = Query(DEFAULT_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    """Admin: every change to the drinks menu — sections, drinks and promos."""
    response.headers.update(READ_CACHE_CONTROL)
    limit, offset = _page(limit, offset)
    return AuditLogResponse(
        area=audit.AREA_MENU,
        entries=[
            _audit_response(row)
            for row in audit.list_audit_entries(
                db, area=audit.AREA_MENU, limit=limit, offset=offset
            )
        ],
        total=audit.count_audit_entries(db, audit.AREA_MENU),
    )


@router.get("/api/logs/content", response_model=AuditLogResponse)
async def get_content_change_log(
    response: Response,
    limit: int = Query(DEFAULT_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    """Admin: every change to the generic content sections and their items."""
    response.headers.update(READ_CACHE_CONTROL)
    limit, offset = _page(limit, offset)
    return AuditLogResponse(
        area=audit.AREA_CONTENT,
        entries=[
            _audit_response(row)
            for row in audit.list_audit_entries(
                db, area=audit.AREA_CONTENT, limit=limit, offset=offset
            )
        ],
        total=audit.count_audit_entries(db, audit.AREA_CONTENT),
    )


@router.get("/api/logs/schedule", response_model=AuditLogResponse)
async def get_schedule_change_log(
    response: Response,
    limit: int = Query(DEFAULT_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    """Admin: every change to the week — party text, opening hours and closures.

    Closures are in here because they are schedule content edited on the same
    page: a closure added on a holiday is as much a change to when the bar is
    open as moving Friday's closing time is.
    """
    response.headers.update(READ_CACHE_CONTROL)
    limit, offset = _page(limit, offset)
    return AuditLogResponse(
        area=audit.AREA_SCHEDULE,
        entries=[
            _audit_response(row)
            for row in audit.list_audit_entries(
                db, area=audit.AREA_SCHEDULE, limit=limit, offset=offset
            )
        ],
        total=audit.count_audit_entries(db, audit.AREA_SCHEDULE),
    )
