"""Constants for the ILEO integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME

DOMAIN = "ileo"
PLATFORMS = ["sensor"]

CONF_START_DATE = "start_date"
DEFAULT_SCAN_INTERVAL = timedelta(hours=4)
DEFAULT_START_DATE = "2025-03-01"

BASE_URL = "https://www.mel-ileo.fr"
LOGIN_URL = f"{BASE_URL}/connexion.aspx"
CONSUMPTION_URL = f"{BASE_URL}/espaceperso/mes-consommations.aspx"

CONF_KEYS = (CONF_USERNAME, CONF_PASSWORD, CONF_START_DATE, CONF_SCAN_INTERVAL)
