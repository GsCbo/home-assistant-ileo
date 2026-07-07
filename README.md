# ILEO for Home Assistant

## Status

HACS-ready custom integration for Home Assistant.

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

## Development

Run the test suite with:

```bash
pytest tests -v
```
