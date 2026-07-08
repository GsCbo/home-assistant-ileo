"""Tests for Supervisor option parsing."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "ileo"))

from app.config import ConfigError, load_config, parse_config


def test_parse_config_returns_validated_app_config() -> None:
    config = parse_config(
        {
            "username": " user@example.test ",
            "password": " secret ",
            "start_date": "2025-03-01",
            "sync_interval_hours": 4,
            "mode": "sync",
        }
    )

    assert config.username == "user@example.test"
    assert config.password == "secret"
    assert config.start_date == date(2025, 3, 1)
    assert config.sync_interval_hours == 4
    assert config.mode == "sync"
    assert config.meter_names == {}


def test_parse_config_accepts_meter_names_mapping() -> None:
    config = parse_config(
        {
            "username": "user@example.test",
            "password": "secret",
            "start_date": "2025-03-01",
            "sync_interval_hours": 4,
            "meter_names": "4052059 = Maison\n4147436=Jardin",
        }
    )

    assert config.meter_names == {
        "4052059": "Maison",
        "4147436": "Jardin",
    }


@pytest.mark.parametrize("meter_names", ["4052059 Maison", "=Maison", "4052059="])
def test_parse_config_rejects_invalid_meter_names(meter_names: str) -> None:
    with pytest.raises(ConfigError):
        parse_config(
            {
                "username": "user@example.test",
                "password": "secret",
                "start_date": "2025-03-01",
                "sync_interval_hours": 4,
                "meter_names": meter_names,
            }
        )


@pytest.mark.parametrize("key", ["username", "password", "start_date"])
def test_parse_config_requires_string_fields(key: str) -> None:
    data = {
        "username": "user@example.test",
        "password": "secret",
        "start_date": "2025-03-01",
        "sync_interval_hours": 4,
    }
    data[key] = ""

    with pytest.raises(ConfigError):
        parse_config(data)


@pytest.mark.parametrize("start_date", ["01/03/2025", "2025-13-01"])
def test_parse_config_rejects_invalid_start_date(start_date: str) -> None:
    with pytest.raises(ConfigError):
        parse_config(
            {
                "username": "user@example.test",
                "password": "secret",
                "start_date": start_date,
                "sync_interval_hours": 4,
            }
        )


@pytest.mark.parametrize("sync_interval_hours", [0, 169, "4"])
def test_parse_config_rejects_invalid_interval(sync_interval_hours: object) -> None:
    with pytest.raises(ConfigError):
        parse_config(
            {
                "username": "user@example.test",
                "password": "secret",
                "start_date": "2025-03-01",
                "sync_interval_hours": sync_interval_hours,
            }
        )


def test_parse_config_rejects_invalid_mode() -> None:
    with pytest.raises(ConfigError):
        parse_config(
            {
                "username": "user@example.test",
                "password": "secret",
                "start_date": "2025-03-01",
                "sync_interval_hours": 4,
                "mode": "delete",
            }
        )


def test_load_config_reads_options_file(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    options_path.write_text(
        json.dumps(
            {
                "username": "user@example.test",
                "password": "secret",
                "start_date": "2025-03-01",
                "sync_interval_hours": 4,
            }
        ),
        encoding="utf-8",
    )

    config = load_config(options_path)

    assert config.username == "user@example.test"


def test_run_script_preserves_supervisor_environment() -> None:
    script_path = Path(__file__).parents[1] / "ileo" / "run.sh"
    first_line = script_path.read_text(encoding="utf-8").splitlines()[0]

    assert first_line == "#!/usr/bin/with-contenv bash"
