"""DataUpdateCoordinator for the Austrian Fuel Prices integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EControlApiClient, EControlApiError
from .const import (
    CONF_FUEL_TYPE,
    CONF_INCLUDE_CLOSED,
    CONF_LOCATION,
    CONF_LOCATION_MODE,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_TRACKED_ENTITY,
    DEFAULT_FUEL_TYPE,
    DEFAULT_INCLUDE_CLOSED,
    DEFAULT_LOCATION_MODE,
    DEFAULT_SCAN_INTERVAL,
    LOCATION_MODE_ENTITY,
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

        def opt(key: str, default: Any = None) -> Any:
            """Read a value from options, falling back to data, then default."""
            return entry.options.get(key, entry.data.get(key, default))

        # Fixed location (also used as the fall-back when tracking an entity).
        location = opt(CONF_LOCATION) or {}
        self._fixed_latitude: float = location.get(
            CONF_LATITUDE, hass.config.latitude
        )
        self._fixed_longitude: float = location.get(
            CONF_LONGITUDE, hass.config.longitude
        )

        # Home coordinates are the ultimate fall-back if nothing else resolves.
        self._home_latitude: float = hass.config.latitude
        self._home_longitude: float = hass.config.longitude

        self._location_mode: str = opt(CONF_LOCATION_MODE, DEFAULT_LOCATION_MODE)
        self._tracked_entity: str | None = opt(CONF_TRACKED_ENTITY)

        self._fuel_type: str = opt(CONF_FUEL_TYPE, DEFAULT_FUEL_TYPE)
        self._include_closed: bool = opt(
            CONF_INCLUDE_CLOSED, DEFAULT_INCLUDE_CLOSED
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

    def _resolve_coordinates(self) -> tuple[float, float]:
        """Return the (latitude, longitude) to query this cycle.

        In ``entity`` mode the current GPS position of the tracked person /
        device_tracker is used. If that entity has no usable coordinates (e.g.
        location permission was not granted, or it only reports home/away),
        we fall back to the configured fixed location and finally to home.
        """
        if self._location_mode == LOCATION_MODE_ENTITY and self._tracked_entity:
            state = self.hass.states.get(self._tracked_entity)
            if state is not None:
                lat = state.attributes.get(ATTR_LATITUDE)
                lon = state.attributes.get(ATTR_LONGITUDE)
                if lat is not None and lon is not None:
                    return float(lat), float(lon)
            _LOGGER.debug(
                "Tracked entity %s has no coordinates; using fixed location",
                self._tracked_entity,
            )

        if self._fixed_latitude is not None and self._fixed_longitude is not None:
            return self._fixed_latitude, self._fixed_longitude

        return self._home_latitude, self._home_longitude

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch and normalise the station list."""
        latitude, longitude = self._resolve_coordinates()
        try:
            stations = await self._client.async_get_stations(
                latitude,
                longitude,
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
