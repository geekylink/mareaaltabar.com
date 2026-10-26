"""Tests for the manage_admin CLI's password handling.

The script has one sharp edge worth guarding: a password typed at the prompt
must never be echoed, and the `--password` shortcut must never become the only
way the command works. The old positional form is gone on purpose, so a
password cannot slip into shell history out of habit.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import manage_admin
from app import auth
from app.models import Admin, Base


@pytest.fixture()
def cli_db(monkeypatch):
    """Point the CLI at a throwaway in-memory database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(manage_admin, "engine", engine)
    monkeypatch.setattr(manage_admin, "SessionLocal", session_factory)

    try:
        yield session_factory
    finally:
        Base.metadata.drop_all(bind=engine)


def run_cli(monkeypatch, *argv):
    monkeypatch.setattr(manage_admin.sys, "argv", ["manage_admin.py", *argv])
    manage_admin.main()


def expect_exit(code, monkeypatch, *argv):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, *argv)
    assert exc.value.code == code


def fake_prompts(monkeypatch, answers):
    """Answer the hidden prompts in order and record which ones were shown."""
    remaining = iter(answers)
    shown = []

    def fake_getpass(prompt="Password: "):
        shown.append(prompt)
        return next(remaining)

    monkeypatch.setattr(manage_admin.getpass, "getpass", fake_getpass)
    monkeypatch.setattr(manage_admin.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    return shown


def forbid_prompts(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("the password prompt should not have run")

    monkeypatch.setattr(manage_admin.getpass, "getpass", unexpected)


def admins(session_factory):
    with session_factory() as db:
        return list(db.execute(select(Admin).order_by(Admin.id)).scalars())


def add_admin(session_factory, username, password):
    with session_factory() as db:
        db.add(Admin(username=username, password_hash=auth.hash_password(password)))
        db.commit()


def test_create_prompts_twice_and_hashes_the_answer(cli_db, monkeypatch):
    shown = fake_prompts(monkeypatch, ["s3cret", "s3cret"])

    run_cli(monkeypatch, "create", "alice")

    assert shown == ["Password: ", "Confirm password: "]
    [admin] = admins(cli_db)
    assert admin.username == "alice"
    assert auth.verify_password("s3cret", admin.password_hash)


def test_create_with_password_flag_skips_the_prompt(cli_db, monkeypatch):
    forbid_prompts(monkeypatch)

    run_cli(monkeypatch, "create", "alice", "--password=s3cret")

    [admin] = admins(cli_db)
    assert auth.verify_password("s3cret", admin.password_hash)


def test_create_rejects_mismatched_confirmation(cli_db, monkeypatch, capsys):
    fake_prompts(monkeypatch, ["s3cret", "s3crat"])

    expect_exit(1, monkeypatch, "create", "alice")

    assert "do not match" in capsys.readouterr().err
    assert admins(cli_db) == []


def test_create_rejects_empty_prompted_password(cli_db, monkeypatch, capsys):
    fake_prompts(monkeypatch, [""])

    expect_exit(1, monkeypatch, "create", "alice")

    assert "cannot be empty" in capsys.readouterr().err
    assert admins(cli_db) == []


def test_create_rejects_empty_password_flag(cli_db, monkeypatch, capsys):
    forbid_prompts(monkeypatch)

    expect_exit(1, monkeypatch, "create", "alice", "--password=")

    assert "cannot be empty" in capsys.readouterr().err
    assert admins(cli_db) == []


def test_no_terminal_refuses_instead_of_reading_stdin(cli_db, monkeypatch, capsys):
    forbid_prompts(monkeypatch)
    monkeypatch.setattr(manage_admin.sys, "stdin", SimpleNamespace(isatty=lambda: False))

    expect_exit(1, monkeypatch, "create", "alice")

    assert "no terminal available" in capsys.readouterr().err
    assert admins(cli_db) == []


def test_existing_username_fails_before_prompting(cli_db, monkeypatch, capsys):
    add_admin(cli_db, "alice", "oldpass")
    forbid_prompts(monkeypatch)

    expect_exit(1, monkeypatch, "create", "alice")

    assert "already exists" in capsys.readouterr().err


def test_positional_password_is_no_longer_accepted(cli_db, monkeypatch, capsys):
    forbid_prompts(monkeypatch)

    expect_exit(2, monkeypatch, "create", "alice", "s3cret")

    assert "unrecognized arguments" in capsys.readouterr().err
    assert admins(cli_db) == []


def test_password_reset_prompts_and_updates_the_hash(cli_db, monkeypatch):
    add_admin(cli_db, "alice", "oldpass")
    shown = fake_prompts(monkeypatch, ["newpass", "newpass"])

    run_cli(monkeypatch, "password", "alice")

    assert shown == ["Password: ", "Confirm password: "]
    [admin] = admins(cli_db)
    assert auth.verify_password("newpass", admin.password_hash)
    assert not auth.verify_password("oldpass", admin.password_hash)


def test_password_reset_with_password_flag(cli_db, monkeypatch):
    add_admin(cli_db, "alice", "oldpass")
    forbid_prompts(monkeypatch)

    run_cli(monkeypatch, "password", "alice", "--password=newpass")

    [admin] = admins(cli_db)
    assert auth.verify_password("newpass", admin.password_hash)


def test_password_reset_on_missing_admin_does_not_prompt(cli_db, monkeypatch, capsys):
    forbid_prompts(monkeypatch)

    expect_exit(1, monkeypatch, "password", "nobody")

    assert "not found" in capsys.readouterr().err


def test_purge_logs_reports_a_bad_window_on_stderr(cli_db, monkeypatch, capsys):
    expect_exit(1, monkeypatch, "purge-logs", "--days=0")

    captured = capsys.readouterr()
    assert "at least one day" in captured.err
    assert captured.out == ""


def test_delete_reports_a_missing_admin_on_stderr(cli_db, monkeypatch, capsys):
    expect_exit(1, monkeypatch, "delete", "nobody")

    captured = capsys.readouterr()
    assert "not found" in captured.err
    assert captured.out == ""


def test_delete_removes_the_admin(cli_db, monkeypatch):
    add_admin(cli_db, "alice", "s3cret")

    run_cli(monkeypatch, "delete", "alice")

    assert admins(cli_db) == []
