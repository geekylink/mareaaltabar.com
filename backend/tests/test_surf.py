"""Tests for the server-side surf report and its cache (ticket #34).

The browser used to call Open-Meteo twice per visit. These tests pin the new
contract: one same-origin read, a small shaped payload, a fifteen-minute cache
and a stale-on-error fallback. Upstream is always a fake here; the suite must
not depend on the real weather.
"""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app import surf

TZ = ZoneInfo("America/Guayaquil")
NOW = datetime(2026, 1, 6, 8, 30, tzinfo=TZ)

# A day of hourly sea levels with highs at 05:00 and 17:00 and lows at 11:00 and
# 23:00, repeated for the second day so the 48-hour window has both.
LEVELS = [
    0.4, 0.7, 1.1, 1.5, 1.8, 2.0, 1.8, 1.5, 1.1, 0.7, 0.4, 0.2,
    0.3, 0.6, 1.0, 1.4, 1.7, 1.9, 1.7, 1.4, 1.0, 0.6, 0.3, 0.1,
    0.5, 0.8, 1.2, 1.6, 1.9, 2.1, 1.9, 1.6, 1.2, 0.8, 0.5, 0.3,
    0.4, 0.7, 1.1, 1.5, 1.8, 2.0, 1.8, 1.5, 1.1, 0.7, 0.4, 0.2,
]


def times_for(day: str, hours: int = 48) -> list[str]:
    start = datetime.fromisoformat(day + "T00:00")
    return [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]


MARINE = {
    "hourly": {
        "time": times_for("2026-01-06"),
        "wave_height": [round(0.5 + i * 0.01, 2) for i in range(48)],
        "wave_period": [round(10 + i * 0.1, 1) for i in range(48)],
        "wave_direction": [180 + i for i in range(48)],
        "sea_level_height_msl": LEVELS,
    }
}

FORECAST = {
    "daily": {
        "sunrise": ["2026-01-06T06:21"],
        "sunset": ["2026-01-06T18:40"],
    },
    "current": {
        "temperature_2m": 26.3,
        "wind_speed_10m": 9.4,
        "wind_direction_10m": 200,
    },
}


@pytest.fixture(autouse=True)
def _clean_cache(monkeypatch):
    surf.reset_cache()
    monkeypatch.setattr(surf, "bar_now", lambda: NOW)
    yield
    surf.reset_cache()


def test_parse_report_shapes_the_widget_payload():
    report = surf.parse_report(MARINE, FORECAST, NOW)

    # 08:00 is index 8: wave 0.58 m, period 10.8 s, direction 188°.
    assert report["wave"] == 0.58
    assert report["period"] == 10.8
    assert report["direction"] == 188
    assert report["sunrise"] == "06:21"
    assert report["sunset"] == "18:40"
    assert report["wind"] == 9.4
    assert report["wind_direction"] == 200
    assert report["temperature"] == 26.3
    assert report["rising"] is False
    assert 0 <= report["tide"] <= 1
    assert [turn["type"] for turn in report["turns"]] == ["High", "Low", "High", "Low"]
    assert all(len(turn["time"]) == 5 for turn in report["turns"])
    assert report["observed_at"].startswith("2026-01-06T08:30")


def test_parse_report_marks_past_tides_and_today_only():
    report = surf.parse_report(MARINE, FORECAST, NOW)

    # 08:30 is after the 05:00 high but before the 11:00 low.
    assert [turn["past"] for turn in report["turns"]] == [True, False, False, False]


def test_parse_report_rejects_a_missing_series():
    broken = json.loads(json.dumps(MARINE))
    del broken["hourly"]["wave_height"]

    with pytest.raises(surf.SurfUnavailable):
        surf.parse_report(broken, FORECAST, NOW)


def test_report_is_small_enough_for_the_hourly_refresh():
    report = surf.parse_report(MARINE, FORECAST, NOW)

    assert len(json.dumps(report).encode()) < 1024


def test_endpoint_caches_the_first_report(client, monkeypatch):
    calls = []

    async def fake_get_json(_client, url):
        calls.append(url)
        return MARINE if "marine-api" in url else FORECAST

    monkeypatch.setattr(surf, "_get_json", fake_get_json)

    first = client.get("/api/surf")
    assert first.status_code == 200
    assert first.json()["wave"] == 0.58
    assert first.headers["cache-control"] == "public, max-age=300"
    assert "x-surf-cache" not in first.headers
    assert len(calls) == 2

    second = client.get("/api/surf")
    assert second.status_code == 200
    assert second.json() == first.json()
    assert second.headers["x-surf-cache"] == "hit"
    assert len(calls) == 2, "the second request must not touch upstream"


def test_endpoint_returns_502_when_upstream_is_down(client, monkeypatch):
    async def boom(_client, _url):
        raise surf.SurfUnavailable("down")

    monkeypatch.setattr(surf, "_get_json", boom)

    response = client.get("/api/surf")

    assert response.status_code == 502
    assert response.json()["detail"] == "Surf report is temporarily unavailable"


def test_a_stale_report_is_better_than_a_blank_widget(client, monkeypatch):
    async def good(_client, url):
        return MARINE if "marine-api" in url else FORECAST

    monkeypatch.setattr(surf, "_get_json", good)
    assert client.get("/api/surf").status_code == 200

    async def down(_client, _url):
        raise surf.SurfUnavailable("down")

    monkeypatch.setattr(surf, "CACHE_TTL_SECONDS", 0)
    monkeypatch.setattr(surf, "_get_json", down)

    stale = client.get("/api/surf")
    assert stale.status_code == 200
    assert stale.headers["x-surf-cache"] == "hit"
    assert stale.json()["wave"] == 0.58


def test_the_report_never_exposes_the_upstream_urls(client, monkeypatch):
    async def good(_client, url):
        return MARINE if "marine-api" in url else FORECAST

    monkeypatch.setattr(surf, "_get_json", good)

    body = client.get("/api/surf").text

    assert "open-meteo" not in body
    assert "latitude" not in body
