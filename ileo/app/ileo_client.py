"""Async client and CSV parser for ILEO private consumption exports."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from io import StringIO
import re
from urllib.parse import urlencode

BASE_URL = "https://www.mel-ileo.fr"
LOGIN_URL = f"{BASE_URL}/connexion.aspx"
CONSUMPTION_URL = f"{BASE_URL}/espaceperso/mes-consommations.aspx"

DEFAULT_METER_ID = "default"
REQUIRED_COLUMNS = {"date", "consommation (litres)", "index"}
LOGIN_FORM_MARKERS = ("je me connecte",)


class IleoError(Exception):
    """Base exception for ILEO errors."""


class IleoAuthError(IleoError):
    """Raised when ILEO authentication fails."""


class IleoConnectionError(IleoError):
    """Raised when ILEO cannot be reached."""


class IleoCsvError(IleoError):
    """Raised when an ILEO CSV export cannot be parsed."""


@dataclass(frozen=True, slots=True)
class IleoMeter:
    """ILEO water meter or contract exposed by an account."""

    meter_id: str
    name: str
    switch_id: str | None = None


@dataclass(frozen=True, slots=True)
class IleoReading:
    """Daily ILEO water consumption reading."""

    date: date
    litres: float
    index_litres: int
    meter_id: str = DEFAULT_METER_ID


@dataclass(frozen=True, slots=True)
class IleoMeterReadings:
    """Readings attached to a single ILEO meter."""

    meter: IleoMeter
    readings: list[IleoReading]


class IleoApiClient:
    """Async HTTP client for the ILEO private consumption pages."""

    def __init__(self, session, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def async_validate_credentials(self) -> bool:
        """Validate configured credentials against the ILEO login page."""
        await self._async_login()
        return True

    async def async_fetch_readings(
        self, start_date: date, end_date: date
    ) -> list[IleoReading]:
        """Fetch and parse all consumption readings for the requested date range."""
        meter_readings = await self.async_fetch_meter_readings(start_date, end_date)
        readings: list[IleoReading] = []
        for item in meter_readings:
            readings.extend(item.readings)
        return sorted(readings, key=lambda reading: (reading.meter_id, reading.date))

    async def async_fetch_meter_readings(
        self, start_date: date, end_date: date
    ) -> list[IleoMeterReadings]:
        """Fetch readings grouped by detected ILEO meter or contract."""
        await self._async_login()

        async with self._session.get(CONSUMPTION_URL) as response:
            if response.status >= 400:
                raise IleoConnectionError("Unable to load ILEO consumption page")
            consumption_html = await response.text()

        meters = parse_meters_from_html(consumption_html)
        if not meters:
            meters = [IleoMeter(DEFAULT_METER_ID, "ILEO")]

        has_explicit_meter_ids = len(meters) > 1
        results: list[IleoMeterReadings] = []
        for meter in meters:
            effective_meter = meter
            if not has_explicit_meter_ids:
                effective_meter = IleoMeter(DEFAULT_METER_ID, meter.name, meter.switch_id)

            if meter.switch_id is not None:
                switch_url = f"{CONSUMPTION_URL}?{urlencode({'switchAbt': meter.switch_id})}"
                async with self._session.get(switch_url) as response:
                    if response.status >= 400:
                        raise IleoConnectionError(f"Unable to switch ILEO contract {meter.meter_id}")
                    await response.text()

            csv_text = await self._async_download_csv(start_date, end_date)
            readings = parse_readings_csv(csv_text, meter_id=effective_meter.meter_id)
            results.append(IleoMeterReadings(effective_meter, readings))

        return results

    async def _async_login(self) -> None:
        async with self._session.get(LOGIN_URL) as response:
            if response.status >= 400:
                raise IleoConnectionError("Unable to load ILEO login page")
            login_html = await response.text()

        if not _has_login_form_shape(login_html):
            raise IleoConnectionError("ILEO login page did not contain the expected form")

        payload = self._build_login_payload(login_html)
        async with self._session.post(LOGIN_URL, data=payload) as response:
            if response.status >= 400:
                raise IleoConnectionError("Unable to authenticate with ILEO")
            final_url = str(response.url).lower()
            body = await response.text()

        if "connexion.aspx" in final_url or "je me connecte" in body.lower():
            raise IleoAuthError("Invalid ILEO credentials")

    async def _async_download_csv(self, start_date: date, end_date: date) -> str:
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
            return await response.text()

    def _build_login_payload(self, login_html: str) -> dict[str, str]:
        """Build the login form payload, preserving ASP.NET hidden fields."""
        payload = _extract_hidden_inputs(login_html)
        payload["email"] = self._username
        payload["password"] = self._password
        return payload


def parse_readings_csv(
    csv_text: str, *, meter_id: str = DEFAULT_METER_ID
) -> list[IleoReading]:
    """Parse an ILEO CSV export into chronological positive readings."""
    if _looks_like_empty_export(csv_text):
        return []

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
                meter_id=meter_id,
            )
        )

    return sorted(readings, key=lambda reading: reading.date)


def parse_meters_from_html(html: str) -> list[IleoMeter]:
    """Parse ILEO contract links from an authenticated page."""
    parser = _LinkParser()
    parser.feed(html)

    meters: list[IleoMeter] = []
    seen: set[str] = set()
    for href, text in parser.links:
        match = re.search(r"contrat\s*n[°º�]?\s*(\d+)", text, re.IGNORECASE)
        if match is None:
            continue

        meter_id = match.group(1)
        if meter_id in seen:
            continue

        switch_match = re.search(r"switchAbt=(\d+)", href or "")
        switch_id = switch_match.group(1) if switch_match else None
        meters.append(IleoMeter(meter_id=meter_id, name=f"Contrat {meter_id}", switch_id=switch_id))
        seen.add(meter_id)

    return meters


def _parse_date(value: str, row_number: int) -> date:
    for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    raise IleoCsvError(f"Invalid date on CSV row {row_number}: {value}")


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


def _looks_like_empty_export(csv_text: str) -> bool:
    stripped = csv_text.strip()
    if not stripped:
        return True

    first_line = stripped.splitlines()[0].strip()
    return first_line.startswith("<") or ";" not in first_line


def _extract_hidden_inputs(html: str) -> dict[str, str]:
    parser = _InputParser()
    parser.feed(html)
    return parser.hidden_inputs


def _contains_login_form_marker(html: str) -> bool:
    normalized_html = html.lower()
    return any(marker in normalized_html for marker in LOGIN_FORM_MARKERS)


def _has_login_form_shape(html: str) -> bool:
    parser = _InputParser()
    parser.feed(html)
    return parser.has_credentials_inputs or _contains_login_form_marker(html)


class _InputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_inputs: dict[str, str] = {}
        self._input_names: set[str] = set()
        self._input_ids: set[str] = set()

    @property
    def has_credentials_inputs(self) -> bool:
        identifiers = self._input_names | self._input_ids
        return "email" in identifiers and "password" in identifiers

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return

        attributes = {key.lower(): value for key, value in attrs}
        name = attributes.get("name")
        input_id = attributes.get("id")

        if name is not None:
            self._input_names.add(name.lower())
        if input_id is not None:
            self._input_ids.add(input_id.lower())

        if name is not None and (attributes.get("type") or "").lower() == "hidden":
            self.hidden_inputs[name] = attributes.get("value") or ""


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attributes = {key.lower(): value for key, value in attrs}
        self._href = attributes.get("href") or ""
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        text = " ".join(part.strip() for part in self._text if part.strip())
        text = re.sub(r"\s+", " ", text).strip()
        self.links.append((self._href, text))
        self._href = None
        self._text = []
