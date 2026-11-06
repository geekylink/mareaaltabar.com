"""The public contact form and the shared admin inbox.

One public write and three session-guarded reads/writes:

* ``POST /api/contact`` — anyone may send a message. Rate-limited per IP, with a
  honeypot field, and never written to the audit log: the audit log records
  *admin* changes, and a visitor's message is not one.
* ``GET /api/submissions`` — every admin sees the same inbox, newest first.
* ``PATCH /api/submissions/{id}`` — mark read or unread.
* ``DELETE /api/submissions/{id}`` — remove a message.

The inbox is shared rather than per-admin on purpose: the bar is small, and a
message that only one person can see is a message that gets missed when that
person is off. There is no ownership column, so there is no way to hide a row
from a colleague by accident.
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
from app.models import Submission
from app.schemas import (
    ContactResponse,
    ContactWrite,
    SubmissionListResponse,
    SubmissionResponse,
    SubmissionUpdate,
)

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

# In-memory sliding window, like the login limiter. It resets on restart and is
# per-process, which is the right trade at one worker: a database-backed counter
# would add a write to every spam request, which is the load the limiter exists
# to avoid.
_recent_submissions: dict[str, list[float]] = defaultdict(list)


def reset_rate_limit() -> None:
    """Clear the contact rate limiter. Used by the test suite."""
    _recent_submissions.clear()


def _is_rate_limited(ip: str) -> bool:
    cutoff = time.monotonic() - settings.RATE_LIMIT_WINDOW_MINUTES * 60
    attempts = _recent_submissions[ip]
    attempts[:] = [t for t in attempts if t > cutoff]
    return len(attempts) >= settings.RATE_LIMIT_ATTEMPTS


def _record_attempt(ip: str) -> None:
    _recent_submissions[ip].append(time.monotonic())


def _utc(value: datetime) -> datetime:
    """Label a stored timestamp as UTC, as the logs endpoints do.

    SQLite's ``CURRENT_TIMESTAMP`` is UTC but arrives naive; a browser would read
    a zone-less ISO string as local time and show every message five hours out
    for a bar in Ecuador.
    """
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _response(row: Submission) -> SubmissionResponse:
    return SubmissionResponse(
        id=row.id,
        name=row.name,
        contact=row.contact,
        subject=row.subject,
        message=row.message,
        ip=row.ip,
        user_agent=row.user_agent,
        is_read=bool(row.is_read),
        created_at=_utc(row.created_at),
    )


# --- Public write ----------------------------------------------------------


@router.post("/api/contact", response_model=ContactResponse, status_code=201)
async def submit_contact(
    data: ContactWrite,
    request: Request,
    db: DBSession = Depends(get_db),
):
    """Public: send a message to the shared inbox.

    A filled honeypot returns the same success response and stores nothing. That
    is deliberate: a bot that is told it failed learns which field to leave
    blank next time, and a bot that is told it succeeded has no reason to retry.
    """
    ip = audit.request_ip(request)
    if _is_rate_limited(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many messages. Please try again later.",
        )
    _record_attempt(ip)

    if data.website:
        return ContactResponse(ok=True)

    submission = Submission(
        name=data.name,
        contact=data.contact,
        subject=data.subject,
        message=data.message,
        ip=ip,
        user_agent=audit.clean_user_agent(request.headers.get("user-agent")),
    )
    db.add(submission)
    db.commit()
    return ContactResponse(ok=True)


# --- Shared admin inbox ----------------------------------------------------


@router.get(
    "/api/submissions",
    response_model=SubmissionListResponse,
    dependencies=[Depends(get_current_admin)],
)
async def list_submissions(
    response: Response,
    db: DBSession = Depends(get_db),
):
    """Admin: every message, newest first, plus the unread count.

    The count travels with the list rather than in a second request, so the
    badge on the dashboard and the rows in the inbox cannot disagree.
    """
    response.headers["Cache-Control"] = "no-cache"
    rows = db.execute(
        select(Submission).order_by(Submission.created_at.desc(), Submission.id.desc())
    ).scalars().all()
    return SubmissionListResponse(
        submissions=[_response(row) for row in rows],
        unread=sum(1 for row in rows if not row.is_read),
    )


@router.patch(
    "/api/submissions/{submission_id}",
    response_model=SubmissionResponse,
    dependencies=write_guard,
)
async def update_submission(
    submission_id: int,
    data: SubmissionUpdate,
    db: DBSession = Depends(get_db),
):
    """Admin: mark a message read or unread. The text itself is immutable."""
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Message not found")

    submission.is_read = data.is_read
    db.commit()
    db.refresh(submission)
    return _response(submission)


@router.delete(
    "/api/submissions/{submission_id}",
    status_code=204,
    dependencies=write_guard,
)
async def delete_submission(
    submission_id: int,
    db: DBSession = Depends(get_db),
):
    """Admin: remove a message from the shared inbox."""
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(submission)
    db.commit()
