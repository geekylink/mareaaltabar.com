#!/usr/bin/env python3
"""CLI tool to manage admin users and the admin logs.

Usage:
    python manage_admin.py create <username>
    python manage_admin.py create <username> --password <password>
    python manage_admin.py list
    python manage_admin.py delete <username>
    python manage_admin.py password <username>
    python manage_admin.py password <username> --password <password>
    python manage_admin.py purge-logs [--days 90]

Without --password the password is asked for on the terminal, twice, with the
input hidden. The flag exists for development and testing only: a password on
the command line ends up in shell history and in the process list.
"""

import argparse
import getpass
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import select

from app import audit, auth
from app.config import settings
from app.database import SessionLocal, engine
from app.models import Admin, Base


def fail(message: str) -> None:
    """Print an error to stderr and exit with a failure status."""
    print(message, file=sys.stderr)
    sys.exit(1)


def read_password(provided: str | None) -> str:
    """Return the password, prompting twice with hidden input when not given.

    A bare --password (empty value) is rejected rather than hashed, and the
    prompt is skipped entirely when stdin is not a terminal: reading a silently
    echoed password from a pipe or a `docker-compose exec -T` session is worse
    than failing.
    """
    if provided is not None:
        if not provided:
            fail("Error: password cannot be empty.")
        return provided

    if not sys.stdin.isatty():
        fail(
            "Error: no terminal available for a password prompt. "
            "Use --password for non-interactive use."
        )

    password = getpass.getpass("Password: ")
    if not password:
        fail("Error: password cannot be empty.")

    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        fail("Error: passwords do not match.")

    return password


def create_admin(username: str, password: str | None) -> None:
    db = SessionLocal()
    try:
        existing = db.execute(select(Admin).where(Admin.username == username)).scalar_one_or_none()
        if existing:
            fail(f"Error: Admin '{username}' already exists.")

        password_hash = auth.hash_password(read_password(password))
        admin = Admin(username=username, password_hash=password_hash)
        db.add(admin)
        db.commit()
        print(f"Admin '{username}' created successfully.")
    finally:
        db.close()


def list_admins() -> None:
    db = SessionLocal()
    try:
        result = db.execute(select(Admin).order_by(Admin.id))
        admins = result.scalars().all()
        if not admins:
            print("No admins found.")
            return
        print(f"{'ID':<5} {'Username':<20} {'Created'}")
        print("-" * 50)
        for a in admins:
            print(f"{a.id:<5} {a.username:<20} {a.created_at}")
    finally:
        db.close()


def delete_admin(username: str) -> None:
    db = SessionLocal()
    try:
        result = db.execute(select(Admin).where(Admin.username == username))
        admin = result.scalar_one_or_none()
        if admin is None:
            fail(f"Error: Admin '{username}' not found.")

        db.delete(admin)
        db.commit()
        print(f"Admin '{username}' deleted.")
    finally:
        db.close()


def reset_password(username: str, password: str | None) -> None:
    db = SessionLocal()
    try:
        result = db.execute(select(Admin).where(Admin.username == username))
        admin = result.scalar_one_or_none()
        if admin is None:
            fail(f"Error: Admin '{username}' not found.")

        admin.password_hash = auth.hash_password(read_password(password))
        db.commit()
        print(f"Password for '{username}' updated.")
    finally:
        db.close()


def purge_logs(days: int | None) -> None:
    """Delete login and change-log rows past the retention window.

    The server does this by itself at 07:00 at the bar; this is the manual
    version, for shrinking the database before a backup or when a long-running
    process has been restarted with the daily purge disabled. It is idempotent,
    so running it while the server is up is safe.
    """
    keep_days = settings.LOG_RETENTION_DAYS if days is None else days
    db = SessionLocal()
    try:
        removed = audit.purge_old_logs(db, keep_days)
    except ValueError as exc:
        fail(f"Error: {exc}")
    finally:
        db.close()

    print(f"Removed log entries older than {keep_days} days:")
    for table, count in removed.items():
        print(f"  {table}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Manage Marea Alta admin users and logs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    password_help = (
        "Password to use instead of the hidden prompt (development and testing "
        "only: visible in shell history and the process list)"
    )

    # create
    create_parser = subparsers.add_parser("create", help="Create a new admin")
    create_parser.add_argument("username")
    create_parser.add_argument("--password", metavar="PASSWORD", help=password_help)

    # list
    subparsers.add_parser("list", help="List all admins")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete an admin")
    delete_parser.add_argument("username")

    # password
    password_parser = subparsers.add_parser("password", help="Reset admin password")
    password_parser.add_argument("username")
    password_parser.add_argument("--password", metavar="PASSWORD", help=password_help)

    # purge-logs
    purge_parser = subparsers.add_parser(
        "purge-logs",
        help="Delete log entries older than the retention window",
    )
    purge_parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=f"Days to keep (default: LOG_RETENTION_DAYS, currently {settings.LOG_RETENTION_DAYS})",
    )

    args = parser.parse_args()

    # Create the tables only once a command actually runs, so importing this
    # module (from tests, say) has no side effects on the database file.
    Base.metadata.create_all(bind=engine)

    if args.command == "create":
        create_admin(args.username, args.password)
    elif args.command == "list":
        list_admins()
    elif args.command == "delete":
        delete_admin(args.username)
    elif args.command == "password":
        reset_password(args.username, args.password)
    elif args.command == "purge-logs":
        purge_logs(args.days)


if __name__ == "__main__":
    main()
