"""Public newsletter signup and the admin subscriber list (ticket #12).

There is deliberately no delivery provider here. The signup stores an address,
its consent timestamp and where it came from; the owner can list, deactivate or
export the list and paste it into whichever provider they choose. That is the
honest version of "newsletter" until an account exists (#12's delivery half).

The public write is rate-limited per IP and has the same honeypot as the contact
form. A duplicate address returns the same success response as a new one and
never creates a second row: telling a bot which addresses are already subscribed
is a small but free information leak.
"""

import csv
import io
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
from app.models import Subscriber
from app.schemas import (
    NewsletterResponse,
    NewsletterWrite,
    SubscriberListResponse,
    SubscriberResponse,
    SubscriberUpdate,
)

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

# Separate window from the contact form: someone signing up for a newsletter is
# not the same caller as someone sending a message, and one should not exhaust
# the other's allowance.
_recent_signups: dict[str, list[float]] = defaultdict(list)


def reset_rate_limit() -> None:
    """Clear the newsletter rate limiter. Used by the test suite."""
    _recent_signups.clear()


def _is_rate_limited(ip: str) -> bool:
    cutoff = time.monotonic() - settings.RATE_LIMIT_WINDOW_MINUTES * 60
    attempts = _recent_signups[ip]
    attempts[:] = [t for t in attempts if t > cutoff]
    return len(attempts) >= settings.RATE_LIMIT_ATTEMPTS


def _record_attempt(ip: str) -> None:
    _recent_signups[ip].append(time.monotonic())


def _utc(value: datetime | None) -> datetime | None:
    """Label a stored timestamp UTC, as the inbox and logs do."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _response(row: Subscriber) -> SubscriberResponse:
    return SubscriberResponse(
        id=row.id,
        email=row.email,
        name=row.name,
        consented_at=_utc(row.consented_at),
        ip=row.ip,
        user_agent=row.user_agent,
        is_active=bool(row.is_active),
        created_at=_utc(row.created_at),
    )


# --- Public write ----------------------------------------------------------


@router.post("/api/newsletter", response_model=NewsletterResponse, status_code=201)
async def subscribe(
    data: NewsletterWrite,
    request: Request,
    db: DBSession = Depends(get_db),
):
    """Public: add an address to the list, once.

    The honeypot returns success and stores nothing. The response is identical
    to a real signup, so a bot cannot tell that it was caught.
    """
    ip = audit.request_ip(request)
    if _is_rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many signups. Please try again later.")
    _record_attempt(ip)

    if data.website:
        return NewsletterResponse(ok=True)

    existing = db.execute(
        select(Subscriber).where(Subscriber.email == data.email)
    ).scalar_one_or_none()
    if existing is not None:
        return NewsletterResponse(ok=True)

    subscriber = Subscriber(
        email=data.email,
        name=data.name,
        consented_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ip=ip,
        user_agent=audit.clean_user_agent(request.headers.get("user-agent")),
    )
    db.add(subscriber)
    db.commit()
    return NewsletterResponse(ok=True)


# --- Admin list ------------------------------------------------------------


@router.get(
    "/api/subscribers",
    response_model=SubscriberListResponse,
    dependencies=[Depends(get_current_admin)],
)
async def list_subscribers(response: Response, db: DBSession = Depends(get_db)):
    """Admin: every subscriber, newest first, with the active count."""
    response.headers["Cache-Control"] = "no-cache"
    rows = db.execute(
        select(Subscriber).order_by(Subscriber.created_at.desc(), Subscriber.id.desc())
    ).scalars().all()
    return SubscriberListResponse(
        subscribers=[_response(row) for row in rows],
        total=len(rows),
        active=sum(1 for row in rows if row.is_active),
    )


@router.get("/api/subscribers/export.csv", dependencies=[Depends(get_current_admin)])
async def export_subscribers(db: DBSession = Depends(get_db)):
    """Admin: the active list as CSV, ready to import into a provider.

    Only active addresses are exported: an unsubscribed row stays in the panel
    for the record, but sending to it is exactly what unsubscribing asked us not
    to do. The file is generated in memory rather than on disk, so there is no
    second copy of the list to clean up.
    """
    rows = db.execute(
        select(Subscriber)
        .where(Subscriber.is_active.is_(True))
        .order_by(Subscriber.created_at, Subscriber.id)
    ).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["email", "name", "consented_at", "created_at"])
    for row in rows:
        writer.writerow([
            row.email,
            row.name,
            row.consented_at.isoformat() if row.consented_at else "",
            row.created_at.isoformat() if row.created_at else "",
        ])

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="subscribers.csv"'},
    )


@router.patch(
    "/api/subscribers/{subscriber_id}",
    response_model=SubscriberResponse,
    dependencies=write_guard,
)
async def update_subscriber(
    subscriber_id: int,
    data: SubscriberUpdate,
    db: DBSession = Depends(get_db),
):
    """Admin: unsubscribe or re-subscribe an address without deleting it."""
    subscriber = db.get(Subscriber, subscriber_id)
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    subscriber.is_active = data.is_active
    db.commit()
    db.refresh(subscriber)
    return _response(subscriber)


@router.delete("/api/subscribers/{subscriber_id}", status_code=204, dependencies=write_guard)
async def delete_subscriber(subscriber_id: int, db: DBSession = Depends(get_db)):
    """Admin: remove an address entirely."""
    subscriber = db.get(Subscriber, subscriber_id)
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    db.delete(subscriber)
    db.commit()
