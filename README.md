# ILEO for Home Assistant

Status: migrated from Docker/MQTT scraper toward HACS-ready custom integration.

## Installation with HACS

1. In HACS, add this repository as a custom repository.
2. Select the category `Integration`.
3. Install the ILEO integration.
4. Restart Home Assistant.
5. Go to Settings > Devices & services > Add integration > ILEO.

## Configuration

Configure the integration with your ILEO email and password.

The history start date is optional and defaults to `2025-03-01`.

## Energy Dashboard

After the first successful update, use the generated water index entity in Settings > Dashboards > Energy > Water consumption.

The water index entity exposes the metadata expected by the Energy Dashboard:

- Device class: `water`
- State class: `total_increasing`
- Unit: `L`

## Legacy Docker/MQTT scraper

The previous Docker/MQTT workflow remains in this repository as a legacy reference during the migration.

Use the native Home Assistant integration once live ILEO login and CSV download are validated.

## Development

Run the test suite with:

```bash
pytest tests -v
```
