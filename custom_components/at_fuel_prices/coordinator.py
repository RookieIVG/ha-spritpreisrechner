"""DataUpdateCoordinator for the Austrian Fuel Prices integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EControlApiClient, EControlApiError
from .const import (
    CONF_FUEL_TYPE,
    CONF_INCLUDE_CLOSED,
    CONF_LOCATION,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_FUEL_TYPE,
    DEFAULT_INCLUDE_CLOSED,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

# A typed config entry so `entry.runtime_data` is the coordinator everywhere.
type AtFuelConfigEntry = ConfigEntry[AtFuelDataUpdateCoordinator]


class AtFuelDataUpdateCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Polls E-Control and keeps the price-bearing stations sorted by price."""

    config_entry: AtFuelConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AtFuelConfigEntry) -> None:
        """Initialise the coordinator from a config entry."""
        self._client = EControlApiClient(async_get_clientsession(hass))

        location = entry.data[CONF_LOCATION]
        self._latitude: float = location[CONF_LATITUDE]
        self._longitude: float = location[CONF_LONGITUDE]
        self._fuel_type: str = entry.data.get(CONF_FUEL_TYPE, DEFAULT_FUEL_TYPE)

        # Mutable values live in options (with fall-back to data / defaults).
        self._include_closed: bool = entry.options.get(
            CONF_INCLUDE_CLOSED,
            entry.data.get(CONF_INCLUDE_CLOSED, DEFAULT_INCLUDE_CLOSED),
        )

        minutes = entry.options.get(CONF_SCAN_INTERVAL_MINUTES)
        if minutes:
            interval = timedelta(minutes=max(minutes, MIN_SCAN_INTERVAL_MINUTES))
        else:
            interval = DEFAULT_SCAN_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=interval,
            config_entry=entry,
        )

    @property
    def fuel_type(self) -> str:
        """Return the configured fuel type (DIE / SUP / GAS)."""
        return self._fuel_type

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch and normalise the station list."""
        try:
            stations = await self._client.async_get_stations(
                self._latitude,
                self._longitude,
                self._fuel_type,
                self._include_closed,
            )
        except EControlApiError as err:
            raise UpdateFailed(str(err)) from err

        # Keep only stations that actually carry a price, then sort ascending by
        # price. The API already returns them sorted, but we don't rely on that.
        priced = [
            station
            for station in stations
            if station.get("prices") and station["prices"][0].get("amount") is not None
        ]
        priced.sort(key=lambda s: s["prices"][0]["amount"])
        return priced

    def station_at(self, rank: int) -> dict[str, Any] | None:
        """Return the station at a 1-based rank, or None if unavailable."""
        index = rank - 1
        if self.data and 0 <= index < len(self.data):
            return self.data[index]
        return None
