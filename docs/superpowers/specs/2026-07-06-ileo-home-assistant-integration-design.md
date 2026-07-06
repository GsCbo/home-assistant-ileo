# ILEO Home Assistant Integration Design

Date: 2026-07-06

## Goal

Convert the current Docker and MQTT based ILEO scraper into a HACS-ready Home Assistant custom integration that can be configured from the Home Assistant UI and expose water consumption entities compatible with the Home Assistant Energy dashboard water section.

The target user experience is:

1. Install the repository as a HACS custom repository.
2. Restart Home Assistant.
3. Add the "ILEO" integration from Settings > Devices & services.
4. Enter ILEO credentials and optional polling/history settings.
5. Select the created water total sensor in Settings > Dashboards > Energy > Water.

## Current State

The repository currently contains:

- `app/main.py`: a synchronous Selenium scraper that logs into `mel-ileo.fr`, downloads a CSV export, filters rows, caches the last sent reading, and publishes recent readings to MQTT.
- `mqtt.yaml`: example MQTT sensors for current water consumption and last consumption date.
- `README.md`, `Dockerfile`, and `docker-compose.yml`: Docker-oriented installation documentation.

Home Assistant integration currently depends on external Docker execution, MQTT configuration, and a Home Assistant automation using `recorder.import_statistics`.

## Chosen Approach

Build a native custom integration in `custom_components/ileo` and keep the old Docker scraper as a migration/reference path until the integration is validated.

The integration should not depend on Selenium. Selenium and Chrome are too heavy and fragile for Home Assistant OS, Home Assistant Container, and HACS installs. The first implementation should replace the browser automation with an HTTP client that:

- Opens the ILEO login page.
- Submits credentials using the portal form fields and session cookies.
- Downloads the CSV export for a configured date range.
- Parses consumption rows into typed readings.

If the ILEO website cannot be accessed without a browser because of anti-bot or JavaScript-only behavior, the project should stop and reassess rather than embedding Selenium inside Home Assistant.

## Architecture

### Package Layout

The new integration will use this structure:

```text
custom_components/ileo/
  __init__.py
  api.py
  config_flow.py
  const.py
  coordinator.py
  diagnostics.py
  manifest.json
  sensor.py
  strings.json
  translations/fr.json
tests/
  test_api.py
  test_config_flow.py
  test_sensor.py
  fixtures/
```

### API Client

`api.py` owns all ILEO website access and CSV parsing. It exposes a small interface:

- `async_validate_credentials()`
- `async_fetch_readings(start_date, end_date)`

It returns typed reading objects with:

- `date`
- `litres`
- `index_litres`

The client must not know about Home Assistant entities, statistics, or config entries.

### Config Flow

`config_flow.py` provides UI setup with:

- email/login
- password
- optional start date for first import
- optional update interval, defaulting to 4 hours

The flow validates credentials before creating the config entry. The unique ID is the normalized login/email so the same ILEO account cannot be configured twice.

Options flow can later adjust update interval and history import range without editing YAML.

### Coordinator

`coordinator.py` uses `DataUpdateCoordinator` to fetch ILEO readings on one shared schedule for all entities.

The default polling interval is 4 hours, matching the current Docker/cron recommendation. The coordinator stores the latest parsed readings and raises Home Assistant update/auth exceptions when appropriate:

- authentication failure triggers reauth
- temporary website/network failure marks entities unavailable and retries later
- malformed CSV raises an update failure with a useful log message

### Sensors

`sensor.py` creates one device named `ILEO` and at least these entities:

- Water meter index: total index from the latest ILEO reading, device class `water`, state class `total_increasing`, native unit `L`. This is the primary Energy dashboard water entity.
- Last consumption: litres from the latest daily reading, device class `water`, state class `measurement`, native unit `L`.
- Last reading date: date of the latest available reading.

Entity unique IDs are stable and derived from the config entry unique ID and a sensor suffix.

### Historical Statistics

The integration should include a history import path for the ILEO CSV data so the Energy dashboard can show older water usage instead of starting from the install date only.

The first version should implement this conservatively:

- Import readings only for the water meter index statistic.
- Use the same statistic ID as the main water index sensor.
- Avoid duplicate or older writes when the statistic already exists.
- Log how many historical points were imported.

If direct statistics import proves too risky for the first implementation, it can be split into a second implementation phase, but the entity model must still be compatible with long-term statistics from day one.

## Error Handling

The integration must distinguish:

- invalid credentials
- ILEO portal unavailable
- CSV download unavailable
- CSV format changed
- no new readings

No new readings is a normal state and should not mark the integration unavailable.

Credentials must be stored in the config entry data and redacted from diagnostics.

## HACS Packaging

The repository should be shaped for HACS default integration installation:

- integration code under `custom_components/ileo`
- `manifest.json` with `domain`, `name`, `version`, `config_flow`, `iot_class`, `requirements`, and documentation URLs
- README updated with HACS install instructions and Energy dashboard setup
- optional `hacs.json` if needed by HACS metadata checks

The existing Docker files can remain during migration but should be marked as legacy once the custom integration is functional.

## Tests

Testing should focus on behavior that can break Home Assistant compatibility:

- CSV parsing from realistic fixture files
- login validation success/failure mocked at HTTP level
- config flow duplicate account and invalid credential paths
- sensor metadata for Energy compatibility
- coordinator handling for auth, network, and malformed CSV failures
- historical import duplicate avoidance if implemented in the first phase

## Non-Goals

This design does not include:

- Selenium inside Home Assistant
- MQTT discovery as the primary integration path
- dashboard cards or Lovelace layout work
- editing a live Home Assistant instance during repository implementation
- publishing to the official Home Assistant core repository

## Open Risks

The main technical risk is whether `mel-ileo.fr` login and CSV export can be performed reliably with HTTP requests instead of Selenium. This should be validated first with a small isolated client test before building the full Home Assistant integration around it.

The second risk is historical statistics import. Home Assistant long-term statistics are strict about metadata and units, so this should be implemented with focused tests and verified in a disposable Home Assistant instance before relying on it in production.
