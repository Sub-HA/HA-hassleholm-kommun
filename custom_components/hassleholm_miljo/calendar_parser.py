"""Parser for Hässleholm Miljö tömningskalender."""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from dataclasses import dataclass, field

import aiohttp

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

# Matches: AppRegistry.registerInitialState('node-id', { ... });
_INITIAL_STATE_RE = re.compile(
    r"AppRegistry\.registerInitialState\('[^']+',(\{)",
)


@dataclass
class PickupEvent:
    """Represents a single pickup event."""
    date: date
    types: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return ", ".join(self.types) if self.types else "Hämtning"

    def days_until(self) -> int:
        return (self.date - date.today()).days


@dataclass
class CalendarData:
    """Holds all parsed calendar data."""
    address: str
    events: list[PickupEvent] = field(default_factory=list)

    def upcoming(self, n: int = 5) -> list[PickupEvent]:
        today = date.today()
        return [e for e in self.events if e.date >= today][:n]

    def next_event(self) -> PickupEvent | None:
        upcoming = self.upcoming(1)
        return upcoming[0] if upcoming else None


async def fetch_calendar(session: aiohttp.ClientSession, alias: str) -> CalendarData:
    """Fetch and parse the calendar for the given alias."""
    url = f"{BASE_URL}?alias={alias}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant/1.0)",
        "Accept-Language": "sv-SE,sv;q=0.9",
    }

    _LOGGER.debug("Fetching calendar from %s", url)
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        _LOGGER.debug("Response status: %s, content-type: %s", resp.status, resp.content_type)
        resp.raise_for_status()
        html = await resp.text()
    _LOGGER.debug("Received %d bytes of HTML", len(html))

    return _parse_html(html)


def _extract_json_objects(html: str) -> list[dict]:
    """Extract all registerInitialState JSON payloads from the page."""
    decoder = json.JSONDecoder()
    results = []
    for m in _INITIAL_STATE_RE.finditer(html):
        # m.start(1) is the position of the opening '{' of the JSON object
        try:
            obj, _ = decoder.raw_decode(html, m.start(1))
            results.append(obj)
        except json.JSONDecodeError as err:
            _LOGGER.debug("Failed to parse registerInitialState JSON: %s", err)
    return results


def _parse_html(html: str) -> CalendarData:
    """Extract pickup events from the embedded JSON state in the page."""
    blobs = _extract_json_objects(html)
    _LOGGER.debug("Found %d registerInitialState blobs", len(blobs))

    calendar_blob = None
    services_blob = None

    for blob in blobs:
        if "calendarMonth" in blob:
            calendar_blob = blob["calendarMonth"]
        elif (
            "services" in blob
            and isinstance(blob["services"], dict)
            and "services" in blob["services"]
        ):
            services_blob = blob["services"]

    # Build address from the services blob
    address = ""
    if services_blob:
        addr = services_blob.get("address", "").title()
        city = services_blob.get("city", "").title()
        if addr and city:
            address = f"{addr}, {city}"
        _LOGGER.debug("Services blob: address=%r, services=%s", address, services_blob.get("services"))

    event_map: dict[date, PickupEvent] = {}

    # Current-month calendar: each day with services is a pickup
    if calendar_blob:
        _LOGGER.debug(
            "Calendar blob: month=%s %s, days=%d",
            calendar_blob.get("month"),
            calendar_blob.get("year"),
            len(calendar_blob.get("days", [])),
        )
        for day in calendar_blob.get("days", []):
            if not day.get("currentMonth") or not day.get("services"):
                continue
            try:
                day_date = date.fromisoformat(day["date"])
            except (KeyError, ValueError):
                continue
            types = [s["name"] for s in day["services"] if s.get("name")]
            if types:
                event_map[day_date] = PickupEvent(date=day_date, types=types)
    else:
        _LOGGER.warning("No calendarMonth blob found in page — page structure may have changed")

    # Services next-dates: fills in upcoming pickups beyond the current month view
    if services_blob:
        for svc in services_blob.get("services", []):
            next_date_str = svc.get("nextDate")
            name = svc.get("description", "")
            if not next_date_str or not name:
                continue
            try:
                svc_date = date.fromisoformat(next_date_str)
            except ValueError:
                continue
            if svc_date in event_map:
                if name not in event_map[svc_date].types:
                    event_map[svc_date].types.append(name)
            else:
                event_map[svc_date] = PickupEvent(date=svc_date, types=[name])
    else:
        _LOGGER.warning("No services blob found in page — page structure may have changed")

    events = sorted(event_map.values(), key=lambda e: e.date)

    _LOGGER.debug("Parsed address: %r, found %d events total", address, len(events))
    for e in events[:5]:
        _LOGGER.debug("  Event: %s — %s", e.date, e.types)

    return CalendarData(address=address, events=events)
