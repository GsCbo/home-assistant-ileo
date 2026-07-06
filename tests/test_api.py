"""Tests for the ILEO API helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from custom_components.ileo.api import IleoCsvError, parse_readings_csv

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
