#!/usr/bin/env python3
"""Nightly SQLite backups for Marea Alta.

The site's schedule, hours, closures and menu live in one SQLite file, and that
file is gitignored — the disk is the only copy. This script makes the copies and
proves they are readable.

It uses :meth:`sqlite3.Connection.backup` rather than ``cp`` (or the ``sqlite3``
CLI, which is not installed everywhere) because SQLite's backup API copies a
consistent snapshot even while uvicorn is writing. ``cp`` can capture a torn
write, and a torn backup is worse than no backup: it looks like one.

Files are named after the source database::

    marea_alta-2026-11-03.db   daily
    marea_alta-2026-11.db      monthly (latest run in that month)

Both are pruned by date, and only files matching those patterns are touched, so
an unrelated file dropped in the backup directory is left alone.

Usage::

    scripts/backup.py                          # back up the configured database
    scripts/backup.py --database /path/app.db  # explicit source
    scripts/backup.py --verify                 # check every backup in the dir
    scripts/backup.py --verify FILE            # check one backup
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

DEFAULT_RETAIN_DAYS = 14
DEFAULT_RETAIN_MONTHS = 12
DEFAULT_BACKUP_DIR = Path("/var/backups/marea-alta")


class BackupError(RuntimeError):
    """A backup could not be created or failed its integrity check."""


# --- Naming ---------------------------------------------------------------

def _daily_name(stem: str, day: date) -> str:
    return f"{stem}-{day.isoformat()}.db"


def _monthly_name(stem: str, day: date) -> str:
    return f"{stem}-{day.year:04d}-{day.month:02d}.db"


def _daily_pattern(stem: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(stem)}-(\d{{4}})-(\d{{2}})-(\d{{2}})\.db$")


def _monthly_pattern(stem: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(stem)}-(\d{{4}})-(\d{{2}})\.db$")


# --- Verification ----------------------------------------------------------

def verify_database(path: str | os.PathLike[str]) -> None:
    """Raise :class:`BackupError` unless ``path`` is a readable SQLite database.

    ``PRAGMA integrity_check`` reads the whole file, so this catches truncation
    and corruption rather than merely a missing file.
    """
    path = Path(path)
    if not path.is_file():
        raise BackupError(f"backup does not exist: {path}")
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise BackupError(f"{path} is not a readable SQLite database: {exc}") from exc

    if not result or result[0] != "ok":
        detail = result[0] if result else "no result"
        raise BackupError(f"{path} failed integrity_check: {detail}")


# --- Writing ---------------------------------------------------------------

def _backup_to(source: Path, destination: Path) -> None:
    """Copy ``source`` into ``destination`` through SQLite's backup API."""
    try:
        src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise BackupError(f"cannot open {source}: {exc}") from exc

    try:
        dst = sqlite3.connect(destination)
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    except sqlite3.Error as exc:
        raise BackupError(f"cannot back up {source}: {exc}") from exc
    finally:
        src.close()


def _atomic_write(target: Path, writer) -> None:
    """Run ``writer(tmp_path)`` then atomically replace ``target``.

    The temporary file lives in the destination directory so ``os.replace`` stays
    on one filesystem and the operation is atomic.
    """
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.unlink()  # sqlite3 wants to create the file itself
        writer(tmp)
        verify_database(tmp)
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def backup_database(
    source: str | os.PathLike[str],
    backup_dir: str | os.PathLike[str] = DEFAULT_BACKUP_DIR,
    *,
    retain_days: int = DEFAULT_RETAIN_DAYS,
    retain_months: int = DEFAULT_RETAIN_MONTHS,
    monthly: bool = True,
    now: datetime | None = None,
) -> dict[str, Path | None]:
    """Back up ``source`` into ``backup_dir`` and prune old copies.

    Returns ``{"daily": Path, "monthly": Path | None}``. ``now`` is injectable so
    tests can pin the date.
    """
    source = Path(source)
    backup_dir = Path(backup_dir)
    if not source.is_file():
        raise BackupError(f"database does not exist: {source}")
    if retain_days < 1:
        raise ValueError("retain_days must be at least 1")
    if retain_months < 1:
        raise ValueError("retain_months must be at least 1")

    backup_dir.mkdir(parents=True, exist_ok=True)
    day = (now or datetime.now()).date()
    stem = source.stem

    daily = backup_dir / _daily_name(stem, day)
    _atomic_write(daily, lambda tmp: _backup_to(source, tmp))

    monthly_path: Path | None = None
    if monthly:
        monthly_path = backup_dir / _monthly_name(stem, day)
        _atomic_write(monthly_path, lambda tmp: _backup_to(source, tmp))

    prune_backups(
        backup_dir,
        stem,
        retain_days=retain_days,
        retain_months=retain_months,
        today=day,
        monthly=monthly,
    )
    return {"daily": daily, "monthly": monthly_path}


# --- Retention -------------------------------------------------------------

def _matching_dates(path: Path, pattern: re.Pattern[str]) -> date | None:
    match = pattern.match(path.name)
    if not match:
        return None
    try:
        parts = [int(part) for part in match.groups()]
        # Monthly names carry no day; the first of the month sorts correctly.
        if len(parts) == 2:
            parts.append(1)
        return date(*parts)
    except ValueError:
        return None


def prune_backups(
    backup_dir: str | os.PathLike[str],
    stem: str,
    *,
    retain_days: int = DEFAULT_RETAIN_DAYS,
    retain_months: int = DEFAULT_RETAIN_MONTHS,
    today: date | None = None,
    monthly: bool = True,
) -> list[Path]:
    """Delete backups outside the retention window, newest kept.

    Only files whose names match this script's patterns are considered. Anything
    else in the directory is someone else's and is left alone.
    """
    backup_dir = Path(backup_dir)
    if not backup_dir.is_dir():
        return []

    today = today or date.today()
    removed: list[Path] = []

    dailies: list[tuple[date, Path]] = []
    monthlies: list[tuple[date, Path]] = []
    for path in backup_dir.iterdir():
        if not path.is_file():
            continue
        if (found := _matching_dates(path, _daily_pattern(stem))) is not None:
            dailies.append((found, path))
        elif (found := _matching_dates(path, _monthly_pattern(stem))) is not None:
            monthlies.append((found, path))

    # Newest first; keep the first N, delete the rest. A daily file dated in the
    # future (a clock change) sorts first and is kept rather than deleted.
    for dates_and_paths, keep in ((dailies, retain_days), (monthlies, retain_months)):
        dates_and_paths.sort(key=lambda item: item[0], reverse=True)
        for _, path in dates_and_paths[keep:]:
            path.unlink(missing_ok=True)
            removed.append(path)

    return removed


# --- CLI -------------------------------------------------------------------

def _default_database() -> Path:
    """Mirror the backend's DATABASE_PATH default without importing the app."""
    return Path(__file__).resolve().parent.parent / "backend" / "data" / "marea_alta.db"


def _resolve_backup_dir(value: str | None) -> Path:
    if value:
        return Path(value)
    env = os.environ.get("BACKUP_DIR")
    if env:
        return Path(env)
    return DEFAULT_BACKUP_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Back up the Marea Alta SQLite database and prune old copies.",
    )
    parser.add_argument("--database", default=os.environ.get("DATABASE_PATH"),
                        help="source database (default: DATABASE_PATH or backend/data/marea_alta.db)")
    parser.add_argument("--backup-dir", default=None,
                        help="destination directory (default: BACKUP_DIR or /var/backups/marea-alta)")
    parser.add_argument("--retain-days", type=int, default=DEFAULT_RETAIN_DAYS,
                        help=f"daily backups to keep (default: {DEFAULT_RETAIN_DAYS})")
    parser.add_argument("--retain-months", type=int, default=DEFAULT_RETAIN_MONTHS,
                        help=f"monthly backups to keep (default: {DEFAULT_RETAIN_MONTHS})")
    parser.add_argument("--no-monthly", action="store_true",
                        help="write only the daily backup")
    parser.add_argument("--verify", nargs="?", const="__all__", metavar="FILE",
                        help="check a backup (default: every backup in the backup directory)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.verify is not None:
            backup_dir = _resolve_backup_dir(args.backup_dir)
            if args.verify == "__all__":
                database = Path(args.database) if args.database else _default_database()
                stem = database.stem
                targets = sorted(
                    path for path in backup_dir.iterdir()
                    if _matching_dates(path, _daily_pattern(stem)) is not None
                    or _matching_dates(path, _monthly_pattern(stem)) is not None
                ) if backup_dir.is_dir() else []
                if not targets:
                    print(f"no backups found in {backup_dir}", file=sys.stderr)
                    return 1
            else:
                targets = [Path(args.verify)]
            for path in targets:
                verify_database(path)
                print(f"ok: {path}")
            return 0

        database = Path(args.database) if args.database else _default_database()
        result = backup_database(
            database,
            _resolve_backup_dir(args.backup_dir),
            retain_days=args.retain_days,
            retain_months=args.retain_months,
            monthly=not args.no_monthly,
        )
        print(f"daily:   {result['daily']}")
        if result["monthly"] is not None:
            print(f"monthly: {result['monthly']}")
        return 0
    except (BackupError, OSError, ValueError) as exc:
        print(f"backup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
