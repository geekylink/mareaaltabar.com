"""JSON API for the party schedule.

Read endpoints are public so the website can render the schedule.
Write endpoints require an authenticated admin session plus a CSRF token.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.dependencies import csrf_protect, get_current_admin
from app.models import ClosedDay, Event, Hours
from app.schemas import (
    ClosedDayCreate,
    ClosedDayResponse,
    EventResponse,
    EventUpdate,
    HoursResponse,
    HoursUpdate,
)

router = APIRouter()

# Writes require a logged-in admin; reads are deliberately public.
write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

# Revalidate on every request so admin edits appear without a hard refresh.
READ_CACHE_CONTROL = {"Cache-Control": "no-cache"}


# --- Events ---

@router.get("/api/events", response_model=list[EventResponse])
async def list_events(response: Response, db: DBSession = Depends(get_db)):
    """Public: the 7 weekly party entries."""
    response.headers.update(READ_CACHE_CONTROL)
    events = db.execute(select(Event).order_by(Event.day)).scalars().all()
    return [
        EventResponse(day=e.day, title=e.title, note=e.note, time=e.time)
        for e in events
    ]


@router.put("/api/events/{day}", response_model=EventUpdate, dependencies=write_guard)
async def update_event(day: int, data: EventUpdate, db: DBSession = Depends(get_db)):
    """Admin: replace the event details for one weekday."""
    if day < 0 or day > 6:
        raise HTTPException(status_code=400, detail="Day must be 0-6")

    event = db.execute(select(Event).where(Event.day == day)).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    event.title = data.title
    event.note = data.note
    event.time = data.time
    db.commit()
    return data


# --- Hours ---

@router.get("/api/hours", response_model=list[HoursResponse])
async def list_hours(response: Response, db: DBSession = Depends(get_db)):
    """Public: opening hours and per-weekday closed flags."""
    response.headers.update(READ_CACHE_CONTROL)
    hours = db.execute(select(Hours).order_by(Hours.day)).scalars().all()
    return [
        HoursResponse(day=h.day, open_time=h.open_time, close_time=h.close_time, is_closed=h.is_closed)
        for h in hours
    ]


@router.put("/api/hours/{day}", response_model=HoursUpdate, dependencies=write_guard)
async def update_hours(day: int, data: HoursUpdate, db: DBSession = Depends(get_db)):
    """Admin: set opening hours or mark a weekday closed."""
    if day < 0 or day > 6:
        raise HTTPException(status_code=400, detail="Day must be 0-6")

    hours = db.execute(select(Hours).where(Hours.day == day)).scalar_one_or_none()
    if hours is None:
        raise HTTPException(status_code=404, detail="Hours not found")

    hours.open_time = data.open_time
    hours.close_time = data.close_time
    hours.is_closed = data.is_closed
    db.commit()
    return data


# --- Closed Days ---

@router.get("/api/closed-days", response_model=list[ClosedDayResponse])
async def list_closed_days(response: Response, db: DBSession = Depends(get_db)):
    """Public: one-off date closures (holidays, private events)."""
    response.headers.update(READ_CACHE_CONTROL)
    days = db.execute(select(ClosedDay).order_by(ClosedDay.date)).scalars().all()
    return [ClosedDayResponse(id=d.id, date=d.date, reason=d.reason) for d in days]


@router.post(
    "/api/closed-days",
    response_model=ClosedDayResponse,
    status_code=201,
    dependencies=write_guard,
)
async def create_closed_day(data: ClosedDayCreate, db: DBSession = Depends(get_db)):
    """Admin: add a one-off closure."""
    iso_date = data.date.isoformat()

    existing = db.execute(select(ClosedDay).where(ClosedDay.date == iso_date)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Closed day already exists for this date")

    closed_day = ClosedDay(date=iso_date, reason=data.reason)
    db.add(closed_day)
    db.commit()
    db.refresh(closed_day)
    return ClosedDayResponse(id=closed_day.id, date=closed_day.date, reason=closed_day.reason)


@router.delete("/api/closed-days/{closed_day_id}", status_code=204, dependencies=write_guard)
async def delete_closed_day(closed_day_id: int, db: DBSession = Depends(get_db)):
    """Admin: remove a one-off closure."""
    closed_day = db.execute(
        select(ClosedDay).where(ClosedDay.id == closed_day_id)
    ).scalar_one_or_none()
    if closed_day is None:
        raise HTTPException(status_code=404, detail="Closed day not found")

    db.delete(closed_day)
    db.commit()