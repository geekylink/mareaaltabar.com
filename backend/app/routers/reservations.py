"""Reservation requests and their admin queue (ticket #14).

A visitor asks for a table; nothing is promised. Every row starts ``pending``
and an admin confirms or declines it in the panel. There is no email or WhatsApp
notification because #51 is not built, so the panel queue is the notification.

Defaults, all reversible decisions rather than policies: at most 20 guests per
request, up to 90 days ahead, at least today at the bar. A deposit, a lead time
or a no-show rule would be business decisions and are not encoded here.
"""

import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app import audit
from app.config import settings
from app.database import get_db
from app.dependencies import csrf_protect, get_current_admin
from app.models import Reservation
from app.schemas import (
    ReservationCreated,
    ReservationListResponse,
    ReservationResponse,
    ReservationUpdate,
    ReservationWrite,
)

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

_recent_requests: dict[str, list[float]] = defaultdict(list)


def reset_rate_limit() -> None:
    """Clear the reservation rate limiter. Used by the test suite."""
    _recent_requests.clear()


def _is_rate_limited(ip: str) -> bool:
    cutoff = time.monotonic() - settings.RATE_LIMIT_WINDOW_MINUTES * 60
    attempts = _recent_requests[ip]
    attempts[:] = [t for t in attempts if t > cutoff]
    return len(attempts) >= settings.RATE_LIMIT_ATTEMPTS


def _record_attempt(ip: str) -> None:
    _recent_requests[ip].append(time.monotonic())


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _response(row: Reservation) -> ReservationResponse:
    return ReservationResponse(
        id=row.id,
        date=row.date,
        time=row.time,
        party_size=row.party_size,
        name=row.name,
        contact=row.contact,
        notes=row.notes,
        status=row.status,
        ip=row.ip,
        user_agent=row.user_agent,
        created_at=_utc(row.created_at),
        updated_at=_utc(row.updated_at),
    )


@router.post("/api/reservations", response_model=ReservationCreated, status_code=201)
async def request_reservation(
    data: ReservationWrite,
    request: Request,
    db: DBSession = Depends(get_db),
):
    """Public: ask for a table. The request is pending until an admin answers."""
    ip = audit.request_ip(request)
    if _is_rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    _record_attempt(ip)

    if data.website:
        return ReservationCreated(ok=True)

    reservation = Reservation(
        date=data.date.isoformat(),
        time=data.time,
        party_size=data.party_size,
        name=data.name,
        contact=data.contact,
        notes=data.notes,
        status="pending",
        ip=ip,
        user_agent=audit.clean_user_agent(request.headers.get("user-agent")),
    )
    db.add(reservation)
    db.commit()
    return ReservationCreated(ok=True)


@router.get(
    "/api/reservations",
    response_model=ReservationListResponse,
    dependencies=[Depends(get_current_admin)],
)
async def list_reservations(response: Response, db: DBSession = Depends(get_db)):
    """Admin: every request, newest first, with the pending count for the badge."""
    response.headers["Cache-Control"] = "no-cache"
    rows = db.execute(
        select(Reservation).order_by(Reservation.created_at.desc(), Reservation.id.desc())
    ).scalars().all()
    return ReservationListResponse(
        reservations=[_response(row) for row in rows],
        pending=sum(1 for row in rows if row.status == "pending"),
    )


@router.patch(
    "/api/reservations/{reservation_id}",
    response_model=ReservationResponse,
    dependencies=write_guard,
)
async def update_reservation(
    reservation_id: int,
    data: ReservationUpdate,
    db: DBSession = Depends(get_db),
):
    """Admin: confirm, decline or return a request to pending."""
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    reservation.status = data.status
    db.commit()
    db.refresh(reservation)
    return _response(reservation)


@router.delete("/api/reservations/{reservation_id}", status_code=204, dependencies=write_guard)
async def delete_reservation(reservation_id: int, db: DBSession = Depends(get_db)):
    """Admin: remove a request from the queue."""
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    db.delete(reservation)
    db.commit()
