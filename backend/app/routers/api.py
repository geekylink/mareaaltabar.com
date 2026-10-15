"""JSON API endpoints for events, hours, and closed days."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.dependencies import csrf_protect, get_current_admin
from app.models import Admin, ClosedDay, Event, Hours
from app.schemas import (
    ClosedDayCreate,
    ClosedDayResponse,
    EventResponse,
    EventUpdate,
    HoursResponse,
    HoursUpdate,
)

router = APIRouter(dependencies=[Depends(get_current_admin)])


# --- Events ---

@router.get("/api/events", response_model=list[EventResponse])
async def list_events(db: DBSession = Depends(get_db)):
    result = db.execute(select(Event).order_by(Event.day))
    events = result.scalars().all()
    return [
        EventResponse(day=e.day, title=e.title, note=e.note, time=e.time)
        for e in events
    ]


@router.put("/api/events/{day}", response_model=EventResponse)
async def update_event(
    day: int,
    data: EventUpdate,
    db: DBSession = Depends(get_db),
    _: None = Depends(csrf_protect),
):
    if day < 0 or day > 6:
        raise HTTPException(status_code=400, detail="Day must be 0-6")

    result = db.execute(select(Event).where(Event.day == day))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    event.title = data.title
    event.note = data.note
    event.time = data.time
    db.commit()
    db.refresh(event)

    return EventResponse(day=event.day, title=event.title, note=event.note, time=event.time)


# --- Hours ---

@router.get("/api/hours", response_model=list[HoursResponse])
async def list_hours(db: DBSession = Depends(get_db)):
    result = db.execute(select(Hours).order_by(Hours.day))
    hours = result.scalars().all()
    return [
        HoursResponse(day=h.day, open_time=h.open_time, close_time=h.close_time, is_closed=h.is_closed)
        for h in hours
    ]


@router.put("/api/hours/{day}", response_model=HoursResponse)
async def update_hours(
    day: int,
    data: HoursUpdate,
    db: DBSession = Depends(get_db),
    _: None = Depends(csrf_protect),
):
    if day < 0 or day > 6:
        raise HTTPException(status_code=400, detail="Day must be 0-6")

    result = db.execute(select(Hours).where(Hours.day == day))
    hours = result.scalar_one_or_none()
    if hours is None:
        raise HTTPException(status_code=404, detail="Hours not found")

    hours.open_time = data.open_time
    hours.close_time = data.close_time
    hours.is_closed = data.is_closed
    db.commit()
    db.refresh(hours)

    return HoursResponse(day=hours.day, open_time=hours.open_time, close_time=hours.close_time, is_closed=hours.is_closed)


# --- Closed Days ---

@router.get("/api/closed-days", response_model=list[ClosedDayResponse])
async def list_closed_days(db: DBSession = Depends(get_db)):
    result = db.execute(select(ClosedDay).order_by(ClosedDay.date))
    days = result.scalars().all()
    return [ClosedDayResponse(id=d.id, date=d.date, reason=d.reason) for d in days]


@router.post("/api/closed-days", response_model=ClosedDayResponse, status_code=201)
async def create_closed_day(
    data: ClosedDayCreate,
    db: DBSession = Depends(get_db),
    _: None = Depends(csrf_protect),
):
    existing = db.execute(select(ClosedDay).where(ClosedDay.date == data.date)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Closed day already exists for this date")

    closed_day = ClosedDay(date=data.date, reason=data.reason)
    db.add(closed_day)
    db.commit()
    db.refresh(closed_day)

    return ClosedDayResponse(id=closed_day.id, date=closed_day.date, reason=closed_day.reason)


@router.delete("/api/closed-days/{closed_day_id}", status_code=204)
async def delete_closed_day(
    closed_day_id: int,
    db: DBSession = Depends(get_db),
    _: None = Depends(csrf_protect),
):
    result = db.execute(select(ClosedDay).where(ClosedDay.id == closed_day_id))
    closed_day = result.scalar_one_or_none()
    if closed_day is None:
        raise HTTPException(status_code=404, detail="Closed day not found")

    db.delete(closed_day)
    db.commit()
