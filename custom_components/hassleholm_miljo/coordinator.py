"""DataUpdateCoordinator for Hässleholm Miljö."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .calendar_parser import CalendarData, fetch_calendar
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class HassleHolmCoordinator(DataUpdateCoordinator[CalendarData]):
    """Coordinator to fetch calendar data on a schedule."""

    def __init__(self, hass: HomeAssistant, alias: str, scan_interval_hours: int) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=scan_interval_hours),
        )
        self.alias = alias
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> CalendarData:
        """Fetch data from the website."""
        _LOGGER.debug("Starting data update for alias %r", self.alias)
        try:
            data = await fetch_calendar(self._session, self.alias)
            _LOGGER.debug(
                "Update successful: address=%r, events=%d, next=%s",
                data.address,
                len(data.events),
                data.next_event(),
            )
            return data
        except Exception as err:
            _LOGGER.error("Error fetching calendar for alias %r: %s", self.alias, err)
            raise UpdateFailed(f"Error fetching calendar: {err}") from err
