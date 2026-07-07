# ILEO

ILEO is a Home Assistant App that synchronizes water readings from an ILEO account into Home Assistant so they can be used by the Energy dashboard.

## Configuration

```yaml
username: your-email@example.com
password: your-password
start_date: "2025-03-01"
sync_interval_hours: 4
mode: sync
```

### Options

- `username`: ILEO account email.
- `password`: ILEO password.
- `start_date`: first date to import, in `YYYY-MM-DD` format.
- `sync_interval_hours`: delay between synchronization runs.
- `mode`: `sync` to import readings, or `reset` to log reset intent without deleting data in v1.

## Energy

The app creates and updates an ILEO water index entity/statistic using liters and water metadata for the Home Assistant Energy dashboard.

## Notes

Live ILEO login and CSV export depend on the ILEO website. If the portal changes its login form or CSV format, the app logs a clear error instead of importing partial data.
