"""Runtime entrypoint for the ILEO Home Assistant app."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .config import AppConfig, load_config
from .ha_api import HomeAssistantClient
from .ileo_client import IleoApiClient, IleoReading
from .statistics import (
    WATER_ENTITY_ID,
    filter_after_last_sync,
    import_statistics_payload,
    latest_state,
)

STATE_PATH = Path("/data/last_sync.json")

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
    readings = await ileo_client.async_fetch_readings(config.start_date, end_date)
    if not readings:
        LOGGER.info("No ILEO readings were returned")
        return SyncResult(0, 0, None)

    state, attributes = latest_state(readings)
    await ha_client.async_set_state(WATER_ENTITY_ID, state, attributes)

    last_sync = read_last_sync(state_path)
    new_readings = filter_after_last_sync(readings, last_sync.get("last_imported_date"))
    if new_readings:
        await ha_client.async_import_statistics(import_statistics_payload(new_readings))

    latest = max(readings, key=lambda reading: reading.date)
    write_last_sync(
        state_path,
        {
            "last_imported_date": latest.date.isoformat(),
            "latest_index_litres": latest.index_litres,
        },
    )

    result = SyncResult(
        fetched_readings=len(readings),
        imported_readings=len(new_readings),
        latest_reading_date=latest.date.isoformat(),
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


async def run_loop(config: AppConfig, state_path: Path = STATE_PATH) -> None:
    """Run synchronization forever using Supervisor options."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        ileo_client = IleoApiClient(session, config.username, config.password)
        ha_client = HomeAssistantClient(session)
        while True:
            try:
                await sync_once(config, ileo_client, ha_client, state_path=state_path)
            except Exception:
                LOGGER.exception("ILEO synchronization failed")
            await asyncio.sleep(config.sync_interval_hours * 3600)


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

