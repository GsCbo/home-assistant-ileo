"""Tests for the ILEO data coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ileo.api import IleoAuthError, IleoConnectionError, IleoCsvError
from custom_components.ileo.const import CONF_START_DATE
from custom_components.ileo.coordinator import IleoDataUpdateCoordinator


def _coordinator_with_client(error: Exception) -> IleoDataUpdateCoordinator:
    coordinator = IleoDataUpdateCoordinator.__new__(IleoDataUpdateCoordinator)
    coordinator.config_entry = Mock(data={CONF_START_DATE: "2026-01-15"})
    coordinator._client = Mock()
    coordinator._client.async_fetch_readings = AsyncMock(side_effect=error)
    return coordinator


@pytest.mark.asyncio
async def test_update_maps_auth_error_to_config_entry_auth_failed() -> None:
    """Authentication errors force Home Assistant to reauth the config entry."""
    coordinator = _coordinator_with_client(IleoAuthError("bad credentials"))

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [IleoConnectionError("offline"), IleoCsvError("bad csv")],
)
async def test_update_maps_recoverable_errors_to_update_failed(error: Exception) -> None:
    """Connection and CSV failures are transient update failures."""
    coordinator = _coordinator_with_client(error)

    with pytest.raises(UpdateFailed, match=str(error)):
        await coordinator._async_update_data()
