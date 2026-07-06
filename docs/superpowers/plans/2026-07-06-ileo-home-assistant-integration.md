# ILEO Home Assistant Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS-ready Home Assistant custom integration for ILEO that creates water sensors compatible with the Home Assistant Energy dashboard.

**Architecture:** Add a native `custom_components/ileo` integration with a UI config flow, a small HTTP/CSV API client, a `DataUpdateCoordinator`, and sensor entities. Keep the existing Docker scraper as legacy/reference until the native integration is verified.

**Tech Stack:** Home Assistant custom integration APIs, `aiohttp`, `DataUpdateCoordinator`, `SensorEntity`, `pytest`, `pytest-homeassistant-custom-component` test patterns.

---

## File Structure

- Create `custom_components/ileo/manifest.json`: integration metadata for HACS and Home Assistant.
- Create `custom_components/ileo/const.py`: domain, config keys, defaults, platform list.
- Create `custom_components/ileo/api.py`: ILEO HTTP session, login validation, CSV export download, CSV parsing.
- Create `custom_components/ileo/coordinator.py`: shared polling and error translation.
- Create `custom_components/ileo/__init__.py`: config entry setup, unload, runtime data.
- Create `custom_components/ileo/config_flow.py`: user setup, duplicate prevention, options flow.
- Create `custom_components/ileo/sensor.py`: water index, last consumption, and last reading date entities.
- Create `custom_components/ileo/diagnostics.py`: redacted diagnostics.
- Create `custom_components/ileo/strings.json`: config flow text.
- Create `custom_components/ileo/translations/fr.json`: French config flow text.
- Create `hacs.json`: HACS metadata.
- Create `tests/fixtures/ileo_export.csv`: realistic CSV sample based on the current scraper columns.
- Create `tests/test_api.py`: parser and API-client unit tests.
- Create `tests/test_config_flow.py`: Home Assistant config flow tests.
- Create `tests/test_sensor.py`: sensor metadata and state tests.
- Create `tests/conftest.py`: Home Assistant test helpers and fake clients.
- Modify `README.md`: document HACS install, UI setup, Energy dashboard setup, and legacy Docker status.
- Modify `requirements.txt`: remove runtime Selenium/MQTT focus only if Docker path is formally deprecated; otherwise keep as legacy and add comments in README instead of changing behavior.

## Scope Notes

Historical statistics import is intentionally not implemented in the first executable pass. The first pass creates an Energy-compatible `total_increasing` water index sensor so Home Assistant long-term statistics start collecting immediately. Historical import remains a follow-up task after the native client is confirmed against the live ILEO portal, because Home Assistant statistics writes are strict and should be validated in a disposable HA instance.

### Task 1: Integration Skeleton And Metadata

**Files:**
- Create: `custom_components/ileo/manifest.json`
- Create: `custom_components/ileo/const.py`
- Create: `custom_components/ileo/__init__.py`
- Create: `custom_components/ileo/strings.json`
- Create: `custom_components/ileo/translations/fr.json`
- Create: `hacs.json`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create the manifest**

Create `custom_components/ileo/manifest.json`:

```json
{
  "domain": "ileo",
  "name": "ILEO",
  "after_dependencies": [],
  "codeowners": ["@GsCbo"],
  "config_flow": true,
  "documentation": "https://github.com/GsCbo/home-assistant-ileo-scraper",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/GsCbo/home-assistant-ileo-scraper/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

- [ ] **Step 2: Add constants**

Create `custom_components/ileo/const.py`:

```python
"""Constants for the ILEO integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME

DOMAIN = "ileo"
PLATFORMS = ["sensor"]

CONF_START_DATE = "start_date"
DEFAULT_SCAN_INTERVAL = timedelta(hours=4)
DEFAULT_START_DATE = "2025-03-01"

BASE_URL = "https://www.mel-ileo.fr"
LOGIN_URL = f"{BASE_URL}/connexion.aspx"
CONSUMPTION_URL = f"{BASE_URL}/espaceperso/mes-consommations.aspx"

CONF_KEYS = (CONF_USERNAME, CONF_PASSWORD, CONF_START_DATE, CONF_SCAN_INTERVAL)
```

- [ ] **Step 3: Add minimal setup entry lifecycle**

Create `custom_components/ileo/__init__.py`:

```python
"""The ILEO integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS

type IleoConfigEntry = ConfigEntry[object]


async def async_setup_entry(hass: HomeAssistant, entry: IleoConfigEntry) -> bool:
    """Set up ILEO from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = None
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IleoConfigEntry) -> bool:
    """Unload an ILEO config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
```

- [ ] **Step 4: Add translation files**

Create `custom_components/ileo/strings.json`:

```json
{
  "title": "ILEO",
  "config": {
    "step": {
      "user": {
        "title": "Connect ILEO",
        "description": "Enter your ILEO account credentials.",
        "data": {
          "username": "Email",
          "password": "Password",
          "start_date": "History start date"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect",
      "invalid_auth": "Invalid authentication",
      "unknown": "Unexpected error"
    },
    "abort": {
      "already_configured": "This ILEO account is already configured"
    }
  }
}
```

Create `custom_components/ileo/translations/fr.json`:

```json
{
  "title": "ILEO",
  "config": {
    "step": {
      "user": {
        "title": "Connecter ILEO",
        "description": "Renseignez les identifiants de votre compte ILEO.",
        "data": {
          "username": "Email",
          "password": "Mot de passe",
          "start_date": "Date de debut de l'historique"
        }
      }
    },
    "error": {
      "cannot_connect": "Connexion impossible",
      "invalid_auth": "Identifiants invalides",
      "unknown": "Erreur inattendue"
    },
    "abort": {
      "already_configured": "Ce compte ILEO est deja configure"
    }
  }
}
```

- [ ] **Step 5: Add HACS metadata**

Create `hacs.json`:

```json
{
  "name": "ILEO",
  "render_readme": true
}
```

- [ ] **Step 6: Add basic test config**

Create `tests/conftest.py`:

```python
"""Test fixtures for the ILEO integration."""

from __future__ import annotations

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in Home Assistant tests."""
    return enable_custom_integrations
```

- [ ] **Step 7: Verify file structure**

Run:

```powershell
rg --files custom_components tests
```

Expected: the new integration files and `tests/conftest.py` are listed.

- [ ] **Step 8: Commit**

Run:

```powershell
git add custom_components hacs.json tests/conftest.py
git commit -m "Add ILEO integration skeleton"
```

Expected: commit succeeds.

### Task 2: CSV Parsing And API Error Model

**Files:**
- Create: `custom_components/ileo/api.py`
- Create: `tests/fixtures/ileo_export.csv`
- Create: `tests/test_api.py`

- [ ] **Step 1: Add CSV fixture**

Create `tests/fixtures/ileo_export.csv`:

```csv
date;consommation (litres);index
01/03/2025;0;120000
02/03/2025;180;120180
03/03/2025;245;120425
04/03/2025;;120425
05/03/2025;90;120515
```

- [ ] **Step 2: Write parser tests**

Create `tests/test_api.py`:

```python
"""Tests for the ILEO API client."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from custom_components.ileo.api import IleoCsvError, parse_readings_csv


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_readings_csv_filters_zero_and_missing_values() -> None:
    """Parser keeps valid positive readings and skips unusable rows."""
    readings = parse_readings_csv((FIXTURES / "ileo_export.csv").read_text(encoding="utf-8"))

    assert [reading.date for reading in readings] == [
        date(2025, 3, 2),
        date(2025, 3, 3),
        date(2025, 3, 5),
    ]
    assert readings[0].litres == 180.0
    assert readings[0].index_litres == 120180


def test_parse_readings_csv_sorts_by_date() -> None:
    """Parser returns readings sorted by date."""
    csv_text = (
        "date;consommation (litres);index\n"
        "03/03/2025;245;120425\n"
        "02/03/2025;180;120180\n"
    )

    readings = parse_readings_csv(csv_text)

    assert [reading.date for reading in readings] == [date(2025, 3, 2), date(2025, 3, 3)]


def test_parse_readings_csv_raises_for_missing_columns() -> None:
    """Parser fails clearly when the ILEO CSV format changes."""
    with pytest.raises(IleoCsvError):
        parse_readings_csv("date;litres\n02/03/2025;180\n")
```

- [ ] **Step 3: Run parser tests to verify they fail**

Run:

```powershell
pytest tests/test_api.py -v
```

Expected: FAIL because `custom_components.ileo.api` does not exist yet.

- [ ] **Step 4: Implement parser and error classes**

Create `custom_components/ileo/api.py`:

```python
"""ILEO website client and CSV parsing."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO


class IleoError(Exception):
    """Base error for ILEO failures."""


class IleoAuthError(IleoError):
    """Raised when ILEO rejects credentials."""


class IleoConnectionError(IleoError):
    """Raised when the ILEO portal cannot be reached."""


class IleoCsvError(IleoError):
    """Raised when an ILEO CSV export cannot be parsed."""


@dataclass(frozen=True, slots=True)
class IleoReading:
    """One ILEO water reading."""

    date: date
    litres: float
    index_litres: int


REQUIRED_COLUMNS = {"date", "consommation (litres)", "index"}


def parse_readings_csv(csv_text: str) -> list[IleoReading]:
    """Parse an ILEO CSV export into sorted readings."""
    reader = csv.DictReader(StringIO(csv_text), delimiter=";")
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise IleoCsvError(f"Unexpected CSV columns: {reader.fieldnames}")

    readings: list[IleoReading] = []
    for row in reader:
        raw_date = (row.get("date") or "").strip()
        raw_litres = (row.get("consommation (litres)") or "").strip()
        raw_index = (row.get("index") or "").strip()
        if not raw_date or not raw_litres or not raw_index:
            continue

        try:
            litres = float(raw_litres.replace(",", "."))
            index_litres = int(float(raw_index.replace(",", ".")))
            reading_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
        except ValueError as err:
            raise IleoCsvError(f"Invalid CSV row: {row}") from err

        if litres <= 0:
            continue

        readings.append(
            IleoReading(
                date=reading_date,
                litres=litres,
                index_litres=index_litres,
            )
        )

    return sorted(readings, key=lambda reading: reading.date)
```

- [ ] **Step 5: Run parser tests to verify they pass**

Run:

```powershell
pytest tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add custom_components/ileo/api.py tests/fixtures/ileo_export.csv tests/test_api.py
git commit -m "Add ILEO CSV parsing"
```

Expected: commit succeeds.

### Task 3: HTTP Client Contract

**Files:**
- Modify: `custom_components/ileo/api.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Add API client tests with a fake session**

Append to `tests/test_api.py`:

```python
from datetime import timedelta

from custom_components.ileo.api import IleoApiClient, IleoAuthError


class FakeResponse:
    """Small async response object for ILEO client tests."""

    def __init__(self, *, status: int, text: str, url: str = "https://www.mel-ileo.fr/espaceperso"):
        self.status = status
        self._text = text
        self.url = url

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def text(self) -> str:
        return self._text


class FakeSession:
    """Records requests and returns queued fake responses."""

    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.requests: list[tuple[str, str, dict]] = []

    def get(self, url: str, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return self.responses.pop(0)

    def post(self, url: str, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_api_validate_credentials_posts_login_form() -> None:
    """Credential validation opens login page then submits the login form."""
    session = FakeSession(
        [
            FakeResponse(
                status=200,
                text=(
                    '<input type="hidden" name="__VIEWSTATE" value="state">'
                    '<input type="hidden" name="__EVENTVALIDATION" value="event">'
                ),
            ),
            FakeResponse(status=200, text="Mes consommations", url="https://www.mel-ileo.fr/espaceperso"),
        ]
    )
    client = IleoApiClient(session=session, username="user@example.com", password="secret")

    assert await client.async_validate_credentials() is True
    assert session.requests[0][0] == "GET"
    assert session.requests[1][0] == "POST"
    assert session.requests[1][2]["data"]["email"] == "user@example.com"
    assert session.requests[1][2]["data"]["password"] == "secret"


@pytest.mark.asyncio
async def test_api_validate_credentials_raises_for_login_page_response() -> None:
    """Credential validation raises an auth error when login does not reach private pages."""
    session = FakeSession(
        [
            FakeResponse(status=200, text="login page"),
            FakeResponse(status=200, text="je me connecte", url="https://www.mel-ileo.fr/connexion.aspx"),
        ]
    )
    client = IleoApiClient(session=session, username="user@example.com", password="bad")

    with pytest.raises(IleoAuthError):
        await client.async_validate_credentials()


@pytest.mark.asyncio
async def test_api_fetch_readings_downloads_csv_after_login() -> None:
    """Fetching readings validates the session and parses the CSV export."""
    session = FakeSession(
        [
            FakeResponse(status=200, text="login page"),
            FakeResponse(status=200, text="Mes consommations", url="https://www.mel-ileo.fr/espaceperso"),
            FakeResponse(
                status=200,
                text="date;consommation (litres);index\n02/03/2025;180;120180\n",
            ),
        ]
    )
    client = IleoApiClient(session=session, username="user@example.com", password="secret")

    readings = await client.async_fetch_readings(date(2025, 3, 1), date(2025, 3, 31))

    assert readings[0].index_litres == 120180
    assert "ex=1" in session.requests[-1][1]
    assert "dateDebut=01/03/2025" in session.requests[-1][1]
    assert "dateFin=31/03/2025" in session.requests[-1][1]
```

- [ ] **Step 2: Run API client tests to verify they fail**

Run:

```powershell
pytest tests/test_api.py -v
```

Expected: FAIL because `IleoApiClient` is not implemented.

- [ ] **Step 3: Implement the HTTP client**

Append to `custom_components/ileo/api.py`:

```python
from datetime import date as Date
from urllib.parse import urlencode

from .const import CONSUMPTION_URL, LOGIN_URL


class IleoApiClient:
    """Small HTTP client for the ILEO website."""

    def __init__(self, *, session, username: str, password: str) -> None:
        """Initialize the client."""
        self._session = session
        self._username = username
        self._password = password

    async def async_validate_credentials(self) -> bool:
        """Validate ILEO credentials by submitting the login form."""
        async with self._session.get(LOGIN_URL) as response:
            if response.status >= 400:
                raise IleoConnectionError(f"Login page returned HTTP {response.status}")
            login_html = await response.text()

        payload = self._build_login_payload(login_html)
        async with self._session.post(LOGIN_URL, data=payload) as response:
            if response.status >= 400:
                raise IleoConnectionError(f"Login submit returned HTTP {response.status}")
            body = await response.text()
            final_url = str(response.url)

        if "connexion.aspx" in final_url or "je me connecte" in body.lower():
            raise IleoAuthError("ILEO credentials were rejected")

        return True

    async def async_fetch_readings(self, start_date: Date, end_date: Date) -> list[IleoReading]:
        """Fetch readings from ILEO CSV export."""
        await self.async_validate_credentials()
        params = urlencode(
            {
                "ex": "1",
                "dateDebut": start_date.strftime("%d/%m/%Y"),
                "dateFin": end_date.strftime("%d/%m/%Y"),
            }
        )
        async with self._session.get(f"{CONSUMPTION_URL}?{params}") as response:
            if response.status >= 400:
                raise IleoConnectionError(f"CSV export returned HTTP {response.status}")
            csv_text = await response.text()

        return parse_readings_csv(csv_text)

    def _build_login_payload(self, login_html: str) -> dict[str, str]:
        """Build login payload, preserving ASP.NET hidden fields when present."""
        payload = {
            "email": self._username,
            "password": self._password,
        }
        for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
            value = _extract_input_value(login_html, name)
            if value is not None:
                payload[name] = value
        return payload


def _extract_input_value(html: str, name: str) -> str | None:
    """Extract a simple hidden input value from HTML."""
    marker = f'name="{name}"'
    marker_index = html.find(marker)
    if marker_index == -1:
        return None
    value_marker = 'value="'
    value_index = html.find(value_marker, marker_index)
    if value_index == -1:
        return ""
    value_start = value_index + len(value_marker)
    value_end = html.find('"', value_start)
    if value_end == -1:
        return ""
    return html[value_start:value_end]
```

- [ ] **Step 4: Run API client tests**

Run:

```powershell
pytest tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add custom_components/ileo/api.py tests/test_api.py
git commit -m "Add ILEO HTTP client contract"
```

Expected: commit succeeds.

### Task 4: Config Flow

**Files:**
- Create: `custom_components/ileo/config_flow.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_config_flow.py`

- [ ] **Step 1: Add config flow tests**

Create `tests/test_config_flow.py`:

```python
"""Tests for the ILEO config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.ileo.const import CONF_START_DATE, DOMAIN, DEFAULT_START_DATE


async def test_config_flow_creates_entry(hass) -> None:
    """The user flow validates credentials and creates an entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"

    with patch(
        "custom_components.ileo.config_flow.IleoApiClient.async_validate_credentials",
        new=AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "USER@EXAMPLE.COM",
                CONF_PASSWORD: "secret",
                CONF_START_DATE: "2025-03-01",
            },
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "user@example.com"
    assert result["data"][CONF_USERNAME] == "user@example.com"
    assert result["data"][CONF_PASSWORD] == "secret"
    assert result["data"][CONF_START_DATE] == "2025-03-01"


async def test_config_flow_invalid_auth(hass) -> None:
    """Invalid credentials show an invalid_auth error."""
    from custom_components.ileo.api import IleoAuthError

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(
        "custom_components.ileo.config_flow.IleoApiClient.async_validate_credentials",
        new=AsyncMock(side_effect=IleoAuthError),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "bad",
                CONF_START_DATE: DEFAULT_START_DATE,
            },
        )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_auth"


async def test_config_flow_duplicate_account(hass) -> None:
    """The same normalized account cannot be configured twice."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="user@example.com",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret",
            CONF_START_DATE: DEFAULT_START_DATE,
        },
        source=config_entries.SOURCE_USER,
        unique_id="user@example.com",
        options={},
        discovery_keys={},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(
        "custom_components.ileo.config_flow.IleoApiClient.async_validate_credentials",
        new=AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "USER@example.com",
                CONF_PASSWORD: "secret",
                CONF_START_DATE: DEFAULT_START_DATE,
            },
        )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
```

- [ ] **Step 2: Run config flow tests to verify they fail**

Run:

```powershell
pytest tests/test_config_flow.py -v
```

Expected: FAIL because `config_flow.py` does not exist.

- [ ] **Step 3: Implement config flow**

Create `custom_components/ileo/config_flow.py`:

```python
"""Config flow for the ILEO integration."""

from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IleoApiClient, IleoAuthError, IleoConnectionError
from .const import CONF_START_DATE, DEFAULT_START_DATE, DOMAIN


class IleoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an ILEO config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = IleoApiClient(
                session=session,
                username=username,
                password=user_input[CONF_PASSWORD],
            )
            try:
                await client.async_validate_credentials()
            except IleoAuthError:
                errors["base"] = "invalid_auth"
            except (IleoConnectionError, aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                data = dict(user_input)
                data[CONF_USERNAME] = username
                return self.async_create_entry(title=username, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_START_DATE, default=DEFAULT_START_DATE): str,
                }
            ),
            errors=errors,
        )
```

- [ ] **Step 4: Run config flow tests**

Run:

```powershell
pytest tests/test_config_flow.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add custom_components/ileo/config_flow.py tests/test_config_flow.py
git commit -m "Add ILEO config flow"
```

Expected: commit succeeds.

### Task 5: Coordinator And Runtime Setup

**Files:**
- Create: `custom_components/ileo/coordinator.py`
- Modify: `custom_components/ileo/__init__.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add coordinator implementation**

Create `custom_components/ileo/coordinator.py`:

```python
"""Coordinator for the ILEO integration."""

from __future__ import annotations

from datetime import date, datetime
import logging

from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import IleoApiClient, IleoAuthError, IleoConnectionError, IleoCsvError, IleoReading
from .const import CONF_START_DATE, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class IleoDataUpdateCoordinator(DataUpdateCoordinator[list[IleoReading]]):
    """Fetch and store ILEO readings."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize the coordinator."""
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
        """Fetch data from ILEO."""
        start_date = datetime.strptime(
            self.config_entry.data[CONF_START_DATE],
            "%Y-%m-%d",
        ).date()
        end_date = date.today()

        try:
            return await self._client.async_fetch_readings(start_date, end_date)
        except IleoAuthError as err:
            raise ConfigEntryAuthFailed from err
        except (IleoConnectionError, IleoCsvError) as err:
            raise UpdateFailed(str(err)) from err
```

- [ ] **Step 2: Wire coordinator into setup**

Replace `custom_components/ileo/__init__.py` with:

```python
"""The ILEO integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import IleoDataUpdateCoordinator

type IleoConfigEntry = ConfigEntry[IleoDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: IleoConfigEntry) -> bool:
    """Set up ILEO from a config entry."""
    coordinator = IleoDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IleoConfigEntry) -> bool:
    """Unload an ILEO config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
```

- [ ] **Step 3: Run currently available tests**

Run:

```powershell
pytest tests/test_api.py tests/test_config_flow.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```powershell
git add custom_components/ileo/__init__.py custom_components/ileo/coordinator.py
git commit -m "Add ILEO data coordinator"
```

Expected: commit succeeds.

### Task 6: Energy-Compatible Sensors

**Files:**
- Create: `custom_components/ileo/sensor.py`
- Create: `tests/test_sensor.py`

- [ ] **Step 1: Add sensor metadata tests**

Create `tests/test_sensor.py`:

```python
"""Tests for ILEO sensors."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfVolume

from custom_components.ileo.api import IleoReading
from custom_components.ileo.sensor import (
    IleoLastConsumptionSensor,
    IleoLastReadingDateSensor,
    IleoWaterIndexSensor,
)


def _coordinator():
    return SimpleNamespace(
        data=[
            IleoReading(date=date(2025, 3, 2), litres=180.0, index_litres=120180),
            IleoReading(date=date(2025, 3, 3), litres=245.0, index_litres=120425),
        ],
        config_entry=SimpleNamespace(entry_id="abc123", unique_id="user@example.com"),
    )


def test_water_index_sensor_energy_metadata() -> None:
    """Water index sensor exposes metadata required by Energy water dashboard."""
    sensor = IleoWaterIndexSensor(_coordinator())

    assert sensor.native_value == 120425
    assert sensor.native_unit_of_measurement == UnitOfVolume.LITERS
    assert sensor.device_class is SensorDeviceClass.WATER
    assert sensor.state_class is SensorStateClass.TOTAL_INCREASING
    assert sensor.unique_id == "user@example.com_water_index"


def test_last_consumption_sensor_metadata() -> None:
    """Last consumption sensor exposes measurement metadata."""
    sensor = IleoLastConsumptionSensor(_coordinator())

    assert sensor.native_value == 245.0
    assert sensor.native_unit_of_measurement == UnitOfVolume.LITERS
    assert sensor.device_class is SensorDeviceClass.WATER
    assert sensor.state_class is SensorStateClass.MEASUREMENT


def test_last_reading_date_sensor_value() -> None:
    """Last reading date sensor returns the latest reading date."""
    sensor = IleoLastReadingDateSensor(_coordinator())

    assert sensor.native_value == date(2025, 3, 3)
```

- [ ] **Step 2: Run sensor tests to verify they fail**

Run:

```powershell
pytest tests/test_sensor.py -v
```

Expected: FAIL because `sensor.py` does not exist.

- [ ] **Step 3: Implement sensors**

Create `custom_components/ileo/sensor.py`:

```python
"""Sensors for the ILEO integration."""

from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IleoDataUpdateCoordinator


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up ILEO sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            IleoWaterIndexSensor(coordinator),
            IleoLastConsumptionSensor(coordinator),
            IleoLastReadingDateSensor(coordinator),
        ]
    )


class IleoBaseSensor(CoordinatorEntity[IleoDataUpdateCoordinator], SensorEntity):
    """Base class for ILEO sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IleoDataUpdateCoordinator, suffix: str, name: str) -> None:
        """Initialize a sensor."""
        super().__init__(coordinator)
        unique_root = coordinator.config_entry.unique_id or coordinator.config_entry.entry_id
        self._attr_unique_id = f"{unique_root}_{suffix}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(unique_root))},
            manufacturer="ILEO",
            name="ILEO",
        )

    @property
    def _latest_reading(self):
        """Return the latest available reading."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data[-1]


class IleoWaterIndexSensor(IleoBaseSensor):
    """Total water meter index sensor."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: IleoDataUpdateCoordinator) -> None:
        """Initialize the water index sensor."""
        super().__init__(coordinator, "water_index", "Water index")

    @property
    def native_value(self) -> int | None:
        """Return latest meter index."""
        latest = self._latest_reading
        return latest.index_litres if latest else None


class IleoLastConsumptionSensor(IleoBaseSensor):
    """Last daily consumption sensor."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: IleoDataUpdateCoordinator) -> None:
        """Initialize the last consumption sensor."""
        super().__init__(coordinator, "last_consumption", "Last consumption")

    @property
    def native_value(self) -> float | None:
        """Return latest daily consumption."""
        latest = self._latest_reading
        return latest.litres if latest else None


class IleoLastReadingDateSensor(IleoBaseSensor):
    """Last reading date sensor."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: IleoDataUpdateCoordinator) -> None:
        """Initialize the last reading date sensor."""
        super().__init__(coordinator, "last_reading_date", "Last reading date")

    @property
    def native_value(self) -> date | None:
        """Return latest reading date."""
        latest = self._latest_reading
        return latest.date if latest else None
```

- [ ] **Step 4: Run sensor tests**

Run:

```powershell
pytest tests/test_sensor.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all tests**

Run:

```powershell
pytest tests -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add custom_components/ileo/sensor.py tests/test_sensor.py
git commit -m "Add ILEO water sensors"
```

Expected: commit succeeds.

### Task 7: Diagnostics And Documentation

**Files:**
- Create: `custom_components/ileo/diagnostics.py`
- Modify: `README.md`

- [ ] **Step 1: Add diagnostics**

Create `custom_components/ileo/diagnostics.py`:

```python
"""Diagnostics support for ILEO."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

TO_REDACT = {CONF_PASSWORD}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Return diagnostics for an ILEO config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "readings_count": len(coordinator.data or []),
        "last_update_success": coordinator.last_update_success,
    }
```

- [ ] **Step 2: Replace README with HACS-first documentation**

Modify `README.md` so the top-level sections are:

```markdown
# ILEO for Home Assistant

Custom Home Assistant integration for ILEO water consumption.

## Status

This repository is being migrated from a Docker/MQTT scraper to a HACS-ready Home Assistant custom integration.

## Installation with HACS

1. In HACS, add this repository as a custom repository.
2. Select category `Integration`.
3. Install `ILEO`.
4. Restart Home Assistant.
5. Go to Settings > Devices & services > Add integration > ILEO.

## Configuration

Enter:

- ILEO email
- ILEO password
- optional history start date, default `2025-03-01`

## Energy Dashboard

After the first successful update, use `sensor.ileo_water_index` or the generated water index entity in:

Settings > Dashboards > Energy > Water consumption.

The index entity uses:

- device class: `water`
- state class: `total_increasing`
- unit: `L`

## Legacy Docker/MQTT scraper

The previous Docker and MQTT workflow remains in the repository as a legacy reference during migration. The native integration is the recommended path once live ILEO login and CSV download are validated.

## Development

Run tests with:

```powershell
pytest tests -v
```
```

- [ ] **Step 3: Run tests**

Run:

```powershell
pytest tests -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```powershell
git add custom_components/ileo/diagnostics.py README.md
git commit -m "Document HACS integration setup"
```

Expected: commit succeeds.

### Task 8: Final Verification And Live-Risk Check

**Files:**
- No planned source edits.

- [ ] **Step 1: Run full test suite**

Run:

```powershell
pytest tests -v
```

Expected: PASS.

- [ ] **Step 2: Inspect repository status**

Run:

```powershell
git status --short
```

Expected: no output.

- [ ] **Step 3: Inspect commit history**

Run:

```powershell
git log --oneline -8
```

Expected: recent commits show skeleton, parser, client, config flow, coordinator, sensors, docs.

- [ ] **Step 4: Record remaining live validation requirement**

Add a final implementation note to the user response:

```text
The native integration code is ready for local tests. The remaining real-world validation is logging into mel-ileo.fr without Selenium from Home Assistant's aiohttp session. If that endpoint rejects non-browser requests, the next design decision is whether to keep a supervised external scraper or investigate a lightweight browserless form workflow.
```

## Self-Review

Spec coverage:

- HACS-ready package: Tasks 1 and 7.
- UI config flow: Task 4.
- No MQTT/Selenium primary path: Tasks 3 and 7.
- Water sensor compatible with Energy: Task 6.
- Error distinction: Tasks 2, 3, 4, and 5.
- Diagnostics credential redaction: Task 7.
- Tests for parser/config/sensors/coordinator-adjacent behavior: Tasks 2, 4, 6, and 8.

Deferred with explicit rationale:

- Historical statistics import is deferred until the native HTTP login path is validated against the live ILEO portal. The first version still creates the correct long-term-statistics-compatible water index sensor.

Placeholder scan:

- No red-flag placeholder wording is present.

Type consistency:

- `IleoReading.date`, `IleoReading.litres`, and `IleoReading.index_litres` are defined in Task 2 and reused consistently.
- `IleoApiClient.async_validate_credentials()` and `IleoApiClient.async_fetch_readings()` are introduced in Task 3 and used by config flow/coordinator.
- `CONF_START_DATE`, `DEFAULT_START_DATE`, and `DEFAULT_SCAN_INTERVAL` are defined in Task 1 and reused consistently.
