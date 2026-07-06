"""Config flow for the ILEO integration."""

from __future__ import annotations

from datetime import datetime
import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IleoApiClient, IleoAuthError, IleoConnectionError
from .const import CONF_START_DATE, DEFAULT_START_DATE, DOMAIN

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_START_DATE, default=DEFAULT_START_DATE): str,
    }
)


class IleoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an ILEO config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            password = user_input[CONF_PASSWORD]
            start_date = user_input.get(CONF_START_DATE, DEFAULT_START_DATE)

            try:
                datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                errors[CONF_START_DATE] = "invalid_date"
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors,
                )

            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = IleoApiClient(
                session=session,
                username=username,
                password=password,
            )

            try:
                await client.async_validate_credentials()
            except IleoAuthError:
                errors["base"] = "invalid_auth"
            except (IleoConnectionError, aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception while validating ILEO credentials")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_START_DATE: start_date,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
