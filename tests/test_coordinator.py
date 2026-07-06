"""Tests for the ILEO data coordinator."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ileo.api import IleoAuthError, IleoConnectionError, IleoCsvError
from custom_components.ileo.const import CONF_START_DATE, DEFAULT_SCAN_INTERVAL
from custom_components.ileo.coordinator import IleoDataUpdateCoordinator


def test_constructor_wires_update_settings_and_api_client() -> None:
    """The coordinator constructor configures polling and the ILEO API client."""
    hass = Mock()
    entry = Mock(
        data={
            CONF_USERNAME: "user@example.test",
            CONF_PASSWORD: "secret",
            CONF_START_DATE: "2026-01-15",
        }
    )
    session = Mock()

    with (
        patch(
            "custom_components.ileo.coordinator.async_get_clientsession",
            return_value=session,
        ) as get_session,
        patch("custom_components.ileo.coordinator.IleoApiClient") as api_client,
    ):
        coordinator = IleoDataUpdateCoordinator(hass, entry)

    get_session.assert_called_once_with(hass)
    api_client.assert_called_once_with(
        session=session,
        username="user@example.test",
        password="secret",
    )
    assert coordinator.config_entry is entry
    assert coordinator.update_interval == DEFAULT_SCAN_INTERVAL
    assert coordinator.always_update is False


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
    [
        IleoConnectionError("offline"),
        IleoCsvError("bad csv"),
        aiohttp.ClientError("transport failed"),
        TimeoutError("timed out"),
    ],
)
async def test_update_maps_recoverable_errors_to_update_failed(error: Exception) -> None:
    """Connection and CSV failures are transient update failures."""
    coordinator = _coordinator_with_client(error)

    with pytest.raises(UpdateFailed, match=str(error)):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_uses_home_assistant_timezone_date_for_end_date() -> None:
    """The coordinator uses Home Assistant's timezone-aware current date."""
    coordinator = IleoDataUpdateCoordinator.__new__(IleoDataUpdateCoordinator)
    coordinator.config_entry = Mock(data={CONF_START_DATE: "2026-01-15"})
    coordinator._client = Mock()
    coordinator._client.async_fetch_readings = AsyncMock(return_value=[])

    with patch(
        "custom_components.ileo.coordinator.dt_util.now",
        return_value=datetime(2026, 7, 6, 23, 30, tzinfo=timezone.utc),
    ):
        assert await coordinator._async_update_data() == []

    coordinator._client.async_fetch_readings.assert_awaited_once()
    start_date, end_date = coordinator._client.async_fetch_readings.await_args.args
    assert start_date.isoformat() == "2026-01-15"
    assert end_date.isoformat() == "2026-07-06"
