"""Constants for the Austrian Fuel Prices integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "at_fuel_prices"

# --- API ---------------------------------------------------------------------
API_BASE_URL: Final = "https://api.e-control.at/sprit/1.0"
API_SEARCH_BY_ADDRESS: Final = f"{API_BASE_URL}/search/gas-stations/by-address"

# E-Control only returns prices for the cheapest five stations, so there is no
# point in ever creating more than five rank-based sensors.
MAX_STATIONS: Final = 5

# Fuel types accepted by the API.
FUEL_TYPES: Final = {
    "DIE": "Diesel",
    "SUP": "Super 95",
    "GAS": "Autogas (LPG)",
}

# --- Config / options keys ---------------------------------------------------
CONF_LOCATION: Final = "location"
CONF_FUEL_TYPE: Final = "fuel_type"
CONF_STATION_COUNT: Final = "station_count"
CONF_INCLUDE_CLOSED: Final = "include_closed"
CONF_SCAN_INTERVAL_MINUTES: Final = "scan_interval_minutes"

# --- Defaults ----------------------------------------------------------------
DEFAULT_FUEL_TYPE: Final = "DIE"
DEFAULT_STATION_COUNT: Final = 5
DEFAULT_INCLUDE_CLOSED: Final = True

# E-Control bans the request URL for a day if polled too aggressively. Keep the
# default conservative and never allow anything below MIN_SCAN_INTERVAL.
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=30)
MIN_SCAN_INTERVAL_MINUTES: Final = 15

# --- Attribute keys exposed on the sensors -----------------------------------
ATTR_STATION_ID: Final = "station_id"
ATTR_STATION_NAME: Final = "station_name"
ATTR_ADDRESS: Final = "address"
ATTR_POSTAL_CODE: Final = "postal_code"
ATTR_CITY: Final = "city"
ATTR_LATITUDE: Final = "latitude"
ATTR_LONGITUDE: Final = "longitude"
ATTR_IS_OPEN: Final = "is_open"
ATTR_FUEL_LABEL: Final = "fuel_label"
ATTR_RANK: Final = "rank"
