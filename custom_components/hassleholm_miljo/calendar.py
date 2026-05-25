"""Calendar platform for Hässleholm Miljö."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HassleHolmCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up calendar from a config entry."""
    coordinator: HassleHolmCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HassleHolmCalendar(coordinator, entry)])


class HassleHolmCalendar(CoordinatorEntity[HassleHolmCoordinator], CalendarEntity):
    """Calendar entity showing all pickup events."""

    _attr_has_entity_name = True
    _attr_name = "Tömningskalender"
    _attr_icon = "mdi:recycle"

    def __init__(self, coordinator: HassleHolmCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._entry = entry

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        next_ev = self.coordinator.data.next_event()
        if not next_ev:
            return None
        return CalendarEvent(
            start=next_ev.date,
            end=next_ev.date + timedelta(days=1),
            summary=next_ev.label,
            description=f"Sophämtning: {next_ev.label}",
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return all events in the given date range."""
        start = start_date.date() if isinstance(start_date, datetime) else start_date
        end = end_date.date() if isinstance(end_date, datetime) else end_date

        events = []
        for ev in self.coordinator.data.events:
            if start <= ev.date <= end:
                events.append(
                    CalendarEvent(
                        start=ev.date,
                        end=ev.date + timedelta(days=1),
                        summary=ev.label,
                        description=f"Sophämtning: {ev.label}",
                    )
                )
        return events

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self.coordinator.data.address or "Hässleholm Miljö",
            "manufacturer": "Hässleholm Miljö AB",
            "model": "Tömningskalender",
        }
