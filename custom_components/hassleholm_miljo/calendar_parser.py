"""Parser for Hässleholm Miljö tömningskalender."""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from dataclasses import dataclass, field

import aiohttp
from bs4 import BeautifulSoup

from .const import BASE_URL, SWEDISH_MONTHS

_LOGGER = logging.getLogger(__name__)


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


def _parse_html(html: str) -> CalendarData:
    """Parse the HTML page and extract pickup events."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract address
    address = ""
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        # Address headers are in all caps like "EKSTIGEN 11, VITTSJÖ"
        if text and text == text.upper() and len(text) > 5 and not any(
            m in text for m in ["VI ANVÄNDER", "FELANMÄLAN", "HITTA"]
        ):
            address = text.title()
            break

    events: list[PickupEvent] = []
    current_year = datetime.now().year
    current_month = None

    for h3 in soup.find_all("h3"):
        month_text = h3.get_text(strip=True)
        # Match "Maj 2026" style
        match = re.match(r"(\w+)\s+(\d{4})", month_text)
        if match:
            month_name, year_str = match.group(1), match.group(2)
            if month_name in SWEDISH_MONTHS:
                current_month = SWEDISH_MONTHS[month_name]
                current_year = int(year_str)
                _LOGGER.debug("Found month section: %s %s", month_name, year_str)
            else:
                _LOGGER.debug("Unrecognized month name: %r", month_name)

        # Now look at the calendar table following this h3
        # Find the next table sibling
        table = h3.find_next("table")
        if not table or current_month is None:
            continue

        _parse_table(table, current_year, current_month, events)

    # Deduplicate and sort
    events.sort(key=lambda e: e.date)

    _LOGGER.debug("Parsed address: %r, found %d events", address, len(events))
    for e in events[:5]:
        _LOGGER.debug("  Event: %s — %s", e.date, e.types)

    return CalendarData(address=address, events=events)


def _parse_table(table, year: int, month: int, events: list[PickupEvent]) -> None:
    """Parse a calendar table and add pickup events to the list."""
    cells = table.find_all("td")

    for cell in cells:
        # Day number is usually a direct text node or in a <p>/<span>
        day_num = None
        pickup_types = []

        # Get all text nodes in the cell
        texts = [t.strip() for t in cell.stripped_strings]

        for text in texts:
            if re.match(r"^\d{1,2}$", text):
                try:
                    num = int(text)
                    if 1 <= num <= 31:
                        day_num = num
                except ValueError:
                    pass
            elif any(kw in text for kw in ["Kärl", "Budad", "hämtning", "Avvikelse"]):
                pickup_types.append(text)

        if day_num and pickup_types:
            try:
                event_date = date(year, month, day_num)
                # Check if we already have an event for this date
                existing = next((e for e in events if e.date == event_date), None)
                if existing:
                    for pt in pickup_types:
                        if pt not in existing.types:
                            existing.types.append(pt)
                else:
                    events.append(PickupEvent(date=event_date, types=pickup_types))
            except ValueError:
                _LOGGER.debug("Invalid date: %d-%d-%d", year, month, day_num)
