"""Sensors for the ILEO integration."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import IleoReading
from .const import DOMAIN
from .coordinator import IleoDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import IleoConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IleoConfigEntry,
    async_add_entities,
) -> None:
    """Set up ILEO sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            IleoWaterIndexSensor(coordinator),
            IleoLastConsumptionSensor(coordinator),
            IleoLastReadingDateSensor(coordinator),
        ]
    )


class IleoBaseSensor(CoordinatorEntity[IleoDataUpdateCoordinator], SensorEntity):
    """Base class for ILEO sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IleoDataUpdateCoordinator,
        suffix: str,
        name: str,
    ) -> None:
        """Initialize a coordinator-backed ILEO sensor."""
        super().__init__(coordinator)
        unique_root = (
            coordinator.config_entry.unique_id or coordinator.config_entry.entry_id
        )
        self._attr_unique_id = f"{unique_root}_{suffix}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_root)},
            manufacturer="ILEO",
            name="ILEO",
        )

    @property
    def latest_reading(self) -> IleoReading | None:
        """Return the latest coordinator reading."""
        if not self.coordinator.data:
            return None

        return self.coordinator.data[-1]


class IleoWaterIndexSensor(IleoBaseSensor):
    """Sensor for the current ILEO water index."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: IleoDataUpdateCoordinator) -> None:
        """Initialize the water index sensor."""
        super().__init__(coordinator, "water_index", "Water index")

    @property
    def native_value(self) -> int | None:
        """Return the latest meter index in litres."""
        latest = self.latest_reading
        return latest.index_litres if latest is not None else None


class IleoLastConsumptionSensor(IleoBaseSensor):
    """Sensor for the latest ILEO water consumption."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: IleoDataUpdateCoordinator) -> None:
        """Initialize the last consumption sensor."""
        super().__init__(coordinator, "last_consumption", "Last consumption")

    @property
    def native_value(self) -> float | None:
        """Return the latest consumption in litres."""
        latest = self.latest_reading
        return latest.litres if latest is not None else None


class IleoLastReadingDateSensor(IleoBaseSensor):
    """Sensor for the latest ILEO reading date."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: IleoDataUpdateCoordinator) -> None:
        """Initialize the last reading date sensor."""
        super().__init__(coordinator, "last_reading_date", "Last reading date")

    @property
    def native_value(self) -> date | None:
        """Return the latest reading date."""
        latest = self.latest_reading
        return latest.date if latest is not None else None
