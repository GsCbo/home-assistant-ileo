"""Tests for the ILEO sensor platform."""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock

import pytest

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume

from custom_components.ileo.api import IleoReading
from custom_components.ileo.sensor import async_setup_entry


def _entry_with_data(readings: list[IleoReading]) -> Mock:
    coordinator = Mock()
    coordinator.data = readings
    coordinator.config_entry = Mock(unique_id="user@example.com", entry_id="entry-123")

    return Mock(
        entry_id="entry-123",
        unique_id="user@example.com",
        runtime_data=coordinator,
    )


async def _setup_entities(entry: Mock) -> list:
    entities = []

    def async_add_entities(new_entities):
        entities.extend(new_entities)

    await async_setup_entry(Mock(), entry, async_add_entities)
    return entities


@pytest.mark.asyncio
async def test_water_index_sensor_uses_latest_index_and_energy_metadata() -> None:
    """The water index sensor exposes a total increasing litre meter."""
    entry = _entry_with_data(
        [
            IleoReading(date=date(2026, 7, 4), litres=50.5, index_litres=123400),
            IleoReading(date=date(2026, 7, 5), litres=42.0, index_litres=123442),
        ]
    )

    water_index, _, _ = await _setup_entities(entry)

    assert water_index.native_value == 123442
    assert water_index.native_unit_of_measurement == UnitOfVolume.LITERS
    assert water_index.device_class == SensorDeviceClass.WATER
    assert water_index.state_class == SensorStateClass.TOTAL_INCREASING
    assert water_index.unique_id == "user@example.com_water_index"


@pytest.mark.asyncio
async def test_last_consumption_sensor_uses_latest_litres_and_measurement_metadata() -> None:
    """The last consumption sensor exposes the most recent daily consumption."""
    entry = _entry_with_data(
        [IleoReading(date=date(2026, 7, 5), litres=42.0, index_litres=123442)]
    )

    _, last_consumption, _ = await _setup_entities(entry)

    assert last_consumption.native_value == 42.0
    assert last_consumption.native_unit_of_measurement == UnitOfVolume.LITERS
    assert last_consumption.device_class == SensorDeviceClass.WATER
    assert last_consumption.state_class == SensorStateClass.MEASUREMENT


@pytest.mark.asyncio
async def test_last_reading_date_sensor_uses_latest_date() -> None:
    """The last reading date sensor exposes the latest reading date."""
    entry = _entry_with_data(
        [IleoReading(date=date(2026, 7, 5), litres=42.0, index_litres=123442)]
    )

    _, _, last_reading_date = await _setup_entities(entry)

    assert last_reading_date.native_value == date(2026, 7, 5)
    assert last_reading_date.device_class == SensorDeviceClass.DATE


@pytest.mark.asyncio
async def test_empty_coordinator_data_returns_none_native_values() -> None:
    """All sensors are unknown when the coordinator has no readings."""
    entities = await _setup_entities(_entry_with_data([]))

    assert [entity.native_value for entity in entities] == [None, None, None]
