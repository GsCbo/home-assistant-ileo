"""API helpers for the ILEO integration."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO


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
