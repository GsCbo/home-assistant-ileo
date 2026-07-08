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
    latest_state,
    meter_entity_id,
)


def test_meter_entity_id_keeps_single_meter_compatibility() -> None:
    assert meter_entity_id("default") == "sensor.ileo_water_index"


def test_meter_entity_id_slugs_explicit_meter_id() -> None:
    assert meter_entity_id("Contrat 12 Rue de Lille") == (
        "sensor.ileo_water_index_contrat_12_rue_de_lille"
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
    assert attributes["meter_id"] == "default"


def test_latest_state_uses_meter_specific_name() -> None:
    state, attributes = latest_state(
        [IleoReading(date(2025, 3, 2), 180.0, 120180, meter_id="4052059")],
        meter_id="4052059",
        meter_label="Contrat 4052059",
    )

    assert state == "120180"
    assert attributes["friendly_name"] == "ILEO eau - Contrat 4052059"
    assert attributes["meter_id"] == "4052059"


def test_empty_meter_state_exposes_zero_water_entity() -> None:
    state, attributes = empty_meter_state("4147436", "Contrat 4147436")

    assert state == "0"
    assert attributes["friendly_name"] == "ILEO eau - Contrat 4147436"
    assert attributes["device_class"] == "water"
    assert attributes["state_class"] == "total_increasing"
    assert attributes["unit_of_measurement"] == "L"
    assert attributes["assumed_zero"] is True
    assert attributes["meter_id"] == "4147436"
    assert attributes["last_reading_date"] is None
