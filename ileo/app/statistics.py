"""Build Home Assistant water sensor states and long-term statistics payloads."""

from __future__ import annotations

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
