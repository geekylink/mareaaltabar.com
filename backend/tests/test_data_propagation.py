"""End-to-end tests: admin edits must be visible through the public read APIs.

This is the regression guard for the original bug: schedule data was hardcoded
in the Svelte frontend, so admin edits never reached visitors.
"""

import pytest


@pytest.fixture()
def edit_as_admin(client, auth_cookies, csrf_token):
    """Return a helper that performs an authenticated admin write."""

    def _edit(method, url, **kwargs):
        return client.request(
            method,
            url,
            headers={"X-CSRF-Token": csrf_token},
            **kwargs,
        )

    return _edit


def test_public_read_endpoints_are_open(client):
    """The frontend reads these with no session, so they must return data."""
    for path in ("/api/events", "/api/hours", "/api/closed-days"):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"
        assert isinstance(resp.json(), list), path


def test_reads_do_not_require_auth_even_when_writes_do(client):
    """Guards the bug where the whole API was behind auth and the site showed nothing."""
    assert client.get("/api/events").status_code == 200
    assert client.put("/api/events/0", json={"title": "x", "note": "", "time": ""}).status_code == 401


def test_event_edit_is_visible_to_visitors(client, edit_as_admin):
    """An admin changing a party title must show up in the public feed."""
    resp = edit_as_admin(
        "PUT",
        "/api/events/5",
        json={"title": "Reggae Night", "note": "Roots and dub all night.", "time": "9 PM - 3 AM"},
    )
    assert resp.status_code == 200

    # Now read it back the way an unauthenticated visitor would.
    public = client.get("/api/events")
    assert public.status_code == 200

    friday = next(e for e in public.json() if e["day"] == 5)
    assert friday["title"] == "Reggae Night"
    assert friday["note"] == "Roots and dub all night."
    assert friday["time"] == "9 PM - 3 AM"


def test_marking_a_day_closed_is_visible_to_visitors(client, edit_as_admin):
    """Setting is_closed must flip the flag the frontend renders."""
    resp = edit_as_admin(
        "PUT",
        "/api/hours/3",
        json={"open_time": "", "close_time": "", "is_closed": True},
    )
    assert resp.status_code == 200

    public = client.get("/api/hours")
    assert public.status_code == 200

    wednesday = next(h for h in public.json() if h["day"] == 3)
    assert wednesday["is_closed"] is True


def test_reopening_a_closed_day_is_visible_to_visitors(client, edit_as_admin):
    """Un-closing a day must clear the flag."""
    edit_as_admin("PUT", "/api/hours/2", json={"open_time": "", "close_time": "", "is_closed": True})

    resp = edit_as_admin(
        "PUT",
        "/api/hours/2",
        json={"open_time": "17:00", "close_time": "03:00", "is_closed": False},
    )
    assert resp.status_code == 200

    public = client.get("/api/hours")
    tuesday = next(h for h in public.json() if h["day"] == 2)
    assert tuesday["is_closed"] is False
    assert tuesday["open_time"] == "17:00"


def test_adding_and_removing_a_closed_day(client, edit_as_admin):
    """Closed-day list is the source for the visitor-facing notice."""
    created = edit_as_admin(
        "POST",
        "/api/closed-days",
        json={"date": "2099-12-25", "reason": "Private event"},
    )
    assert created.status_code == 201
    day_id = created.json()["id"]

    listed = client.get("/api/closed-days")
    assert listed.status_code == 200
    assert any(d["date"] == "2099-12-25" for d in listed.json())

    removed = edit_as_admin("DELETE", f"/api/closed-days/{day_id}")
    assert removed.status_code == 204

    listed = client.get("/api/closed-days")
    assert not any(d["date"] == "2099-12-25" for d in listed.json())


def test_edit_persists_across_requests(client, edit_as_admin):
    """A write must be durable, not just visible in the same response."""
    edit_as_admin("PUT", "/api/events/0", json={"title": "First Write", "note": "", "time": ""})

    # Read twice to be sure it isn't cached or transactional-only.
    for _ in range(2):
        events = client.get("/api/events").json()
        sunday = next(e for e in events if e["day"] == 0)
        assert sunday["title"] == "First Write"


def test_all_seven_days_are_independently_editable(client, edit_as_admin):
    """Editing one day must not bleed into the others."""
    edit_as_admin("PUT", "/api/events/4", json={"title": "Open Mic", "note": "", "time": "8 PM"})

    events = client.get("/api/events").json()
    by_day = {e["day"]: e["title"] for e in events}

    assert by_day[4] == "Open Mic"
    assert by_day[5] == "Live Music"
    assert by_day[0] == "Latin Night"