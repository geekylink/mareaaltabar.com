#!/usr/bin/env python3
"""CLI tool to manage admin users for the Marea Alta backend.

Usage:
    python manage_admin.py create <username> <password>
    python manage_admin.py list
    python manage_admin.py delete <username>
    python manage_admin.py password <username> <new_password>
"""

import argparse
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import select

from app import auth
from app.database import SessionLocal, engine
from app.models import Admin, Base

# Ensure tables exist
Base.metadata.create_all(bind=engine)


def create_admin(username: str, password: str) -> None:
    db = SessionLocal()
    try:
        existing = db.execute(select(Admin).where(Admin.username == username)).scalar_one_or_none()
        if existing:
            print(f"Error: Admin '{username}' already exists.")
            sys.exit(1)

        admin = Admin(username=username, password_hash=auth.hash_password(password))
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
            print(f"Error: Admin '{username}' not found.")
            sys.exit(1)

        db.delete(admin)
        db.commit()
        print(f"Admin '{username}' deleted.")
    finally:
        db.close()


def reset_password(username: str, new_password: str) -> None:
    db = SessionLocal()
    try:
        result = db.execute(select(Admin).where(Admin.username == username))
        admin = result.scalar_one_or_none()
        if admin is None:
            print(f"Error: Admin '{username}' not found.")
            sys.exit(1)

        admin.password_hash = auth.hash_password(new_password)
        db.commit()
        print(f"Password for '{username}' updated.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Manage Marea Alta admin users")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="Create a new admin")
    create_parser.add_argument("username")
    create_parser.add_argument("password")

    # list
    subparsers.add_parser("list", help="List all admins")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete an admin")
    delete_parser.add_argument("username")

    # password
    password_parser = subparsers.add_parser("password", help="Reset admin password")
    password_parser.add_argument("username")
    password_parser.add_argument("new_password")

    args = parser.parse_args()

    if args.command == "create":
        create_admin(args.username, args.password)
    elif args.command == "list":
        list_admins()
    elif args.command == "delete":
        delete_admin(args.username)
    elif args.command == "password":
        reset_password(args.username, args.new_password)


if __name__ == "__main__":
    main()
