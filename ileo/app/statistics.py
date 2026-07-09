"""Build Home Assistant water sensor states and long-term statistics payloads."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .ileo_client import DEFAULT_METER_ID, IleoReading

WATER_ENTITY_ID = "sensor.ileo_water_index"
WATER_SOURCE = "recorder"
WATER_NAME = "ILEO water index"
WATER_UNIT = "L"
WATER_UNIT_CLASS = "volume"
WATER_TIME_ZONE = ZoneInfo("Europe/Paris")


def meter_entity_id(meter_id: str) -> str:
    """Build the Home Assistant entity id for a meter."""
    if meter_id == DEFAULT_METER_ID:
        return WATER_ENTITY_ID
    return f"{WATER_ENTITY_ID}_{_slugify(meter_id)}"


def meter_name(meter_label: str | None) -> str:
    """Build a friendly name for a meter."""
    if meter_label:
        return f"ILEO eau - {meter_label}"
    return WATER_NAME


def latest_state(
    readings: list[IleoReading],
    *,
    meter_id: str = DEFAULT_METER_ID,
    meter_label: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build the current entity state from the latest reading."""
    if not readings:
        raise ValueError("At least one reading is required")

    latest = max(readings, key=lambda reading: reading.date)
    return str(latest.index_litres), {
        **_base_attributes(meter_id, meter_label),
        "device_class": "water",
        "state_class": "total_increasing",
        "unit_of_measurement": WATER_UNIT,
        "last_reading_date": latest.date.isoformat(),
        "last_daily_litres": latest.litres,
    }


def empty_meter_state(
    meter_id: str,
    meter_label: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build a visible numeric Home Assistant state for a meter without readings yet."""
    return "0", {
        **_base_attributes(meter_id, meter_label),
        "device_class": "water",
        "state_class": "total_increasing",
        "unit_of_measurement": WATER_UNIT,
        "assumed_zero": True,
        "last_reading_date": None,
        "last_daily_litres": None,
    }


def import_statistics_payload(
    readings: list[IleoReading],
    *,
    meter_id: str = DEFAULT_METER_ID,
    meter_label: str | None = None,
    start_date: date,
    previous_imported_date: str | None = None,
    previous_sum_litres: float = 0.0,
) -> tuple[dict[str, Any] | None, int, str | None, float]:
    """Build a Recorder statistics import payload and updated import marker."""
    ordered_readings = sorted(readings, key=lambda reading: reading.date)
    if not ordered_readings:
        return None, 0, previous_imported_date, previous_sum_litres

    latest_reading_date = ordered_readings[-1].date.isoformat()
    imported_readings = [
        reading
        for reading in ordered_readings
        if previous_imported_date is None
        or reading.date.isoformat() > previous_imported_date
    ]
    if not imported_readings:
        return None, 0, previous_imported_date, previous_sum_litres

    running_sum = previous_sum_litres
    stats: list[dict[str, Any]] = []
    if previous_imported_date is None:
        first_reading = imported_readings[0]
        stats.append(
            {
                "start": _stat_start(start_date),
                "state": first_reading.index_litres - first_reading.litres,
                "sum": 0.0,
            }
        )

    for reading in imported_readings:
        running_sum += reading.litres
        stats.append(
            {
                "start": _stat_start(reading.date + timedelta(days=1)),
                "state": reading.index_litres,
                "sum": running_sum,
            }
        )

    payload = {
        "metadata": {
            "has_mean": False,
            "has_sum": True,
            "mean_type": "none",
            "name": meter_name(meter_label),
            "source": WATER_SOURCE,
            "statistic_id": meter_entity_id(meter_id),
            "unit_class": WATER_UNIT_CLASS,
            "unit_of_measurement": WATER_UNIT,
        },
        "stats": stats,
    }
    return payload, len(imported_readings), latest_reading_date, running_sum


def _base_attributes(meter_id: str, meter_label: str | None) -> dict[str, Any]:
    return {
        "friendly_name": meter_name(meter_label),
        "meter_id": meter_id,
    }


def _stat_start(value: date) -> str:
    return datetime.combine(value, time.min, WATER_TIME_ZONE).isoformat()


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
    return slug or "unknown"
