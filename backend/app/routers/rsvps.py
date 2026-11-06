"""Free RSVPs for dated events (ticket #25).

An RSVP is not a reservation and not a ticket: it says "I am coming to this
event", so the bar can gauge the crowd. There is no payment, no ticket code and
no confirmation email — paid ticketing belongs to Eventbrite or Ticket Tailor,
and the notification half is #51.

The public write is rate-limited per IP with the same honeypot as the contact
form. A hidden or past event is treated as missing, so a stranger cannot use the
endpoint to discover an event that is still being planned.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app import audit
from app.config import settings
from app.database import get_db
from app.dependencies import csrf_protect, get_current_admin
from app.models import Rsvp, SpecialEvent
from app.schemas import RsvpCreated, RsvpListResponse, RsvpResponse, RsvpWrite
from app.ssr import bar_today

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

_recent_rsvps: dict[str, list[float]] = defaultdict(list)


def reset_rate_limit() -> None:
    """Clear the RSVP rate limiter. Used by the test suite."""
    _recent_rsvps.clear()


def _is_rate_limited(ip: str) -> bool:
    cutoff = time.monotonic() - settings.RATE_LIMIT_WINDOW_MINUTES * 60
    attempts = _recent_rsvps[ip]
    attempts[:] = [t for t in attempts if t > cutoff]
    return len(attempts) >= settings.RATE_LIMIT_ATTEMPTS


def _record_attempt(ip: str) -> None:
    _recent_rsvps[ip].append(time.monotonic())


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _response(row: Rsvp, event: SpecialEvent) -> RsvpResponse:
    return RsvpResponse(
        id=row.id,
        event_id=row.event_id,
        event_date=event.date,
        event_title_en=event.title_en,
        event_title_es=event.title_es,
        name=row.name,
        contact=row.contact,
        party_size=row.party_size,
        notes=row.notes,
        ip=row.ip,
        user_agent=row.user_agent,
        created_at=_utc(row.created_at),
    )


@router.post(
    "/api/special-events/{event_id}/rsvp",
    response_model=RsvpCreated,
    status_code=201,
)
async def create_rsvp(
    event_id: int,
    data: RsvpWrite,
    request: Request,
    db: DBSession = Depends(get_db),
):
    """Public: say you are coming to an upcoming, published event."""
    event = db.get(SpecialEvent, event_id)
    today = bar_today()[1]
    if event is None or not event.is_active or event.date < today:
        raise HTTPException(status_code=404, detail="Event not found")

    ip = audit.request_ip(request)
    if _is_rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many RSVPs. Please try again later.")
    _record_attempt(ip)

    if data.website:
        return RsvpCreated(ok=True)

    db.add(
        Rsvp(
            event_id=event.id,
            name=data.name,
            contact=data.contact,
            party_size=data.party_size,
            notes=data.notes,
            ip=ip,
            user_agent=audit.clean_user_agent(request.headers.get("user-agent")),
        )
    )
    db.commit()
    return RsvpCreated(ok=True)


@router.get(
    "/api/rsvps",
    response_model=RsvpListResponse,
    dependencies=[Depends(get_current_admin)],
)
async def list_rsvps(
    response: Response,
    event_id: int | None = Query(None, ge=1),
    db: DBSession = Depends(get_db),
):
    """Admin: every RSVP, newest first, with the guest count for the badge."""
    response.headers["Cache-Control"] = "no-cache"
    query = (
        select(Rsvp, SpecialEvent)
        .join(SpecialEvent, Rsvp.event_id == SpecialEvent.id)
        .order_by(Rsvp.created_at.desc(), Rsvp.id.desc())
    )
    if event_id is not None:
        query = query.where(Rsvp.event_id == event_id)

    rows = db.execute(query).all()
    return RsvpListResponse(
        rsvps=[_response(rsvp, event) for rsvp, event in rows],
        total_rsvps=len(rows),
        total_guests=sum(rsvp.party_size for rsvp, _event in rows),
    )


@router.delete("/api/rsvps/{rsvp_id}", status_code=204, dependencies=write_guard)
async def delete_rsvp(rsvp_id: int, db: DBSession = Depends(get_db)):
    """Admin: remove one RSVP (for example, a duplicate or a cancellation)."""
    row = db.get(Rsvp, rsvp_id)
    if row is None:
        raise HTTPException(status_code=404, detail="RSVP not found")
    db.delete(row)
    db.commit()
