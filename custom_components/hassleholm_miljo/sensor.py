"""Sensor platform for Hässleholm Miljö."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTR_UPCOMING, ATTR_ADDRESS, ATTR_PICKUP_TYPE
from .coordinator import HassleHolmCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: HassleHolmCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        NextPickupSensor(coordinator, entry),
        DaysUntilPickupSensor(coordinator, entry),
        PickupTypeSensor(coordinator, entry),
    ])


class NextPickupSensor(CoordinatorEntity[HassleHolmCoordinator], SensorEntity):
    """Sensor showing the date of the next pickup."""

    _attr_icon = "mdi:trash-can"
    _attr_has_entity_name = True

    def __init__(self, coordinator: HassleHolmCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_next_pickup"
        self._attr_name = "Next Pickup"
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        event = self.coordinator.data.next_event()
        if event:
            return event.date.isoformat()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        event = data.next_event()
        upcoming = data.upcoming(10)

        return {
            ATTR_ADDRESS: data.address,
            ATTR_PICKUP_TYPE: event.label if event else None,
            ATTR_UPCOMING: [
                {
                    "date": e.date.isoformat(),
                    "types": e.types,
                    "days_until": e.days_until(),
                }
                for e in upcoming
            ],
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self.coordinator.data.address or "Hässleholm Miljö",
            "manufacturer": "Hässleholm Miljö AB",
            "model": "Tömningskalender",
        }


class DaysUntilPickupSensor(CoordinatorEntity[HassleHolmCoordinator], SensorEntity):
    """Sensor showing days until the next pickup."""

    _attr_icon = "mdi:calendar-clock"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "days"

    def __init__(self, coordinator: HassleHolmCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_days_until_pickup"
        self._attr_name = "Days Until Pickup"
        self._entry = entry

    @property
    def native_value(self) -> int | None:
        event = self.coordinator.data.next_event()
        if event:
            return event.days_until()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self.coordinator.data.next_event()
        return {
            ATTR_PICKUP_TYPE: event.label if event else None,
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self.coordinator.data.address or "Hässleholm Miljö",
            "manufacturer": "Hässleholm Miljö AB",
            "model": "Tömningskalender",
        }


class PickupTypeSensor(CoordinatorEntity[HassleHolmCoordinator], SensorEntity):
    """Sensor showing what is being picked up next."""

    _attr_icon = "mdi:trash-can-outline"
    _attr_has_entity_name = True

    def __init__(self, coordinator: HassleHolmCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pickup_type"
        self._attr_name = "Pickup Type"
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        event = self.coordinator.data.next_event()
        return event.label if event else None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self.coordinator.data.address or "Hässleholm Miljö",
            "manufacturer": "Hässleholm Miljö AB",
            "model": "Tömningskalender",
        }
