"""Configuration loading for the ILEO app."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

DEFAULT_OPTIONS_PATH = Path("/data/options.json")
VALID_MODES = {"sync", "reset"}


class ConfigError(Exception):
    """Raised when app options are missing or invalid."""


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated runtime configuration."""

    username: str
    password: str
    start_date: date
    sync_interval_hours: int
    mode: str = "sync"


def load_config(path: Path = DEFAULT_OPTIONS_PATH) -> AppConfig:
    """Load app options from Supervisor's options file."""
    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ConfigError(f"Options file not found: {path}") from err
    except json.JSONDecodeError as err:
        raise ConfigError(f"Options file is not valid JSON: {path}") from err

    if not isinstance(raw_data, dict):
        raise ConfigError("Options file must contain a JSON object")

    return parse_config(raw_data)


def parse_config(data: dict[str, Any]) -> AppConfig:
    """Validate raw Supervisor options."""
    username = _required_str(data, "username")
    password = _required_str(data, "password")
    start_date = _parse_start_date(_required_str(data, "start_date"))
    sync_interval_hours = _parse_sync_interval(data.get("sync_interval_hours"))
    mode = str(data.get("mode", "sync")).strip().lower()

    if mode not in VALID_MODES:
        raise ConfigError(f"mode must be one of: {', '.join(sorted(VALID_MODES))}")

    return AppConfig(
        username=username,
        password=password,
        start_date=start_date,
        sync_interval_hours=sync_interval_hours,
        mode=mode,
    )


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} is required")
    return value.strip()


def _parse_start_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as err:
        raise ConfigError("start_date must use YYYY-MM-DD format") from err


def _parse_sync_interval(value: Any) -> int:
    if not isinstance(value, int):
        raise ConfigError("sync_interval_hours must be an integer")
    if value < 1 or value > 168:
        raise ConfigError("sync_interval_hours must be between 1 and 168")
    return value

