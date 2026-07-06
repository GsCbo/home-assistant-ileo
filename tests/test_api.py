"""Tests for the ILEO API helpers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

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
parse_readings_csv = ileo_api.parse_readings_csv


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
