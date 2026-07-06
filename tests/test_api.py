"""Tests for the ILEO API helpers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
API_PATH = Path(__file__).parents[1] / "custom_components" / "ileo" / "api.py"

spec = importlib.util.spec_from_file_location("ileo_api_under_test", API_PATH)
assert spec is not None
assert spec.loader is not None
ileo_api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ileo_api
spec.loader.exec_module(ileo_api)

IleoCsvError = ileo_api.IleoCsvError
IleoAuthError = ileo_api.IleoAuthError
IleoConnectionError = ileo_api.IleoConnectionError
IleoApiClient = ileo_api.IleoApiClient
parse_readings_csv = ileo_api.parse_readings_csv


class FakeResponse:
    """Small async response double matching aiohttp's context-manager shape."""

    def __init__(self, *, status: int = 200, url: str, body: str) -> None:
        self.status = status
        self.url = url
        self._body = body

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def text(self) -> str:
        return self._body


class FakeSession:
    """Queue-backed fake session recording GET and POST calls."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def get(self, url: str) -> FakeResponse:
        self.calls.append(("GET", url, {}))
        return self._responses.pop(0)

    def post(self, url: str, *, data: dict[str, str]) -> FakeResponse:
        self.calls.append(("POST", url, {"data": data}))
        return self._responses.pop(0)


LOGIN_HTML = """
<html>
  <body>
    <form>
      <input type="hidden" name="__VIEWSTATE" value="view-state-token" />
      <input type="hidden" name="__VIEWSTATEGENERATOR" value="generator-token" />
      <input type="hidden" name="__EVENTVALIDATION" value="event-validation-token" />
      <input type="hidden" name="__RequestVerificationToken" value="request-token" />
      <input type="hidden" name="ctl00$hidden" value="control-token" />
      <input name="email" />
      <input name="password" />
    </form>
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_async_validate_credentials_posts_credentials_and_hidden_fields() -> None:
    """The login POST preserves ASP.NET fields and reaches the private page."""
    session = FakeSession(
        [
            FakeResponse(url=ileo_api.LOGIN_URL, body=LOGIN_HTML),
            FakeResponse(url=ileo_api.CONSUMPTION_URL, body="<html>mes consommations</html>"),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "secret")

    result = await client.async_validate_credentials()

    assert result is True
    assert session.calls[0] == ("GET", ileo_api.LOGIN_URL, {})
    method, url, kwargs = session.calls[1]
    assert method == "POST"
    assert url == ileo_api.LOGIN_URL
    assert kwargs["data"] == {
        "__VIEWSTATE": "view-state-token",
        "__VIEWSTATEGENERATOR": "generator-token",
        "__EVENTVALIDATION": "event-validation-token",
        "__RequestVerificationToken": "request-token",
        "ctl00$hidden": "control-token",
        "email": "user@example.test",
        "password": "secret",
    }


def test_build_login_payload_preserves_arbitrary_hidden_fields() -> None:
    """All hidden fields from the login form are submitted with credentials."""
    client = IleoApiClient(FakeSession([]), "user@example.test", "secret")

    payload = client._build_login_payload(
        """
        <input type="hidden" name="__RequestVerificationToken" value="request-token" />
        <input type="hidden" name="ctl00$hidden" value="control-token" />
        """
    )

    assert payload == {
        "__RequestVerificationToken": "request-token",
        "ctl00$hidden": "control-token",
        "email": "user@example.test",
        "password": "secret",
    }


@pytest.mark.asyncio
async def test_async_validate_credentials_raises_connection_error_for_unexpected_login_page() -> None:
    """A 200 response without the expected login form shape is treated as connection drift."""
    session = FakeSession(
        [
            FakeResponse(
                url=ileo_api.LOGIN_URL,
                body="<html><h1>Service unavailable</h1><p>Try later</p></html>",
            ),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "secret")

    with pytest.raises(IleoConnectionError):
        await client.async_validate_credentials()

    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_async_validate_credentials_rejects_hidden_only_unexpected_page() -> None:
    """A hidden input alone is not enough evidence of the login form."""
    session = FakeSession(
        [
            FakeResponse(
                url=ileo_api.LOGIN_URL,
                body='<html><input type="hidden" name="tracking" value="abc" /></html>',
            ),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "secret")

    with pytest.raises(IleoConnectionError):
        await client.async_validate_credentials()

    assert len(session.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("final_url", "body"),
    [
        (ileo_api.LOGIN_URL, "<html>mes consommations</html>"),
        (ileo_api.CONSUMPTION_URL, "<button>Je me connecte</button>"),
    ],
)
async def test_async_validate_credentials_raises_when_login_page_remains(
    final_url: str, body: str
) -> None:
    """Authentication fails when the final page is still the login screen."""
    session = FakeSession(
        [
            FakeResponse(url=ileo_api.LOGIN_URL, body=LOGIN_HTML),
            FakeResponse(url=final_url, body=body),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "wrong")

    with pytest.raises(IleoAuthError):
        await client.async_validate_credentials()


@pytest.mark.asyncio
async def test_async_fetch_readings_validates_session_and_downloads_csv_export() -> None:
    """Fetching readings logs in, requests the CSV export, and parses readings."""
    csv_text = "date;consommation (litres);index\n02/03/2025;180;120180\n"
    session = FakeSession(
        [
            FakeResponse(url=ileo_api.LOGIN_URL, body=LOGIN_HTML),
            FakeResponse(url=ileo_api.CONSUMPTION_URL, body="<html>mes consommations</html>"),
            FakeResponse(url=ileo_api.CONSUMPTION_URL, body=csv_text),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "secret")

    readings = await client.async_fetch_readings(date(2025, 3, 1), date(2025, 3, 31))

    assert readings == [ileo_api.IleoReading(date(2025, 3, 2), 180.0, 120180)]
    method, export_url, kwargs = session.calls[2]
    assert method == "GET"
    assert kwargs == {}
    parsed_url = urlparse(export_url)
    assert parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path == ileo_api.CONSUMPTION_URL
    assert "dateDebut=01%2F03%2F2025" in export_url
    assert "dateFin=31%2F03%2F2025" in export_url
    assert parse_qs(parsed_url.query) == {
        "ex": ["1"],
        "dateDebut": ["01/03/2025"],
        "dateFin": ["31/03/2025"],
    }


def test_parse_readings_csv_filters_zero_and_missing_values() -> None:
    """Only rows with positive consumption and complete values are returned."""
    csv_text = (FIXTURES_DIR / "ileo_export.csv").read_text(encoding="utf-8")

    readings = parse_readings_csv(csv_text)

    assert [reading.date for reading in readings] == [
        date(2025, 3, 2),
        date(2025, 3, 3),
        date(2025, 3, 5),
    ]
    assert readings[0].litres == 180.0
    assert readings[0].index_litres == 120180


def test_parse_readings_csv_sorts_readings_by_date() -> None:
    """Readings are returned chronologically even when CSV rows are not."""
    csv_text = (
        "date;consommation (litres);index\n"
        "05/03/2025;90;120515\n"
        "02/03/2025;180;120180\n"
    )

    readings = parse_readings_csv(csv_text)

    assert [reading.date for reading in readings] == [
        date(2025, 3, 2),
        date(2025, 3, 5),
    ]


def test_parse_readings_csv_raises_for_missing_required_columns() -> None:
    """A CSV export without every required column is rejected."""
    csv_text = "date;consommation (litres)\n02/03/2025;180\n"

    with pytest.raises(IleoCsvError):
        parse_readings_csv(csv_text)


def test_parse_readings_csv_normalizes_required_headers() -> None:
    """Required CSV headers tolerate BOM, casing, and surrounding spaces."""
    csv_text = "\ufeffDate; Consommation (litres) ;INDEX\n02/03/2025;180;120180\n"

    readings = parse_readings_csv(csv_text)

    assert readings[0].date == date(2025, 3, 2)
    assert readings[0].litres == 180.0
    assert readings[0].index_litres == 120180


def test_parse_readings_csv_accepts_space_thousands_separators() -> None:
    """Numeric fields tolerate regular and non-breaking thousands separators."""
    csv_text = "date;consommation (litres);index\n02/03/2025;1 234,5;120\u00a0180\n"

    readings = parse_readings_csv(csv_text)

    assert readings[0].litres == 1234.5
    assert readings[0].index_litres == 120180
