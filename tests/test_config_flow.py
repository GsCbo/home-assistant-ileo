"""Tests for the ILEO config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ileo.api import IleoAuthError, IleoConnectionError
from custom_components.ileo.const import CONF_START_DATE, DEFAULT_START_DATE, DOMAIN


pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_user_flow_shows_form(hass):
    """The user step initially shows a form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == config_entries.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_valid_input_validates_credentials_and_creates_entry(hass):
    """Valid credentials create an entry with normalized account data."""
    session = Mock()

    with (
        patch(
            "custom_components.ileo.config_flow.async_get_clientsession",
            return_value=session,
        ),
        patch("custom_components.ileo.config_flow.IleoApiClient") as api_client,
    ):
        client = api_client.return_value
        client.async_validate_credentials = AsyncMock(return_value=True)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_USERNAME: "  USER@Example.COM ",
                CONF_PASSWORD: " keep-this-secret ",
                CONF_START_DATE: "2026-01-15",
            },
        )

    assert result["type"] == config_entries.FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@example.com"
    assert result["data"] == {
        CONF_USERNAME: "user@example.com",
        CONF_PASSWORD: " keep-this-secret ",
        CONF_START_DATE: "2026-01-15",
    }
    api_client.assert_called_once_with(
        session=session,
        username="user@example.com",
        password=" keep-this-secret ",
    )
    client.async_validate_credentials.assert_awaited_once()


async def test_valid_input_uses_default_start_date(hass):
    """The start date defaults when omitted from user input."""
    with (
        patch("custom_components.ileo.config_flow.async_get_clientsession"),
        patch("custom_components.ileo.config_flow.IleoApiClient") as api_client,
    ):
        api_client.return_value.async_validate_credentials = AsyncMock(return_value=True)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "secret",
            },
        )

    assert result["type"] == config_entries.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_START_DATE] == DEFAULT_START_DATE


async def test_auth_error_maps_to_invalid_auth(hass):
    """Authentication failures show invalid_auth on the form."""
    with (
        patch("custom_components.ileo.config_flow.async_get_clientsession"),
        patch("custom_components.ileo.config_flow.IleoApiClient") as api_client,
    ):
        api_client.return_value.async_validate_credentials = AsyncMock(
            side_effect=IleoAuthError
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "bad-secret",
            },
        )

    assert result["type"] == config_entries.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.parametrize(
    "error",
    [
        IleoConnectionError,
        aiohttp.ClientError,
        TimeoutError,
    ],
)
async def test_connection_errors_map_to_cannot_connect(hass, error):
    """Connection failures show cannot_connect on the form."""
    with (
        patch("custom_components.ileo.config_flow.async_get_clientsession"),
        patch("custom_components.ileo.config_flow.IleoApiClient") as api_client,
    ):
        api_client.return_value.async_validate_credentials = AsyncMock(side_effect=error)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "secret",
            },
        )

    assert result["type"] == config_entries.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_normalized_account_aborts(hass):
    """The flow aborts when a normalized account already exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="user@example.com",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_USERNAME: " USER@example.COM ",
            CONF_PASSWORD: "secret",
        },
    )

    assert result["type"] == config_entries.FlowResultType.ABORT
    assert result["reason"] == "already_configured"
