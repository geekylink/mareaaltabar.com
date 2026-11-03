"""Tests for the nightly backup script.

Two risks are worth guarding. The first is that the backup is not actually a
database — a torn copy that opens but is missing rows is worse than a loud
failure, so every file this script writes is checked with
``PRAGMA integrity_check``. The second is retention deleting the wrong thing, so
the tests cover both the pruning window and unrelated files surviving it.
"""

import importlib.util
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "backup.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("marea_backup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backup = _load_script()


def make_database(path: Path, value: str = "Latin Night") -> Path:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
        conn.execute("INSERT INTO events (title) VALUES (?)", (value,))
        conn.commit()
    finally:
        conn.close()
    return path


def rows(path: Path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT id, title FROM events ORDER BY id").fetchall()
    finally:
        conn.close()


def test_backup_writes_a_daily_and_a_monthly_copy(tmp_path):
    source = make_database(tmp_path / "marea_alta.db")

    result = backup.backup_database(source, tmp_path / "backups",
                                    now=datetime(2026, 11, 3, 4, 15))

    assert result["daily"].name == "marea_alta-2026-11-03.db"
    assert result["monthly"].name == "marea_alta-2026-11.db"
    assert result["daily"].is_file()
    assert result["monthly"].is_file()
    # The copy is a real database, not just a file of the right size.
    backup.verify_database(result["daily"])
    backup.verify_database(result["monthly"])


def test_a_backup_restores_the_schedule(tmp_path):
    source = make_database(tmp_path / "marea_alta.db", "Full Moon Party")

    result = backup.backup_database(source, tmp_path / "backups",
                                    now=datetime(2026, 11, 3, 4, 15))

    assert rows(result["daily"]) == [(1, "Full Moon Party")]


def test_a_second_run_on_the_same_day_replaces_the_daily_file(tmp_path):
    source = make_database(tmp_path / "marea_alta.db", "Before")
    backup_dir = tmp_path / "backups"
    noon = datetime(2026, 11, 3, 12, 0)

    first = backup.backup_database(source, backup_dir, now=noon)

    conn = sqlite3.connect(source)
    try:
        conn.execute("UPDATE events SET title = ? WHERE id = 1", ("After",))
        conn.commit()
    finally:
        conn.close()

    second = backup.backup_database(source, backup_dir, now=noon)

    assert first["daily"] == second["daily"]
    assert rows(second["daily"]) == [(1, "After")]
    assert len(list(backup_dir.glob("*-2026-11-03.db"))) == 1


def test_retention_keeps_the_newest_daily_and_monthly_files(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    today = date(2026, 11, 3)

    for offset in range(20):
        day = today - timedelta(days=offset)
        (backup_dir / f"marea_alta-{day.isoformat()}.db").write_bytes(b"x")
    for month_offset in range(15):
        year = today.year
        month = today.month - month_offset
        while month <= 0:
            month += 12
            year -= 1
        (backup_dir / f"marea_alta-{year:04d}-{month:02d}.db").write_bytes(b"x")

    removed = backup.prune_backups(backup_dir, "marea_alta", retain_days=14,
                                   retain_months=12, today=today)

    dailies = sorted(p.name for p in backup_dir.glob("marea_alta-20??-??-??.db"))
    monthlies = sorted(p.name for p in backup_dir.glob("marea_alta-20??-??.db"))

    assert len(dailies) == 14
    assert dailies[0] == "marea_alta-2026-10-21.db"
    assert "marea_alta-2026-11-03.db" in dailies
    assert len(monthlies) == 12
    assert "marea_alta-2026-11.db" in monthlies
    assert len(removed) == 6 + 3


def test_retention_leaves_unrelated_files_alone(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    today = date(2026, 11, 3)
    (backup_dir / "notes.txt").write_text("keep me")
    (backup_dir / "other_app-2020-01-01.db").write_bytes(b"x")
    (backup_dir / "marea_alta-2020-01-01.db").write_bytes(b"x")
    (backup_dir / "marea_alta-2026-11-03.db").write_bytes(b"x")

    backup.prune_backups(backup_dir, "marea_alta", retain_days=1,
                         retain_months=1, today=today)

    assert (backup_dir / "notes.txt").is_file()
    assert (backup_dir / "other_app-2020-01-01.db").is_file()
    assert not (backup_dir / "marea_alta-2020-01-01.db").exists()


def test_verify_rejects_a_file_that_is_not_a_database(tmp_path):
    broken = tmp_path / "broken.db"
    broken.write_bytes(b"this is not sqlite")

    with pytest.raises(backup.BackupError):
        backup.verify_database(broken)


def test_verify_rejects_a_missing_file(tmp_path):
    with pytest.raises(backup.BackupError):
        backup.verify_database(tmp_path / "missing.db")


def test_backup_refuses_a_missing_database(tmp_path):
    with pytest.raises(backup.BackupError):
        backup.backup_database(tmp_path / "missing.db", tmp_path / "backups")


def test_no_monthly_skips_the_monthly_copy(tmp_path):
    source = make_database(tmp_path / "marea_alta.db")

    result = backup.backup_database(source, tmp_path / "backups", monthly=False,
                                    now=datetime(2026, 11, 3, 4, 15))

    assert result["monthly"] is None
    assert not list((tmp_path / "backups").glob("marea_alta-2026-11.db"))


def test_cli_backs_up_and_verifies(tmp_path, capsys):
    source = make_database(tmp_path / "marea_alta.db")
    backup_dir = tmp_path / "backups"

    rc = backup.main(["--database", str(source), "--backup-dir", str(backup_dir),
                      "--retain-days", "3", "--no-monthly"])
    assert rc == 0
    assert "daily:" in capsys.readouterr().out

    rc = backup.main(["--database", str(source), "--backup-dir", str(backup_dir),
                      "--verify"])
    assert rc == 0
    assert "ok:" in capsys.readouterr().out


def test_cli_fails_cleanly_when_there_is_nothing_to_verify(tmp_path, capsys):
    source = make_database(tmp_path / "marea_alta.db")

    rc = backup.main(["--database", str(source), "--backup-dir", str(tmp_path / "empty"),
                      "--verify"])

    assert rc == 1
    assert "no backups found" in capsys.readouterr().err
