"""Tests for the app synchronization runtime."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "ileo"))

from app.config import AppConfig
from app.ileo_client import IleoMeter, IleoMeterReadings, IleoReading
from app.main import (
    ERROR_RETRY_SECONDS,
    MAX_INITIAL_JITTER_SECONDS,
    calculate_error_retry_seconds,
    calculate_initial_jitter_seconds,
    calculate_sync_interval_seconds,
    get_or_create_installation_id,
    read_meter_sync_state,
    read_last_sync,
    sync_once,
    write_meter_sync_state,
    write_last_sync,
)
from app.statistics import WATER_ENTITY_ID, meter_entity_id


class FakeIleoClient:
    def __init__(
        self,
        readings: list[IleoReading] | None = None,
        meter_readings: list[IleoMeterReadings] | None = None,
    ) -> None:
        self.readings = readings
        self.meter_readings = meter_readings
        self.calls: list[tuple[date, date]] = []

    async def async_fetch_readings(
        self, start_date: date, end_date: date
    ) -> list[IleoReading]:
        self.calls.append((start_date, end_date))
        return self.readings or []

    async def async_fetch_meter_readings(
        self, start_date: date, end_date: date
    ) -> list[IleoMeterReadings]:
        self.calls.append((start_date, end_date))
        if self.meter_readings is not None:
            return self.meter_readings
        return [
            IleoMeterReadings(
                IleoMeter("default", "ILEO"),
                self.readings or [],
            )
        ]


class FakeHomeAssistantClient:
    def __init__(self) -> None:
        self.states: list[tuple[str, str | int | float, dict[str, Any]]] = []

    async def async_set_state(
        self,
        entity_id: str,
        state: str | int | float,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        self.states.append((entity_id, state, attributes))
        return {}


def _config(mode: str = "sync") -> AppConfig:
    return AppConfig(
        username="user@example.test",
        password="secret",
        start_date=date(2025, 3, 1),
        sync_interval_hours=4,
        mode=mode,
    )


@pytest.mark.asyncio
async def test_sync_once_publishes_state_statistics_and_marker(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    ileo_client = FakeIleoClient(
        [
            IleoReading(date(2025, 3, 1), 120.0, 120000),
            IleoReading(date(2025, 3, 2), 180.0, 120180),
        ]
    )
    ha_client = FakeHomeAssistantClient()

    result = await sync_once(
        _config(),
        ileo_client,
        ha_client,
        state_path=state_path,
        today=date(2025, 3, 31),
    )

    assert ileo_client.calls == [(date(2025, 3, 1), date(2025, 3, 31))]
    assert ha_client.states[0][0] == WATER_ENTITY_ID
    assert ha_client.states[0][1] == "120180"
    assert result.fetched_readings == 2
    assert result.imported_readings == 1
    assert read_last_sync(state_path)["meters"]["default"] == {
        "last_imported_date": "2025-03-02",
        "latest_index_litres": 120180,
    }


@pytest.mark.asyncio
async def test_sync_once_updates_marker_without_recorder_import_service(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    write_last_sync(
        state_path,
        {
            "installation_id": "stable-installation",
            "last_imported_date": "2025-03-01",
        },
    )
    ileo_client = FakeIleoClient(
        [
            IleoReading(date(2025, 3, 1), 120.0, 120000),
            IleoReading(date(2025, 3, 2), 180.0, 120180),
        ]
    )
    ha_client = FakeHomeAssistantClient()

    result = await sync_once(
        _config(),
        ileo_client,
        ha_client,
        state_path=state_path,
        today=date(2025, 3, 31),
    )

    assert result.imported_readings == 1
    assert read_last_sync(state_path)["installation_id"] == "stable-installation"
    assert read_last_sync(state_path)["meters"]["default"] == {
        "last_imported_date": "2025-03-02",
        "latest_index_litres": 120180,
    }


@pytest.mark.asyncio
async def test_sync_once_reset_mode_is_non_destructive(tmp_path: Path) -> None:
    ileo_client = FakeIleoClient([IleoReading(date(2025, 3, 1), 120.0, 120000)])
    ha_client = FakeHomeAssistantClient()

    result = await sync_once(
        _config(mode="reset"),
        ileo_client,
        ha_client,
        state_path=tmp_path / "last_sync.json",
    )

    assert result.imported_readings == 0
    assert ileo_client.calls == []
    assert ha_client.states == []
    assert ha_client.statistics == []


def test_read_last_sync_returns_empty_state_for_missing_or_invalid_file(tmp_path: Path) -> None:
    assert read_last_sync(tmp_path / "missing.json") == {}

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{", encoding="utf-8")

    assert read_last_sync(invalid_path) == {}


def test_meter_sync_state_reads_legacy_root_marker(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    write_last_sync(
        state_path,
        {"last_imported_date": "2025-03-02", "latest_index_litres": 120180},
    )

    assert read_meter_sync_state(state_path, "default") == {
        "last_imported_date": "2025-03-02",
        "latest_index_litres": 120180,
    }


def test_write_meter_sync_state_preserves_installation_id(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    write_last_sync(state_path, {"installation_id": "stable"})

    write_meter_sync_state(state_path, "4052059", {"last_imported_date": "2025-03-03"})

    state = read_last_sync(state_path)
    assert state["installation_id"] == "stable"
    assert state["meters"]["4052059"]["last_imported_date"] == "2025-03-03"


@pytest.mark.asyncio
async def test_sync_once_publishes_each_meter_including_empty_contract(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    ileo_client = FakeIleoClient(
        meter_readings=[
            IleoMeterReadings(
                IleoMeter("4052059", "Contrat 4052059"),
                [IleoReading(date(2026, 6, 28), 180.0, 120180, meter_id="4052059")],
            ),
            IleoMeterReadings(IleoMeter("4147436", "Contrat 4147436"), []),
        ]
    )
    ha_client = FakeHomeAssistantClient()

    result = await sync_once(
        _config(),
        ileo_client,
        ha_client,
        state_path=state_path,
        today=date(2026, 7, 8),
    )

    assert [state[0] for state in ha_client.states] == [
        meter_entity_id("4052059"),
        meter_entity_id("4147436"),
    ]
    assert ha_client.states[0][1] == "120180"
    assert ha_client.states[1][1] == "unknown"
    assert result.fetched_readings == 1
    assert result.imported_readings == 1
    assert read_last_sync(state_path)["meters"]["4052059"] == {
        "last_imported_date": "2026-06-28",
        "latest_index_litres": 120180,
    }


@pytest.mark.asyncio
async def test_sync_once_uses_configured_meter_name(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    ileo_client = FakeIleoClient(
        meter_readings=[
            IleoMeterReadings(
                IleoMeter("4052059", "Contrat 4052059"),
                [IleoReading(date(2026, 6, 28), 180.0, 120180, meter_id="4052059")],
            ),
        ]
    )
    ha_client = FakeHomeAssistantClient()

    result = await sync_once(
        AppConfig(
            username="user@example.test",
            password="secret",
            start_date=date(2025, 3, 1),
            sync_interval_hours=4,
            mode="sync",
            meter_names={"4052059": "Compteur maison"},
        ),
        ileo_client,
        ha_client,
        state_path=state_path,
        today=date(2026, 7, 8),
    )

    assert result.imported_readings == 1
    assert ha_client.states[0][2]["friendly_name"] == "ILEO eau - Compteur maison"


def test_get_or_create_installation_id_reuses_persisted_value(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    write_last_sync(state_path, {"installation_id": "stable-installation"})

    installation_id = get_or_create_installation_id(state_path)

    assert installation_id == "stable-installation"
    assert read_last_sync(state_path) == {"installation_id": "stable-installation"}


def test_get_or_create_installation_id_persists_new_value(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"

    installation_id = get_or_create_installation_id(state_path)

    assert installation_id
    assert read_last_sync(state_path) == {"installation_id": installation_id}


def test_calculate_initial_jitter_seconds_is_stable_and_bounded() -> None:
    jitter = calculate_initial_jitter_seconds("stable-installation")

    assert jitter == calculate_initial_jitter_seconds("stable-installation")
    assert 0 <= jitter <= MAX_INITIAL_JITTER_SECONDS


def test_calculate_sync_interval_seconds_adds_stable_jitter_after_first_sync() -> None:
    interval = calculate_sync_interval_seconds(4, "stable-installation")

    assert interval == 4 * 3600 + calculate_initial_jitter_seconds("stable-installation")


def test_calculate_error_retry_seconds_uses_short_retry_delay() -> None:
    assert calculate_error_retry_seconds() == ERROR_RETRY_SECONDS
    assert calculate_error_retry_seconds() == 5 * 60
