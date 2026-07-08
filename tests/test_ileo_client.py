"""Tests for the ILEO client helpers."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "ileo"))

from app import ileo_client
from app.ileo_client import (
    IleoApiClient,
    IleoAuthError,
    IleoConnectionError,
    IleoCsvError,
    parse_meters_from_html,
    parse_readings_csv,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
    session = FakeSession(
        [
            FakeResponse(url=ileo_client.LOGIN_URL, body=LOGIN_HTML),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body="<html>mes consommations</html>"),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "secret")

    result = await client.async_validate_credentials()

    assert result is True
    assert session.calls[0] == ("GET", ileo_client.LOGIN_URL, {})
    method, url, kwargs = session.calls[1]
    assert method == "POST"
    assert url == ileo_client.LOGIN_URL
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
    session = FakeSession(
        [
            FakeResponse(
                url=ileo_client.LOGIN_URL,
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
    session = FakeSession(
        [
            FakeResponse(
                url=ileo_client.LOGIN_URL,
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
        (ileo_client.LOGIN_URL, "<html>mes consommations</html>"),
        (ileo_client.CONSUMPTION_URL, "<button>Je me connecte</button>"),
    ],
)
async def test_async_validate_credentials_raises_when_login_page_remains(
    final_url: str, body: str
) -> None:
    session = FakeSession(
        [
            FakeResponse(url=ileo_client.LOGIN_URL, body=LOGIN_HTML),
            FakeResponse(url=final_url, body=body),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "wrong")

    with pytest.raises(IleoAuthError):
        await client.async_validate_credentials()


@pytest.mark.asyncio
async def test_async_fetch_readings_validates_session_and_downloads_csv_export() -> None:
    csv_text = "date;consommation (litres);index\n02/03/2025;180;120180\n"
    session = FakeSession(
        [
            FakeResponse(url=ileo_client.LOGIN_URL, body=LOGIN_HTML),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body="<html>mes consommations</html>"),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body="<html>no contract menu</html>"),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body=csv_text),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "secret")

    readings = await client.async_fetch_readings(date(2025, 3, 1), date(2025, 3, 31))

    assert readings == [ileo_client.IleoReading(date(2025, 3, 2), 180.0, 120180)]
    method, export_url, kwargs = session.calls[3]
    assert method == "GET"
    assert kwargs == {}
    parsed_url = urlparse(export_url)
    assert parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path == ileo_client.CONSUMPTION_URL
    assert "dateDebut=01%2F03%2F2025" in export_url
    assert "dateFin=31%2F03%2F2025" in export_url
    assert parse_qs(parsed_url.query) == {
        "ex": ["1"],
        "dateDebut": ["01/03/2025"],
        "dateFin": ["31/03/2025"],
    }


@pytest.mark.asyncio
async def test_async_fetch_meter_readings_switches_each_detected_contract() -> None:
    first_csv = "date;consommation (litres);index\n2026-06-28;180;120180\n"
    second_csv = "date;consommation (litres);index\n"
    consumption_html = """
    <a href="javascript:">Contrat n°4052059</a>
    <a href="?switchAbt=4147436">Contrat n°4147436</a>
    """
    session = FakeSession(
        [
            FakeResponse(url=ileo_client.LOGIN_URL, body=LOGIN_HTML),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body="<html>mes consommations</html>"),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body=consumption_html),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body=first_csv),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body="<html>switched</html>"),
            FakeResponse(url=ileo_client.CONSUMPTION_URL, body=second_csv),
        ]
    )
    client = IleoApiClient(session, "user@example.test", "secret")

    result = await client.async_fetch_meter_readings(date(2026, 1, 1), date(2026, 7, 8))

    assert [item.meter.meter_id for item in result] == ["4052059", "4147436"]
    assert result[0].readings == [
        ileo_client.IleoReading(date(2026, 6, 28), 180.0, 120180, meter_id="4052059")
    ]
    assert result[1].readings == []
    assert any("switchAbt=4147436" in call[1] for call in session.calls)


def test_parse_meters_from_html_extracts_contract_menu_links() -> None:
    html = """
    <a href="javascript:">Contrat n°4052059</a>
    <a href="?switchAbt=4147436">Contrat n°4147436</a>
    <a href="attacher-contrat.aspx">Attacher un nouveau contrat</a>
    """

    meters = parse_meters_from_html(html)

    assert meters == [
        ileo_client.IleoMeter("4052059", "Contrat 4052059", None),
        ileo_client.IleoMeter("4147436", "Contrat 4147436", "4147436"),
    ]


def test_parse_readings_csv_filters_zero_and_missing_values() -> None:
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


def test_parse_readings_csv_accepts_iso_dates_from_current_ileo_export() -> None:
    csv_text = "date;consommation (litres);index\n2026-06-28;180;120180\n"

    readings = parse_readings_csv(csv_text)

    assert readings[0].date == date(2026, 6, 28)


def test_parse_readings_csv_assigns_default_meter_id() -> None:
    csv_text = "date;consommation (litres);index\n02/03/2025;180;120180\n"

    readings = parse_readings_csv(csv_text)

    assert readings[0].meter_id == "default"


def test_parse_readings_csv_assigns_requested_meter_id() -> None:
    csv_text = "date;consommation (litres);index\n02/03/2025;180;120180\n"

    readings = parse_readings_csv(csv_text, meter_id="4052059")

    assert readings[0].meter_id == "4052059"


def test_parse_readings_csv_raises_for_missing_required_columns() -> None:
    csv_text = "date;consommation (litres)\n02/03/2025;180\n"

    with pytest.raises(IleoCsvError):
        parse_readings_csv(csv_text)


def test_parse_readings_csv_normalizes_required_headers() -> None:
    csv_text = "\ufeffDate; Consommation (litres) ;INDEX\n02/03/2025;180;120180\n"

    readings = parse_readings_csv(csv_text)

    assert readings[0].date == date(2025, 3, 2)
    assert readings[0].litres == 180.0
    assert readings[0].index_litres == 120180


def test_parse_readings_csv_accepts_space_thousands_separators() -> None:
    csv_text = "date;consommation (litres);index\n02/03/2025;1 234,5;120\u00a0180\n"

    readings = parse_readings_csv(csv_text)

    assert readings[0].litres == 1234.5
    assert readings[0].index_litres == 120180
