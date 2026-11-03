"""The health endpoint is what a monitor and the container healthcheck call.

It must be public, cheap, uncached, and must fail loudly when the database is
unreachable instead of reporting a healthy site with a blank schedule.
"""

from app.database import get_db
from app.main import app


class BrokenSession:
    """A session whose only operation is to fail, for the 503 path."""

    def execute(self, *args, **kwargs):
        raise RuntimeError("database is unavailable")


def test_healthz_reports_ok_for_a_working_database(client):
    resp = client.get("/healthz")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert resp.headers["cache-control"] == "no-store"


def test_healthz_is_public(client):
    """No session cookie: a monitor cannot log in, and should not have to."""
    assert client.get("/healthz").status_code == 200


def test_healthz_reports_503_when_the_database_fails(client):
    original = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        resp = client.get("/healthz")
    finally:
        if original is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = original

    assert resp.status_code == 503
    assert resp.json() == {"status": "unavailable"}
    assert resp.headers["cache-control"] == "no-store"
