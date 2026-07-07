"""Build Home Assistant water sensor states and long-term statistics payloads."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any

from .ileo_client import IleoReading

WATER_ENTITY_ID = "sensor.ileo_water_index"
WATER_STATISTIC_ID = WATER_ENTITY_ID
WATER_SOURCE = "ileo"
WATER_NAME = "ILEO water index"
WATER_UNIT = "L"


def latest_state(readings: list[IleoReading]) -> tuple[str, dict[str, Any]]:
    """Build the current entity state from the latest reading."""
    if not readings:
        raise ValueError("At least one reading is required")

    latest = max(readings, key=lambda reading: reading.date)
    return str(latest.index_litres), {
        "friendly_name": WATER_NAME,
        "device_class": "water",
        "state_class": "total_increasing",
        "unit_of_measurement": WATER_UNIT,
        "last_reading_date": latest.date.isoformat(),
        "last_daily_litres": latest.litres,
    }


def import_statistics_payload(readings: list[IleoReading]) -> dict[str, Any]:
    """Build a recorder.import_statistics payload for water index history."""
    sorted_readings = sorted(readings, key=lambda reading: reading.date)
    return {
        "metadata": {
            "has_mean": False,
            "has_sum": True,
            "name": WATER_NAME,
            "source": WATER_SOURCE,
            "statistic_id": WATER_STATISTIC_ID,
            "unit_of_measurement": WATER_UNIT,
        },
        "stats": [
            {
                "start": _reading_start(reading),
                "state": reading.index_litres,
                "sum": reading.index_litres,
            }
            for reading in sorted_readings
        ],
    }


def filter_after_last_sync(
    readings: list[IleoReading], last_imported_date: str | None
) -> list[IleoReading]:
    """Keep readings newer than the persisted import marker."""
    if not last_imported_date:
        return sorted(readings, key=lambda reading: reading.date)

    return sorted(
        [
            reading
            for reading in readings
            if reading.date.isoformat() > last_imported_date
        ],
        key=lambda reading: reading.date,
    )


def _reading_start(reading: IleoReading) -> str:
    start = datetime.combine(reading.date, time.min, tzinfo=timezone.utc)
    return start.isoformat()

