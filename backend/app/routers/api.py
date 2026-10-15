"""JSON API for the weekly schedule.

``/api/schedule`` merges the event and its opening hours into a single resource
per weekday, so an admin edits a day's description and its times in one place
and saves them atomically.

Read endpoints are public (the website needs them). Writes require an
authenticated admin session plus a CSRF token.
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
    ClosedDayUpdate,
    DayScheduleResponse,
    DayScheduleUpdate,
)
from app.ssr import day_payload, load_closed_days, load_schedule

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

# Revalidate so admin edits appear without visitors hard-refreshing.
READ_CACHE_CONTROL = {"Cache-Control": "no-cache"}


# --- Weekly schedule ---

@router.get("/api/schedule", response_model=list[DayScheduleResponse])
async def get_schedule(response: Response, db: DBSession = Depends(get_db)):
    """Public: the full week, both languages, ready for the visitor's locale."""
    response.headers.update(READ_CACHE_CONTROL)
    return load_schedule(db)


@router.put("/api/schedule/{day}", response_model=DayScheduleResponse, dependencies=write_guard)
async def update_day(day: int, data: DayScheduleUpdate, db: DBSession = Depends(get_db)):
    """Admin: save a day's titles, descriptions and hours together."""
    if day < 0 or day > 6:
        raise HTTPException(status_code=400, detail="Day must be 0-6")

    event = db.execute(select(Event).where(Event.day == day)).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Day not found")

    hours = db.execute(select(Hours).where(Hours.day == day)).scalar_one_or_none()
    if hours is None:
        hours = Hours(day=day)
        db.add(hours)

    event.title_en = data.title_en
    event.title_es = data.title_es
    event.note_en = data.note_en
    event.note_es = data.note_es

    hours.open_time = data.open_time
    hours.close_time = data.close_time
    hours.is_closed = data.is_closed

    db.commit()
    db.refresh(event)
    db.refresh(hours)
    return day_payload(event, hours)


# --- Closed days (bilingual reason) ---

@router.get("/api/closed-days", response_model=list[ClosedDayResponse])
async def list_closed_days(response: Response, db: DBSession = Depends(get_db)):
    """Public: one-off date closures (holidays, private events)."""
    response.headers.update(READ_CACHE_CONTROL)
    return load_closed_days(db)


@router.post(
    "/api/closed-days",
    response_model=ClosedDayResponse,
    status_code=201,
    dependencies=write_guard,
)
async def create_closed_day(data: ClosedDayCreate, db: DBSession = Depends(get_db)):
    """Admin: add a one-off closure with a reason in both languages."""
    iso_date = data.date.isoformat()

    existing = db.execute(select(ClosedDay).where(ClosedDay.date == iso_date)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Closed day already exists for this date")

    closed_day = ClosedDay(
        date=iso_date,
        reason_en=data.reason_en,
        reason_es=data.reason_es,
    )
    db.add(closed_day)
    db.commit()
    db.refresh(closed_day)
    return ClosedDayResponse(
        id=closed_day.id,
        date=closed_day.date,
        reason_en=closed_day.reason_en,
        reason_es=closed_day.reason_es,
    )


@router.patch(
    "/api/closed-days/{closed_day_id}",
    response_model=ClosedDayResponse,
    dependencies=write_guard,
)
async def update_closed_day(
    closed_day_id: int, data: ClosedDayUpdate, db: DBSession = Depends(get_db)
):
    """Admin: correct the wording of a closure after the fact."""
    closed_day = db.execute(
        select(ClosedDay).where(ClosedDay.id == closed_day_id)
    ).scalar_one_or_none()
    if closed_day is None:
        raise HTTPException(status_code=404, detail="Closed day not found")

    closed_day.reason_en = data.reason_en
    closed_day.reason_es = data.reason_es
    db.commit()
    db.refresh(closed_day)
    return ClosedDayResponse(
        id=closed_day.id,
        date=closed_day.date,
        reason_en=closed_day.reason_en,
        reason_es=closed_day.reason_es,
    )


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