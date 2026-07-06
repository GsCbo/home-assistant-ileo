"""Config flow for the ILEO integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import CONF_START_DATE, DEFAULT_START_DATE, DOMAIN


class IleoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an ILEO config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial user step."""
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_START_DATE, default=DEFAULT_START_DATE): str,
                }
            ),
        )
