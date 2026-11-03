"""Writing and retaining the admin logs.

Two tables, two jobs. ``login_attempts`` records every ``POST /admin/login`` so a
brute-force run against the panel leaves a trail, and ``audit_log`` records who
changed the menu or the schedule and exactly what they changed. Both are
append-only: the routers that serve them are GET-only, so the logs cannot be
edited or erased through the application — the one exception is the retention
purge at the bottom of this module, which deletes rows on their way out.

A login row is written defensively (:func:`log_login_attempt` swallows its own
errors) because a full disk must not stop the owner logging in to fix the disk. A
change row is *not* written defensively (:func:`log_change` adds to the caller's
session and lets the caller's own commit publish both): an edit that cannot be
logged is an edit that should not have happened.
"""

import logging
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import AuditEntry, LoginAttempt
from app.ssr import BAR_UTC_OFFSET

log = logging.getLogger(__name__)

# The three ways a login can end. Anything else is a bug, and the read endpoint
# renders the raw value rather than hiding it.
OUTCOME_SUCCESS = "success"
OUTCOME_INVALID = "invalid_credentials"
OUTCOME_RATE_LIMITED = "rate_limited"

# Which part of the site a change belongs to. The logs page shows one log per
# area, so this is the only thing separating Friday's hours from a cocktail price.
AREA_MENU = "menu"
AREA_SCHEDULE = "schedule"

ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"

# `target` is a "<kind>:<id>" key rather than a sentence, so the panel can render
# the row in whichever language it is currently in — a weekday name and a menu
# item name are both translatable, but only the item name is data.
TARGET_SCHEDULE_DAY = "schedule_day"
TARGET_CLOSED_DAY = "closed_day"
TARGET_MENU_CATEGORY = "menu_category"
TARGET_MENU_ITEM = "menu_item"
# Notices are logged in the schedule area: a closure notice is schedule news,
# and a fourth tab on /admin/logs would separate two halves of the same job.
TARGET_NOTICE = "notice"

# 07:00 at the bar, which is when the retention purge runs.
PURGE_HOUR_BAR = 7

# Long enough for a browser string to be recognisable, short enough that the
# column is not a dumping ground for whatever a client decides to send.
USER_AGENT_MAX = 255

# A typed username is unbounded; the column is not.
USERNAME_MAX = 128


class ChangeAuthor(NamedTuple):
    """Who is making a change, and where the request came from.

    Produced by :func:`app.dependencies.change_author` and handed to
    :func:`log_change`. One object rather than three parameters because every
    write handler needs the same three, and a log entry that is missing its IP
    because a handler forgot a keyword argument is worse than no log at all.
    """

    username: str
    ip: str
    user_agent: str


def request_ip(request) -> str:
    """The caller's IP, or ``"unknown"`` when the client is not visible.

    This is the peer address the server saw, which is what the rest of the auth
    code uses. Behind a proxy that is the proxy's address, not the visitor's.
    """
    client = getattr(request, "client", None)
    return client.host if client else "unknown"


def clean_username(username: str | None) -> str:
    """A typed username, trimmed and bounded for the column."""
    return (username or "").strip()[:USERNAME_MAX]


def clean_user_agent(user_agent: str | None) -> str:
    return (user_agent or "").strip()[:USER_AGENT_MAX]


def log_login_attempt(
    db: DBSession,
    *,
    username: str,
    ip: str,
    user_agent: str = "",
    outcome: str,
) -> LoginAttempt:
    """Record one login attempt.

    The password is not a parameter, so there is no path by which it can reach
    this row. Failures are logged and swallowed: the attempt is still worth
    recording, but a broken log must not turn a valid login into an error page —
    which is exactly when someone would most need to get in.
    """
    entry = LoginAttempt(
        username=clean_username(username),
        ip=ip or "unknown",
        outcome=outcome,
        user_agent=clean_user_agent(user_agent),
    )
    try:
        db.add(entry)
        db.commit()
    except Exception:  # noqa: BLE001 - see the docstring
        log.exception("Could not write the login attempt to the log")
        db.rollback()
    return entry


def snapshot(row, fields: Sequence[str]) -> dict[str, Any]:
    """The named fields of a row as a plain dict, ready for the log or a diff."""
    return {field: getattr(row, field, None) for field in fields}


def diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Only the fields whose value actually changed, as ``{field: {from, to}}``.

    Saving an unchanged form writes nothing at all, so every entry in the log is
    a real edit. That is the whole reason this is not just a before/after pair:
    a week of "Save all days" presses would bury the one save that mattered.
    """
    changed: dict[str, Any] = {}
    for field, new_value in after.items():
        old_value = before.get(field)
        if old_value != new_value:
            changed[field] = {"from": old_value, "to": new_value}
    return changed


def log_change(
    db: DBSession,
    *,
    area: str,
    action: str,
    author: ChangeAuthor,
    target: str,
    target_name: str = "",
    details: Mapping[str, Any] | None = None,
) -> AuditEntry | None:
    """Record one change, in the transaction the caller is about to commit.

    ``db.add`` only — the caller's ``commit`` publishes the edit and its log row
    together, so one cannot exist without the other. Returns ``None`` for an
    update whose ``details`` came back empty from :func:`diff`: nothing changed,
    so there is nothing to record.
    """
    payload = dict(details or {})
    if not payload and action == ACTION_UPDATE:
        return None

    entry = AuditEntry(
        area=area,
        action=action,
        admin_username=author.username,
        ip=author.ip or "unknown",
        user_agent=clean_user_agent(author.user_agent),
        target=target[:64],
        target_name=target_name[:255],
        details=payload,
    )
    db.add(entry)
    return entry


def format_target(kind: str, identifier: str | int) -> str:
    """The ``<kind>:<id>`` key stored in ``audit_log.target``."""
    return f"{kind}:{identifier}"


# --- Reading ---------------------------------------------------------------
#
# The routers do the selecting; these two keep the "newest first, and tell me how
# many there are" query in one place so all three logs page identically.


def count_entries(db: DBSession, model, **filters) -> int:
    query = select(func.count()).select_from(model)
    return db.execute(query.filter_by(**filters)).scalar_one()


def list_entries(
    db: DBSession,
    model,
    *,
    limit: int,
    offset: int,
    **filters,
) -> list:
    """One page of log rows, newest first.

    ``id`` breaks the ordering: several rows can share a ``created_at`` second
    (SQLite's clock has no sub-second resolution here, and "Save all days" writes
    seven in a row), and without it pages would overlap or skip rows.
    """
    query = (
        select(model)
        .filter_by(**filters)
        .order_by(model.created_at.desc(), model.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(query).scalars())


def count_logins(db: DBSession) -> int:
    return count_entries(db, LoginAttempt)


def count_audit_entries(db: DBSession, area: str) -> int:
    return count_entries(db, AuditEntry, area=area)


def list_login_attempts(db: DBSession, *, limit: int, offset: int) -> list[LoginAttempt]:
    return list_entries(db, LoginAttempt, limit=limit, offset=offset)


def list_audit_entries(
    db: DBSession, *, area: str, limit: int, offset: int
) -> list[AuditEntry]:
    return list_entries(db, AuditEntry, area=area, limit=limit, offset=offset)


# --- Retention -------------------------------------------------------------


def purge_old_logs(db: DBSession, days: int | None = None) -> dict[str, int]:
    """Delete log rows older than ``days``. Returns rows removed per table.

    This is the only code in the project that deletes from either table. It is
    deliberately blunt rather than selective — a log nobody has read in three
    months is not evidence anyone is going to miss — and idempotent, so the
    scheduled purge and the CLI can both run it without either caring whether the
    other already did.

    ``days`` of zero or less purges everything, which is a reasonable reading of
    "keep no history" and a trap for a mistyped argument, so it is rejected.
    """
    keep_days = settings.LOG_RETENTION_DAYS if days is None else days
    if keep_days <= 0:
        raise ValueError("retention must be at least one day")

    # `created_at` is SQLite's CURRENT_TIMESTAMP: UTC, second resolution, stored
    # as a plain string. The same naive-UTC convention as the session cleanup.
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=keep_days)

    removed = {}
    for name, model in (("login_attempts", LoginAttempt), ("audit_log", AuditEntry)):
        result = db.execute(delete(model).where(model.created_at < cutoff))
        removed[name] = result.rowcount or 0
    db.commit()
    return removed


def seconds_until_next_purge(now: datetime | None = None) -> float:
    """Seconds from ``now`` until the next 07:00 at the bar.

    The purge runs at a fixed wall-clock time at the bar rather than every N
    hours, so a database that grows unevenly is still tidied on a predictable
    schedule. ``now`` is injectable purely so a test can pin it; a time already
    past 07:00 means the next run is tomorrow's.

    Ecuador is UTC-5 with no daylight saving, so the fixed offset from
    :mod:`app.ssr` is exact and no tzdata package is needed.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    local = now.astimezone(timezone(BAR_UTC_OFFSET))
    target = local.replace(hour=PURGE_HOUR_BAR, minute=0, second=0, microsecond=0)
    if target <= local:
        target += timedelta(days=1)
    return (target - local).total_seconds()
