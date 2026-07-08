"""Build Home Assistant water sensor states and long-term statistics payloads."""

from __future__ import annotations

from datetime import datetime, time, timezone
import re
import unicodedata
from typing import Any

from .ileo_client import DEFAULT_METER_ID, IleoReading

WATER_ENTITY_ID = "sensor.ileo_water_index"
WATER_SOURCE = "ileo"
WATER_NAME = "ILEO water index"
WATER_UNIT = "L"


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
    """Build a visible Home Assistant state for a meter without readings yet."""
    return "unknown", {
        **_base_attributes(meter_id, meter_label),
        "device_class": "water",
        "state_class": "total_increasing",
        "unit_of_measurement": WATER_UNIT,
        "last_reading_date": None,
        "last_daily_litres": None,
    }


def import_statistics_payload(
    readings: list[IleoReading],
    meter_id: str = DEFAULT_METER_ID,
    meter_label: str | None = None,
) -> dict[str, Any]:
    """Build a recorder.import_statistics payload for water index history."""
    sorted_readings = sorted(readings, key=lambda reading: reading.date)
    return {
        "metadata": {
            "has_mean": False,
            "has_sum": True,
            "name": meter_name(meter_label),
            "source": WATER_SOURCE,
            "statistic_id": meter_entity_id(meter_id),
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


def _base_attributes(meter_id: str, meter_label: str | None) -> dict[str, Any]:
    return {
        "friendly_name": meter_name(meter_label),
        "meter_id": meter_id,
    }


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
    return slug or "unknown"
