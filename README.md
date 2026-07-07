# ILEO Home Assistant App

## Status

Home Assistant App repository for synchronizing ILEO water readings with Home Assistant Energy statistics.

## Installation

1. Open Home Assistant.
2. Go to Settings > Apps > Store.
3. Open the repository menu.
4. Add `https://github.com/GsCbo/home-assistant-ileo`.
5. Install the ILEO app.
6. Configure the app and start it.

## Configuration

Configure the app with your ILEO email, password, optional history start date, synchronization interval, and mode.

## Energy Dashboard

After the first successful synchronization, use the generated ILEO water statistic in Settings > Dashboards > Energy > Water consumption.

The water index entity exposes the metadata expected by the Energy Dashboard:

- Device class: `water`
- State class: `total_increasing`
- Unit: `L`

## Development

Run the test suite with:

```bash
pytest tests -v
```
