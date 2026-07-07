"""Tests for Home Assistant statistics payload generation."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "ileo"))

from app.ileo_client import IleoReading
from app.statistics import (
    WATER_ENTITY_ID,
    filter_after_last_sync,
    import_statistics_payload,
    latest_state,
)


def test_latest_state_uses_latest_reading_with_energy_metadata() -> None:
    state, attributes = latest_state(
        [
            IleoReading(date(2025, 3, 1), 120.0, 120000),
            IleoReading(date(2025, 3, 2), 180.0, 120180),
        ]
    )

    assert WATER_ENTITY_ID == "sensor.ileo_water_index"
    assert state == "120180"
    assert attributes["device_class"] == "water"
    assert attributes["state_class"] == "total_increasing"
    assert attributes["unit_of_measurement"] == "L"
    assert attributes["last_reading_date"] == "2025-03-02"
    assert attributes["last_daily_litres"] == 180.0


def test_import_statistics_payload_is_sorted_and_uses_water_metadata() -> None:
    payload = import_statistics_payload(
        [
            IleoReading(date(2025, 3, 2), 180.0, 120180),
            IleoReading(date(2025, 3, 1), 120.0, 120000),
        ]
    )

    assert payload["metadata"] == {
        "has_mean": False,
        "has_sum": True,
        "name": "ILEO water index",
        "source": "ileo",
        "statistic_id": "sensor.ileo_water_index",
        "unit_of_measurement": "L",
    }
    assert payload["stats"] == [
        {
            "start": "2025-03-01T00:00:00+00:00",
            "state": 120000,
            "sum": 120000,
        },
        {
            "start": "2025-03-02T00:00:00+00:00",
            "state": 120180,
            "sum": 120180,
        },
    ]


def test_filter_after_last_sync_keeps_only_new_dates() -> None:
    readings = [
        IleoReading(date(2025, 3, 1), 120.0, 120000),
        IleoReading(date(2025, 3, 2), 180.0, 120180),
        IleoReading(date(2025, 3, 3), 90.0, 120270),
    ]

    filtered = filter_after_last_sync(readings, "2025-03-02")

    assert filtered == [IleoReading(date(2025, 3, 3), 90.0, 120270)]

