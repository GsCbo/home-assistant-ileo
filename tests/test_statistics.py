"""Tests for Home Assistant statistics payload generation."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "ileo"))

from app.ileo_client import IleoReading
from app.statistics import (
    WATER_ENTITY_ID,
    empty_meter_state,
    import_statistics_payload,
    latest_state,
    meter_entity_id,
)


def test_meter_entity_id_keeps_single_meter_compatibility() -> None:
    assert meter_entity_id("default") == "sensor.ileo_water_index"


def test_meter_entity_id_slugs_explicit_meter_id() -> None:
    assert meter_entity_id("Contrat 12 Rue de Lille") == (
        "sensor.ileo_water_index_contrat_12_rue_de_lille"
    )


def test_latest_state_uses_latest_reading_without_recorder_state_class() -> None:
    state, attributes = latest_state(
        [
            IleoReading(date(2025, 3, 1), 120.0, 120000),
            IleoReading(date(2025, 3, 2), 180.0, 120180),
        ]
    )

    assert WATER_ENTITY_ID == "sensor.ileo_water_index"
    assert state == "120180"
    assert attributes["device_class"] == "water"
    assert "state_class" not in attributes
    assert attributes["unit_of_measurement"] == "L"
    assert attributes["last_reading_date"] == "2025-03-02"
    assert attributes["last_daily_litres"] == 180.0
    assert attributes["meter_id"] == "default"


def test_latest_state_uses_meter_specific_name() -> None:
    state, attributes = latest_state(
        [IleoReading(date(2025, 3, 2), 180.0, 120180, meter_id="1234567")],
        meter_id="1234567",
        meter_label="Contrat 1234567",
    )

    assert state == "120180"
    assert attributes["friendly_name"] == "ILEO eau - Contrat 1234567"
    assert attributes["meter_id"] == "1234567"


def test_empty_meter_state_exposes_zero_water_entity_without_recorder_state_class() -> None:
    state, attributes = empty_meter_state("7654321", "Contrat 7654321")

    assert state == "0"
    assert attributes["friendly_name"] == "ILEO eau - Contrat 7654321"
    assert attributes["device_class"] == "water"
    assert "state_class" not in attributes
    assert attributes["unit_of_measurement"] == "L"
    assert attributes["assumed_zero"] is True
    assert attributes["meter_id"] == "7654321"
    assert attributes["last_reading_date"] is None


def test_import_statistics_payload_carries_forward_sum_until_today() -> None:
    payload, imported_count, imported_date, running_sum = import_statistics_payload(
        [IleoReading(date(2026, 6, 28), 417.0, 582513)],
        meter_id="1234567",
        meter_label="Maison",
        start_date=date(2026, 1, 1),
        previous_imported_date="2026-06-28",
        previous_sum_litres=417.0,
        previous_bridge_until_date="2026-06-29",
        bridge_until=date(2026, 7, 2),
    )

    assert imported_count == 0
    assert imported_date == "2026-06-28"
    assert running_sum == 417.0
    assert payload is not None
    assert payload["stats"] == [
        {
            "start": "2026-06-30T00:00:00+02:00",
            "state": 582513,
            "sum": 417.0,
        },
        {
            "start": "2026-07-01T00:00:00+02:00",
            "state": 582513,
            "sum": 417.0,
        },
        {
            "start": "2026-07-02T00:00:00+02:00",
            "state": 582513,
            "sum": 417.0,
        },
    ]
