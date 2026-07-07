# ILEO Multi-Meter Design

## Goal

Support ILEO accounts that expose several water meters or contracts, while keeping the current single-meter behavior working.

## Current State

The app currently assumes one ILEO account maps to one water index:

- one CSV export;
- one entity id: `sensor.ileo_water_index`;
- one statistic id: `sensor.ileo_water_index`;
- one persisted `last_imported_date`.

This is too narrow for accounts with several addresses, contracts, or meters.

## Product Behavior

The default behavior is automatic import:

- detect all meters exposed by the ILEO account;
- import every detected meter by default;
- create one Home Assistant entity and one long-term statistic per meter;
- allow users to rename entities inside Home Assistant without breaking future syncs.

The app must keep a stable technical identifier per meter. The display name can change, but the statistic id must remain stable.

## Meter Model

Each meter is represented internally as:

```python
IleoMeter(
    meter_id="stable-technical-id",
    name="Human-readable ILEO label",
)
```

Each reading belongs to one meter:

```python
IleoReading(
    meter_id="stable-technical-id",
    date=date(2025, 3, 2),
    litres=180.0,
    index_litres=120180,
)
```

If ILEO only exposes one meter and no explicit id is available, the app uses a compatibility id named `default`.

## Entity And Statistic Naming

The default single-meter compatibility entity remains:

```text
sensor.ileo_water_index
```

For explicit multi-meter data, entity ids are derived from the stable meter id:

```text
sensor.ileo_water_index_<slug>
```

The statistic id matches the entity id. The friendly name uses the ILEO meter label when available, for example `ILEO eau - Maison`.

## Persistence

`/data/last_sync.json` keeps global app state and per-meter sync markers:

```json
{
  "installation_id": "uuid",
  "meters": {
    "default": {
      "last_imported_date": "2025-03-02",
      "latest_index_litres": 120180
    },
    "contract-123": {
      "last_imported_date": "2025-03-02",
      "latest_index_litres": 88052
    }
  }
}
```

Legacy single-meter state is migrated in memory by treating root-level `last_imported_date` and `latest_index_litres` as the `default` meter.

## ILEO Discovery Strategy

Because the ILEO website is in maintenance on July 7, 2026, real multi-meter discovery cannot be confirmed yet.

The implementation will first make the runtime multi-meter capable with a single compatibility meter. When the portal is available, discovery can be connected using whichever ILEO shape exists:

- a contract/meter selector in HTML;
- a meter id parameter in the CSV export URL;
- a CSV column containing the meter, contract, address, or reference;
- separate pages per contract or address.

The parser must fail clearly if it detects ambiguous multi-meter data without a stable id.

## Configuration

No extra configuration is required for the first multi-meter-ready version. Existing options remain valid:

```yaml
username: user@example.com
password: secret
start_date: "2025-03-01"
sync_interval_hours: 4
mode: sync
```

Optional include/exclude filters can be added later if real accounts expose old or unwanted meters.

## Testing

Tests must cover:

- compatibility parsing where readings use `meter_id="default"`;
- entity/statistic generation for single and multiple meters;
- per-meter filtering after last sync;
- sync state persistence without losing `installation_id`;
- legacy root-level sync state migration.

