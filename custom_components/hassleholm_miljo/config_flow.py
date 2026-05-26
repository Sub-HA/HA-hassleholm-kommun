"""Config flow for Hässleholm Miljö integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_ALIAS, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .calendar_parser import fetch_calendar

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ALIAS, description={"suggested_value": "hmab-ekstigen-11-vittsjoe"}): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=24)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input by fetching the calendar."""
    session = async_get_clientsession(hass)
    calendar = await fetch_calendar(session, data[CONF_ALIAS])
    if not calendar.address:
        raise InvalidAlias
    return {"title": calendar.address}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hässleholm Miljö."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlowHandler:
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Normalize alias: strip URL if pasted
            alias = user_input[CONF_ALIAS]
            if "alias=" in alias:
                alias = alias.split("alias=")[-1]
            user_input[CONF_ALIAS] = alias.strip()

            await self.async_set_unique_id(user_input[CONF_ALIAS])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except InvalidAlias:
                errors["base"] = "invalid_alias"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "url_example": "https://hassleholmmiljo.se/...?alias=hmab-ekstigen-11-vittsjoe"
            },
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Hässleholm Miljö."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        current_alias = self._config_entry.options.get(
            CONF_ALIAS, self._config_entry.data.get(CONF_ALIAS, "")
        )
        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        if user_input is not None:
            alias = user_input[CONF_ALIAS]
            if "alias=" in alias:
                alias = alias.split("alias=")[-1]
            user_input[CONF_ALIAS] = alias.strip()

            try:
                await validate_input(self.hass, user_input)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except InvalidAlias:
                errors["base"] = "invalid_alias"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_ALIAS, default=current_alias): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=24)
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


class InvalidAlias(Exception):
    """Error for invalid address alias."""
