"""Build Home Assistant water sensor states and long-term statistics payloads."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .ileo_client import DEFAULT_METER_ID, IleoReading

WATER_STATISTIC_ID = "ileo:water_index"
WATER_SOURCE = "ileo"
WATER_NAME = "ILEO water index"
WATER_UNIT = "L"
WATER_UNIT_CLASS = "volume"
WATER_TIME_ZONE = ZoneInfo("Europe/Paris")
STATISTIC_MEAN_TYPE_NONE = 0


def meter_statistic_id(meter_id: str) -> str:
    """Build the external Recorder statistic id for a meter."""
    if meter_id == DEFAULT_METER_ID:
        return WATER_STATISTIC_ID
    return f"{WATER_STATISTIC_ID}_{_slugify(meter_id)}"


def meter_name(meter_label: str | None) -> str:
    """Build a friendly name for a meter."""
    if meter_label:
        return f"ILEO eau - {meter_label}"
    return WATER_NAME


def import_statistics_payload(
    readings: list[IleoReading],
    *,
    meter_id: str = DEFAULT_METER_ID,
    meter_label: str | None = None,
    start_date: date,
    previous_imported_date: str | None = None,
    previous_sum_litres: float = 0.0,
    previous_bridge_until_date: str | None = None,
    bridge_until: date | None = None,
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

    latest_known_reading = (
        imported_readings[-1] if imported_readings else ordered_readings[-1]
    )
    if bridge_until is not None:
        bridge_start = _bridge_start_date(
            latest_known_reading.date,
            previous_bridge_until_date,
            has_imported_readings=bool(imported_readings),
        )
        while bridge_start <= bridge_until:
            stats.append(
                {
                    "start": _stat_start(bridge_start),
                    "state": latest_known_reading.index_litres,
                    "sum": running_sum,
                }
            )
            bridge_start += timedelta(days=1)

    if not stats:
        return None, 0, previous_imported_date, previous_sum_litres

    payload = {
        "metadata": {
            "has_mean": False,
            "has_sum": True,
            "mean_type": STATISTIC_MEAN_TYPE_NONE,
            "name": meter_name(meter_label),
            "source": WATER_SOURCE,
            "statistic_id": meter_statistic_id(meter_id),
            "unit_class": WATER_UNIT_CLASS,
            "unit_of_measurement": WATER_UNIT,
        },
        "stats": stats,
    }
    return payload, len(imported_readings), latest_reading_date, running_sum


def _stat_start(value: date) -> str:
    return datetime.combine(value, time.min, WATER_TIME_ZONE).isoformat()


def _bridge_start_date(
    latest_reading_date: date,
    previous_bridge_until_date: str | None,
    *,
    has_imported_readings: bool,
) -> date:
    if previous_bridge_until_date and not has_imported_readings:
        return date.fromisoformat(previous_bridge_until_date) + timedelta(days=1)
    return latest_reading_date + timedelta(days=2)


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
    return slug or "unknown"
