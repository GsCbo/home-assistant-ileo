# ILEO Home Assistant App Design

Date: 2026-07-07

## Goal

Convert the repository from a HACS custom integration into a Home Assistant App repository, following the model used by apps such as HA Linky.

The target user experience is:

1. Add `https://github.com/GsCbo/home-assistant-ileo-scraper` in Home Assistant under Apps > Store > Repositories.
2. Install the ILEO app.
3. Configure ILEO credentials and import options in the app configuration tab.
4. Start the app and monitor synchronization from the app log.
5. Select the generated water consumption statistics in the Energy dashboard.

## Architecture Choice

The app runtime will remain Python for the first app version.

Reasons:

- The current repository already has tested Python parsing and ILEO client code.
- Python is straightforward inside a Home Assistant app container.
- The main integration work is Home Assistant API/statistics behavior, not frontend or service UI work.
- Rewriting in TypeScript or .NET now would add migration risk before validating the ILEO portal and statistics import path.

TypeScript or .NET can be reconsidered later if the app grows a real web UI, background worker framework, or external service API.

## Repository Shape

The repository will become an app repository:

```text
repository.yaml
ileo/
  config.yaml
  Dockerfile
  README.md
  run.sh
  requirements.txt
  app/
    ileo_client.py
    ha_api.py
    statistics.py
    main.py
tests/
```

The current `custom_components/ileo` integration will be removed. The app is not installed through HACS and should not contain `hacs.json`.

## App Configuration

The app configuration will expose:

- `username`: ILEO account email.
- `password`: ILEO password.
- `start_date`: first import date, default `2025-03-01`.
- `sync_interval_hours`: recurring sync interval, default `4`.
- `mode`: `sync` or `reset`, with `sync` as default.

The app should validate configuration at startup and fail with clear log messages if required fields are missing or malformed.

## Runtime Behavior

At startup, the app will:

1. Read `/data/options.json`.
2. Validate configuration.
3. Log into ILEO.
4. Download and parse the CSV export.
5. Create or update Home Assistant statistics/entities needed by the Energy dashboard.
6. Persist the latest imported reading in `/data`.
7. Repeat on the configured interval while the app is running.

The first version should prioritize a reliable water total statistic. Cost tracking and multiple meters are out of scope.

## Home Assistant Communication

The app will use the Home Assistant API exposed through Supervisor:

- `SUPERVISOR_TOKEN` for authentication.
- `http://supervisor/core/api` for Home Assistant REST calls where suitable.
- WebSocket API if REST is not enough for statistics operations.

The app `config.yaml` must enable `homeassistant_api: true`. It should not request broad privileges unless needed.

## Statistics And Energy Dashboard

The app should produce a water total compatible with the Energy dashboard:

- statistic/entity name based on ILEO water index.
- unit `L`.
- device class `water`.
- state class / statistic model equivalent to total increasing water usage.

Historical import is a first-class goal in the app model, but it must be implemented conservatively:

- avoid duplicate statistic writes;
- keep imported timestamps stable;
- log imported, skipped, and failed counts;
- provide a reset mode before changing historical behavior broadly.

## Error Handling

The app must distinguish:

- invalid ILEO credentials;
- ILEO portal unavailable;
- unexpected ILEO login form or CSV format;
- Home Assistant API/statistics write failures;
- no new readings.

No new readings is a normal result and should not fail the app.

## Migration From Current Integration

Remove:

- `custom_components/ileo`
- `hacs.json`
- integration-specific README instructions

Keep and adapt:

- CSV parser and ILEO HTTP client behavior
- tests for parser/client behavior

Add:

- app repository metadata
- app container files
- app runtime loop
- Home Assistant API/statistics writer
- app installation documentation

## Testing

The implementation should include:

- unit tests for CSV parsing and ILEO client behavior;
- unit tests for app configuration validation;
- unit tests for Home Assistant payload/statistics generation;
- smoke validation that app metadata files are valid YAML;
- Python compilation checks.

Live ILEO login and Home Assistant statistics import remain deployment validation steps because they depend on external services.

## Non-Goals For First App Version

- TypeScript or .NET rewrite.
- Multi-meter support.
- Cost calculations.
- Embedded web UI.
- Ingress dashboard.
- Long-lived custom integration under `custom_components`.
