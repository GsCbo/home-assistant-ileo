"""API helpers for the ILEO integration."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from io import StringIO
from urllib.parse import urlencode

if __package__:
    from .const import CONSUMPTION_URL, LOGIN_URL
else:
    BASE_URL = "https://www.mel-ileo.fr"
    LOGIN_URL = f"{BASE_URL}/connexion.aspx"
    CONSUMPTION_URL = f"{BASE_URL}/espaceperso/mes-consommations.aspx"


class IleoError(Exception):
    """Base exception for ILEO errors."""


class IleoAuthError(IleoError):
    """Raised when ILEO authentication fails."""


class IleoConnectionError(IleoError):
    """Raised when ILEO cannot be reached."""


class IleoCsvError(IleoError):
    """Raised when an ILEO CSV export cannot be parsed."""


@dataclass(frozen=True, slots=True)
class IleoReading:
    """Daily ILEO water consumption reading."""

    date: date
    litres: float
    index_litres: int


REQUIRED_COLUMNS = {"date", "consommation (litres)", "index"}
LOGIN_FORM_MARKERS = ("je me connecte",)


class IleoApiClient:
    """Async HTTP client for the ILEO private consumption pages."""

    def __init__(self, session, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def async_validate_credentials(self) -> bool:
        """Validate configured credentials against the ILEO login page."""
        async with self._session.get(LOGIN_URL) as response:
            if response.status >= 400:
                raise IleoConnectionError("Unable to load ILEO login page")
            login_html = await response.text()

        payload = self._build_login_payload(login_html)
        if len(payload) == 2 and not _contains_login_form_marker(login_html):
            raise IleoConnectionError("ILEO login page did not contain the expected form")

        async with self._session.post(LOGIN_URL, data=payload) as response:
            if response.status >= 400:
                raise IleoConnectionError("Unable to authenticate with ILEO")
            final_url = str(response.url).lower()
            body = await response.text()

        if "connexion.aspx" in final_url or "je me connecte" in body.lower():
            raise IleoAuthError("Invalid ILEO credentials")

        return True

    async def async_fetch_readings(
        self, start_date: date, end_date: date
    ) -> list[IleoReading]:
        """Fetch and parse consumption readings for the requested date range."""
        await self.async_validate_credentials()

        query = urlencode(
            {
                "ex": "1",
                "dateDebut": start_date.strftime("%d/%m/%Y"),
                "dateFin": end_date.strftime("%d/%m/%Y"),
            }
        )
        export_url = f"{CONSUMPTION_URL}?{query}"
        async with self._session.get(export_url) as response:
            if response.status >= 400:
                raise IleoConnectionError("Unable to download ILEO consumption export")
            csv_text = await response.text()

        return parse_readings_csv(csv_text)

    def _build_login_payload(self, login_html: str) -> dict[str, str]:
        """Build the login form payload, preserving ASP.NET hidden fields."""
        payload = _extract_hidden_inputs(login_html)
        payload["email"] = self._username
        payload["password"] = self._password
        return payload


def parse_readings_csv(csv_text: str) -> list[IleoReading]:
    """Parse an ILEO CSV export into chronological positive readings."""
    reader = csv.DictReader(StringIO(csv_text), delimiter=";")
    columns = {_normalize_header(fieldname): fieldname for fieldname in reader.fieldnames or []}
    missing_columns = REQUIRED_COLUMNS - set(columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise IleoCsvError(f"Missing required CSV columns: {missing}")

    readings: list[IleoReading] = []
    for row_number, row in enumerate(reader, start=2):
        raw_date = (row[columns["date"]] or "").strip()
        raw_litres = (row[columns["consommation (litres)"]] or "").strip()
        raw_index = (row[columns["index"]] or "").strip()

        if not raw_date or not raw_litres or not raw_index:
            continue

        reading_date = _parse_date(raw_date, row_number)
        litres = _parse_litres(raw_litres, row_number)
        index_litres = _parse_index(raw_index, row_number)

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


def _parse_date(value: str, row_number: int) -> date:
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as err:
        raise IleoCsvError(f"Invalid date on CSV row {row_number}: {value}") from err


def _parse_litres(value: str, row_number: int) -> float:
    try:
        return float(_normalize_number(value))
    except ValueError as err:
        raise IleoCsvError(f"Invalid litres on CSV row {row_number}: {value}") from err


def _parse_index(value: str, row_number: int) -> int:
    try:
        index_value = float(_normalize_number(value))
    except ValueError as err:
        raise IleoCsvError(f"Invalid index on CSV row {row_number}: {value}") from err

    if not index_value.is_integer():
        raise IleoCsvError(f"Invalid index on CSV row {row_number}: {value}")

    return int(index_value)


def _normalize_header(value: str) -> str:
    return value.lstrip("\ufeff").strip().lower()


def _normalize_number(value: str) -> str:
    return value.replace(" ", "").replace("\u00a0", "").replace(",", ".")


def _extract_input_value(html: str, name: str) -> str | None:
    """Extract a named input's value from an HTML form."""
    parser = _InputParser()
    parser.feed(html)
    return parser.input_values.get(name)


def _extract_hidden_inputs(html: str) -> dict[str, str]:
    """Extract all hidden input values from an HTML form."""
    parser = _InputParser()
    parser.feed(html)
    return parser.hidden_inputs


def _contains_login_form_marker(html: str) -> bool:
    normalized_html = html.lower()
    return any(marker in normalized_html for marker in LOGIN_FORM_MARKERS)


class _InputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_inputs: dict[str, str] = {}
        self.input_values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return

        attributes = {key.lower(): value for key, value in attrs}
        name = attributes.get("name")
        if name is None:
            return

        value = attributes.get("value") or ""
        self.input_values[name] = value
        if (attributes.get("type") or "").lower() == "hidden":
            self.hidden_inputs[name] = value
