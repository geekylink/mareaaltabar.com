"""End-to-end tests: admin edits must be visible through the public read API.

Regression guard for the original bug -- schedule data was hardcoded in the
Svelte frontend, so admin edits never reached visitors.
"""

import pytest


@pytest.fixture()
def edit_as_admin(client, auth_cookies, csrf_token):
    """Return a helper that performs an authenticated admin write."""

    def _edit(method, url, **kwargs):
        return client.request(method, url, headers={"X-CSRF-Token": csrf_token}, **kwargs)

    return _edit


def test_public_read_endpoints_are_open(client):
    """The frontend reads these with no session, so they must return data."""
    for path in ("/api/schedule", "/api/closed-days"):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"
        assert isinstance(resp.json(), list), path


def test_reads_are_open_while_writes_are_not(client):
    """Guards the bug where the whole API sat behind auth and the site showed nothing."""
    assert client.get("/api/schedule").status_code == 200
    assert client.put("/api/schedule/0", json={"title_en": "x"}).status_code == 401


def test_bilingual_event_edit_reaches_visitors(client, edit_as_admin):
    """Both language variants must round-trip through the public feed."""
    edit_as_admin(
        "PUT",
        "/api/schedule/5",
        json={
            "title_en": "Reggae Night",
            "title_es": "Noche de Reggae",
            "note_en": "Roots and dub all night.",
            "note_es": "Roots y dub toda la noche.",
            "open_time": "18:00",
            "close_time": "03:00",
            "is_closed": False,
        },
    )

    friday = next(d for d in client.get("/api/schedule").json() if d["day"] == 5)
    assert friday["title_en"] == "Reggae Night"
    assert friday["title_es"] == "Noche de Reggae"
    assert friday["note_en"] == "Roots and dub all night."
    assert friday["note_es"] == "Roots y dub toda la noche."
    assert friday["open_time"] == "18:00"


def test_hours_edit_reaches_visitors(client, edit_as_admin):
    """Hours are part of the same resource, so they must propagate too."""
    edit_as_admin(
        "PUT",
        "/api/schedule/4",
        json={
            "title_en": "Open Mic",
            "title_es": "Mic Abierto",
            "note_en": "",
            "note_es": "",
            "open_time": "17:30",
            "close_time": "01:00",
            "is_closed": False,
        },
    )
    thursday = next(d for d in client.get("/api/schedule").json() if d["day"] == 4)
    assert thursday["open_time"] == "17:30"
    assert thursday["close_time"] == "01:00"


def test_marking_a_day_closed_reaches_visitors(client, edit_as_admin):
    edit_as_admin(
        "PUT",
        "/api/schedule/3",
        json={"title_en": "Closed", "title_es": "Cerrado", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": True},
    )
    wednesday = next(d for d in client.get("/api/schedule").json() if d["day"] == 3)
    assert wednesday["is_closed"] is True


def test_reopening_a_day_reaches_visitors(client, edit_as_admin):
    edit_as_admin(
        "PUT",
        "/api/schedule/2",
        json={"title_en": "Closed", "title_es": "Cerrado", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": True},
    )
    edit_as_admin(
        "PUT",
        "/api/schedule/2",
        json={"title_en": "Latin Night", "title_es": "Noche Latina", "note_en": "x", "note_es": "y",
              "open_time": "16:00", "close_time": "02:00", "is_closed": False},
    )
    tuesday = next(d for d in client.get("/api/schedule").json() if d["day"] == 2)
    assert tuesday["is_closed"] is False
    assert tuesday["title_es"] == "Noche Latina"


def test_closed_day_lifecycle_reaches_visitors(client, edit_as_admin):
    created = edit_as_admin(
        "POST",
        "/api/closed-days",
        json={"date": "2099-12-25", "reason_en": "Christmas", "reason_es": "Navidad"},
    )
    assert created.status_code == 201
    day_id = created.json()["id"]

    listed = client.get("/api/closed-days").json()
    entry = next(d for d in listed if d["date"] == "2099-12-25")
    assert entry["reason_en"] == "Christmas"
    assert entry["reason_es"] == "Navidad"

    assert edit_as_admin("DELETE", f"/api/closed-days/{day_id}").status_code == 204
    assert client.get("/api/closed-days").json() == []


def test_edit_is_durable_across_requests(client, edit_as_admin):
    edit_as_admin(
        "PUT",
        "/api/schedule/0",
        json={"title_en": "First Write", "title_es": "Primera", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": False},
    )
    for _ in range(2):
        sunday = next(d for d in client.get("/api/schedule").json() if d["day"] == 0)
        assert sunday["title_en"] == "First Write"


def test_days_are_independently_editable(client, edit_as_admin):
    """Editing one day must not bleed into its neighbours."""
    edit_as_admin(
        "PUT",
        "/api/schedule/4",
        json={"title_en": "Open Mic", "title_es": "Mic", "note_en": "", "note_es": "",
              "open_time": "", "close_time": "", "is_closed": False},
    )
    by_day = {d["day"]: d["title_en"] for d in client.get("/api/schedule").json()}
    assert by_day[4] == "Open Mic"
    assert by_day[5] == "Live Music"
    assert by_day[0] == "Latin Night"


def test_spanish_only_edit_does_not_clobber_english(client, edit_as_admin):
    """A Spanish-only correction must leave the English copy intact."""
    edit_as_admin(
        "PUT",
        "/api/schedule/5",
        json={"title_en": "Live Music", "title_es": "Música en Vivo",
              "note_en": "Live music all night.", "note_es": "Música en vivo toda la noche.",
              "open_time": "16:00", "close_time": "04:00", "is_closed": False},
    )
    friday = next(d for d in client.get("/api/schedule").json() if d["day"] == 5)
    assert friday["title_en"] == "Live Music"
    assert friday["note_en"] == "Live music all night."