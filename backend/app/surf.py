"""The surf report, fetched once on the server and cached (ticket #34).

The browser used to call two Open-Meteo APIs directly on every visit: a DNS
lookup, two TLS handshakes and two round trips from a phone on the Ecuadorian
coast before the widget could paint. The app now exposes one same-origin read
(``GET /api/surf``) and this module does the upstream work, so a busy afternoon
at the bar is one upstream request every fifteen minutes rather than one per
visitor.

The report is deliberately shaped for the widget rather than forwarding the
Open-Meteo payload. That keeps the response small, keeps the tide arithmetic
testable in Python, and means a change to the upstream JSON does not break the
frontend. If the upstream fails, the last good report is served instead of an
error: a fifteen-minute-old wave height is more useful to a surfer than a blank
card.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)

LATITUDE = -1.8268
LONGITUDE = -80.7517
TIMEZONE_NAME = "America/Guayaquil"
TIMEZONE = ZoneInfo(TIMEZONE_NAME)

CACHE_TTL_SECONDS = 15 * 60
UPSTREAM_TIMEOUT_SECONDS = 6.0

MARINE_URL = (
    "https://marine-api.open-meteo.com/v1/marine"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    "&hourly=wave_height,wave_period,wave_direction,sea_level_height_msl"
    f"&timezone={TIMEZONE_NAME}&forecast_days=3"
)
FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    "&daily=sunrise,sunset"
    "&current=temperature_2m,wind_speed_10m,wind_direction_10m"
    f"&timezone={TIMEZONE_NAME}&forecast_days=1"
)


class SurfUnavailable(RuntimeError):
    """The upstream report could not be read or understood."""


# The cache is a single last-good report. The app runs one worker, so a process
# dict is the whole cache; the short TTL is what keeps it fresh. The lock is
# created per running loop so the test client (which starts a new loop per
# request) cannot inherit a lock bound to a closed loop.
_report: dict[str, Any] | None = None
_report_at = 0.0
_locks: dict[Any, asyncio.Lock] = {}


def _lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    return _locks.setdefault(loop, asyncio.Lock())


def reset_cache() -> None:
    """Drop the cached report. Used by the tests and by a manual refresh."""
    global _report, _report_at
    _report = None
    _report_at = 0.0
    _locks.clear()


def bar_now() -> datetime:
    """The current time at the bar, with a timezone attached."""
    return datetime.now(TIMEZONE)


def _number(value: Any, *, field: str) -> float:
    if value is None or isinstance(value, bool):
        raise SurfUnavailable(f"missing {field}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SurfUnavailable(f"invalid {field}") from exc


def _optional_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _series(payload: dict[str, Any], key: str) -> list[Any]:
    block = payload.get("hourly")
    if not isinstance(block, dict):
        raise SurfUnavailable("missing hourly block")
    values = block.get(key)
    if not isinstance(values, list) or not values:
        raise SurfUnavailable(f"missing hourly {key}")
    return values


def _hhmm(value: Any) -> str:
    """Pull "18:20" out of an ISO timestamp, or return an empty string."""
    if not isinstance(value, str) or len(value) < 16:
        return ""
    return value[11:16]


def _tide_turns(times: list[str], levels: list[float], now: datetime) -> list[dict[str, Any]]:
    """Every high and low tide today, with minutes refined between hourly samples.

    Open-Meteo gives sea level once an hour. A parabola through the sample and
    the two beside it gives a better turning time than the sample itself, which
    is the difference between "high tide at 09:00" and "high tide around 08:37".
    """
    today = now.strftime("%Y-%m-%d")
    now_minutes = now.hour * 60 + now.minute
    start = next((index for index, value in enumerate(times) if value.startswith(today)), 0)

    turns: list[dict[str, Any]] = []
    for index in range(max(start, 1), len(levels) - 1):
        if not times[index].startswith(today):
            break
        left, middle, right = levels[index - 1], levels[index], levels[index + 1]
        high = middle > left and middle >= right
        low = middle < left and middle <= right
        if not high and not low:
            continue

        denominator = left - 2 * middle + right
        offset = 0.5 * (left - right) / denominator if denominator else 0.0
        minutes = round((index - start + (offset if abs(offset) < 1 else 0)) * 60)
        turns.append(
            {
                "type": "High" if high else "Low",
                "time": f"{minutes // 60:02d}:{minutes % 60:02d}",
                "past": minutes < now_minutes,
            }
        )
    return turns


def parse_report(
    marine: dict[str, Any],
    forecast: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Turn the two Open-Meteo payloads into the small shape the widget renders."""
    now = now or bar_now()
    times = _series(marine, "time")
    moments = [str(value) for value in times]
    heights = [_number(value, field="wave_height") for value in _series(marine, "wave_height")]
    periods = [_number(value, field="wave_period") for value in _series(marine, "wave_period")]
    directions = [_number(value, field="wave_direction") for value in _series(marine, "wave_direction")]
    levels = [_number(value, field="sea_level_height_msl") for value in _series(marine, "sea_level_height_msl")]

    if not (len(moments) == len(heights) == len(periods) == len(directions) == len(levels)):
        raise SurfUnavailable("hourly series have different lengths")

    current = now.strftime("%Y-%m-%dT%H:00")
    index = moments.index(current) if current in moments else 0
    if index >= len(levels) - 1:
        raise SurfUnavailable("no sea level after the current hour")

    window = levels[index : index + 48]
    low, high = min(window), max(window)
    tide = (levels[index] - low) / (high - low or 1)

    daily = forecast.get("daily")
    if not isinstance(daily, dict):
        daily = {}
    current_weather = forecast.get("current")
    if not isinstance(current_weather, dict):
        current_weather = {}

    sunrise = daily.get("sunrise")
    sunset = daily.get("sunset")

    return {
        "wave": round(heights[index], 2),
        "period": round(periods[index], 1),
        "direction": round(directions[index]),
        "tide": round(tide, 4),
        "rising": levels[index + 1] > levels[index],
        "turns": _tide_turns(moments, levels, now),
        "sunrise": _hhmm(sunrise[0] if isinstance(sunrise, list) and sunrise else ""),
        "sunset": _hhmm(sunset[0] if isinstance(sunset, list) and sunset else ""),
        "wind": round(_optional_number(current_weather.get("wind_speed_10m")), 1),
        "wind_direction": round(_optional_number(current_weather.get("wind_direction_10m"))),
        "temperature": round(_optional_number(current_weather.get("temperature_2m")), 1),
        "observed_at": now.isoformat(),
    }


async def _get_json(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    try:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SurfUnavailable("upstream request failed") from exc
    if not isinstance(payload, dict):
        raise SurfUnavailable("upstream returned a non-object payload")
    return payload


async def build_report(now: datetime | None = None) -> dict[str, Any]:
    """Fetch both upstream APIs concurrently and shape the result."""
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as client:
            marine, forecast = await asyncio.gather(
                _get_json(client, MARINE_URL),
                _get_json(client, FORECAST_URL),
            )
        return parse_report(marine, forecast, now)
    except SurfUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - report, do not crash the request
        raise SurfUnavailable("could not build the surf report") from exc


async def get_report() -> tuple[dict[str, Any], bool]:
    """Return ``(report, cached)``, refreshing at most once per TTL.

    ``cached`` is true when the report came from the cache, including the
    stale-on-error case, so the route can say so in a header.
    """
    global _report, _report_at

    if _report is not None and time.monotonic() - _report_at < CACHE_TTL_SECONDS:
        return _report, True

    async with _lock():
        # Another request may have refreshed while this one waited for the lock.
        if _report is not None and time.monotonic() - _report_at < CACHE_TTL_SECONDS:
            return _report, True

        try:
            report = await build_report()
        except SurfUnavailable:
            if _report is not None:
                logger.warning("Surf upstream failed; serving the last good report")
                return _report, True
            raise

        _report = report
        _report_at = time.monotonic()
        return report, False
