"""Data update coordinator for the ILEO integration."""

from __future__ import annotations

from datetime import datetime
import logging

import aiohttp

import homeassistant.util.dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    IleoApiClient,
    IleoAuthError,
    IleoConnectionError,
    IleoCsvError,
    IleoReading,
)
from .const import CONF_START_DATE, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class IleoDataUpdateCoordinator(DataUpdateCoordinator[list[IleoReading]]):
    """Coordinate ILEO consumption updates."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ILEO data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            always_update=False,
        )
        self.config_entry = entry
        self._client = IleoApiClient(
            session=async_get_clientsession(hass),
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )

    async def _async_update_data(self) -> list[IleoReading]:
        """Fetch readings from ILEO."""
        start_date = datetime.strptime(
            self.config_entry.data[CONF_START_DATE], "%Y-%m-%d"
        ).date()
        end_date = dt_util.now().date()

        try:
            return await self._client.async_fetch_readings(start_date, end_date)
        except IleoAuthError as err:
            raise ConfigEntryAuthFailed from err
        except (
            IleoConnectionError,
            IleoCsvError,
            aiohttp.ClientError,
            TimeoutError,
        ) as err:
            raise UpdateFailed(str(err)) from err
