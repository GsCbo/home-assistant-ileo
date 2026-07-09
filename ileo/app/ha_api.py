"""Home Assistant Core API client for Supervisor apps."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_CORE_API_URL = "http://supervisor/core/api"
DEFAULT_CORE_WS_URL = "ws://supervisor/core/websocket"


class HomeAssistantApiError(Exception):
    """Raised when Home Assistant Core rejects an API request."""


class HomeAssistantClient:
    """Small async REST client using the Supervisor-provided Core API proxy."""

    def __init__(
        self,
        session,
        *,
        base_url: str = DEFAULT_CORE_API_URL,
        websocket_url: str = DEFAULT_CORE_WS_URL,
        token: str | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._websocket_url = websocket_url
        self._token = token or os.environ.get("SUPERVISOR_TOKEN")
        if not self._token:
            raise HomeAssistantApiError("SUPERVISOR_TOKEN is required")

    async def async_set_state(
        self,
        entity_id: str,
        state: str | int | float,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        """Set or update an entity state in Home Assistant."""
        return await self.async_post(
            f"/states/{entity_id}",
            {"state": state, "attributes": attributes},
        )

    async def async_import_statistics(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Import dated long-term statistics through Home Assistant WebSocket API."""
        return await self.async_ws_command(
            {
                "type": "recorder/import_statistics",
                **payload,
            }
        )

    async def async_post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to Home Assistant Core and return the JSON response when present."""
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        async with self._session.post(url, json=payload, headers=headers) as response:
            body = await response.text()
            if response.status >= 400:
                raise HomeAssistantApiError(
                    f"Home Assistant API returned {response.status} for {path}: {body}"
                )
            if not body:
                return {}
            return await response.json()

    async def async_ws_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """Send one authenticated Home Assistant WebSocket command."""
        headers = {"Authorization": f"Bearer {self._token}"}
        async with self._session.ws_connect(
            self._websocket_url,
            headers=headers,
        ) as websocket:
            auth_required = await websocket.receive_json()
            if auth_required.get("type") == "auth_required":
                await websocket.send_json(
                    {
                        "type": "auth",
                        "access_token": self._token,
                    }
                )
                auth_response = await websocket.receive_json()
            else:
                auth_response = auth_required

            if auth_response.get("type") != "auth_ok":
                raise HomeAssistantApiError(
                    f"Home Assistant WebSocket authentication failed: {auth_response}"
                )

            command_id = 1
            await websocket.send_json({"id": command_id, **command})
            while True:
                response = await websocket.receive_json()
                if response.get("id") != command_id:
                    continue
                if not response.get("success", False):
                    raise HomeAssistantApiError(
                        f"Home Assistant WebSocket command failed: {response}"
                    )
                result = response.get("result")
                return result if isinstance(result, dict) else {}
