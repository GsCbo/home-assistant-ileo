"""Tests for Home Assistant statistics payload generation."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "ileo"))

from app.ileo_client import IleoReading
from app.statistics import (
    import_statistics_payload,
    meter_statistic_id,
)


def test_meter_statistic_id_uses_external_ileo_namespace() -> None:
    assert meter_statistic_id("default") == "ileo:water_index"
    assert meter_statistic_id("Contrat 12 Rue de Lille") == (
        "ileo:water_index_contrat_12_rue_de_lille"
    )


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
    assert payload["metadata"]["statistic_id"] == "ileo:water_index_1234567"
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
