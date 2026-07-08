"""Runtime entrypoint for the ILEO Home Assistant app."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .config import AppConfig, load_config
from .ha_api import HomeAssistantClient
from .ileo_client import DEFAULT_METER_ID, IleoApiClient, IleoMeter, IleoMeterReadings, IleoReading
from .statistics import (
    empty_meter_state,
    filter_after_last_sync,
    import_statistics_payload,
    latest_state,
    meter_entity_id,
)

STATE_PATH = Path("/data/last_sync.json")
INSTALLATION_ID_KEY = "installation_id"
MAX_INITIAL_JITTER_SECONDS = 30 * 60

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Summary of a synchronization run."""

    fetched_readings: int
    imported_readings: int
    latest_reading_date: str | None


async def sync_once(
    config: AppConfig,
    ileo_client: IleoApiClient,
    ha_client: HomeAssistantClient,
    *,
    state_path: Path = STATE_PATH,
    today: date | None = None,
) -> SyncResult:
    """Fetch ILEO readings once and publish state/statistics to Home Assistant."""
    if config.mode == "reset":
        LOGGER.warning("Reset mode is selected; no destructive reset is performed yet")
        return SyncResult(0, 0, None)

    end_date = today or date.today()
    meter_readings = await _fetch_meter_readings(ileo_client, config.start_date, end_date)
    if not meter_readings:
        LOGGER.info("No ILEO meters were returned")
        return SyncResult(0, 0, None)

    fetched_readings = 0
    imported_readings = 0
    latest_reading_date: str | None = None

    for item in meter_readings:
        meter = item.meter
        readings = item.readings
        fetched_readings += len(readings)

        entity_id = meter_entity_id(meter.meter_id)
        if readings:
            state, attributes = latest_state(
                readings,
                meter_id=meter.meter_id,
                meter_label=meter.name,
            )
        else:
            state, attributes = empty_meter_state(meter.meter_id, meter.name)
        await ha_client.async_set_state(entity_id, state, attributes)

        meter_sync = read_meter_sync_state(state_path, meter.meter_id)
        new_readings = filter_after_last_sync(
            readings, meter_sync.get("last_imported_date")
        )
        if new_readings:
            await ha_client.async_import_statistics(
                import_statistics_payload(new_readings, meter.meter_id, meter.name)
            )
            imported_readings += len(new_readings)

        if readings:
            latest = max(readings, key=lambda reading: reading.date)
            write_meter_sync_state(
                state_path,
                meter.meter_id,
                {
                    "last_imported_date": latest.date.isoformat(),
                    "latest_index_litres": latest.index_litres,
                },
            )
            if latest_reading_date is None or latest.date.isoformat() > latest_reading_date:
                latest_reading_date = latest.date.isoformat()

    result = SyncResult(
        fetched_readings=fetched_readings,
        imported_readings=imported_readings,
        latest_reading_date=latest_reading_date,
    )
    LOGGER.info("ILEO sync finished: %s", asdict(result))
    return result


def read_last_sync(path: Path = STATE_PATH) -> dict[str, Any]:
    """Read persisted sync state, returning an empty state when absent or invalid."""
    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    return raw_data if isinstance(raw_data, dict) else {}


def write_last_sync(path: Path, data: dict[str, Any]) -> None:
    """Persist sync state under /data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


async def _fetch_meter_readings(
    ileo_client: IleoApiClient,
    start_date: date,
    end_date: date,
) -> list[IleoMeterReadings]:
    if hasattr(ileo_client, "async_fetch_meter_readings"):
        return await ileo_client.async_fetch_meter_readings(start_date, end_date)

    readings = await ileo_client.async_fetch_readings(start_date, end_date)
    return [IleoMeterReadings(IleoMeter(DEFAULT_METER_ID, "ILEO"), readings)]


def read_meter_sync_state(path: Path, meter_id: str) -> dict[str, Any]:
    """Read the persisted sync marker for a meter, including legacy default state."""
    state = read_last_sync(path)
    meters = state.get("meters")
    if isinstance(meters, dict) and isinstance(meters.get(meter_id), dict):
        return meters[meter_id]

    if meter_id == DEFAULT_METER_ID:
        return {
            key: state[key]
            for key in ("last_imported_date", "latest_index_litres")
            if key in state
        }

    return {}


def write_meter_sync_state(
    path: Path, meter_id: str, meter_state: dict[str, Any]
) -> None:
    """Persist the sync marker for one meter without losing global state."""
    state = read_last_sync(path)
    current_meters = state.get("meters")
    meters = current_meters if isinstance(current_meters, dict) else {}
    write_last_sync(path, {**state, "meters": {**meters, meter_id: meter_state}})


def get_or_create_installation_id(path: Path = STATE_PATH) -> str:
    """Return a stable per-installation identifier stored with sync state."""
    state = read_last_sync(path)
    installation_id = state.get(INSTALLATION_ID_KEY)
    if isinstance(installation_id, str) and installation_id:
        return installation_id

    installation_id = str(uuid.uuid4())
    write_last_sync(path, {**state, INSTALLATION_ID_KEY: installation_id})
    return installation_id


def calculate_initial_jitter_seconds(installation_id: str) -> int:
    """Calculate a stable 0-30 minute startup delay from the installation id."""
    digest = hashlib.sha256(installation_id.encode("utf-8")).digest()
    value = int.from_bytes(digest[:4], byteorder="big", signed=False)
    return value % (MAX_INITIAL_JITTER_SECONDS + 1)


def calculate_sync_interval_seconds(sync_interval_hours: int, installation_id: str) -> int:
    """Calculate the delay between syncs after the immediate startup sync."""
    return sync_interval_hours * 3600 + calculate_initial_jitter_seconds(installation_id)


async def run_loop(config: AppConfig, state_path: Path = STATE_PATH) -> None:
    """Run synchronization forever using Supervisor options."""
    import aiohttp

    installation_id = get_or_create_installation_id(state_path)
    sync_interval = calculate_sync_interval_seconds(
        config.sync_interval_hours,
        installation_id,
    )
    LOGGER.info("Using %s seconds between ILEO syncs", sync_interval)

    async with aiohttp.ClientSession() as session:
        ileo_client = IleoApiClient(session, config.username, config.password)
        ha_client = HomeAssistantClient(session)
        while True:
            try:
                await sync_once(config, ileo_client, ha_client, state_path=state_path)
            except Exception:
                LOGGER.exception("ILEO synchronization failed")
            await asyncio.sleep(sync_interval)


def configure_logging() -> None:
    """Configure readable logs for Supervisor."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def main() -> None:
    """CLI entrypoint used by run.sh."""
    configure_logging()
    config = load_config()
    asyncio.run(run_loop(config))


if __name__ == "__main__":
    main()
