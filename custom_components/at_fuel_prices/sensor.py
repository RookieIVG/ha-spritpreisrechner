"""Sensor platform for Austrian Fuel Prices."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ADDRESS,
    ATTR_CITY,
    ATTR_FUEL_LABEL,
    ATTR_IS_OPEN,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_POSTAL_CODE,
    ATTR_RANK,
    ATTR_STATION_ID,
    ATTR_STATION_NAME,
    CONF_FUEL_TYPE,
    CONF_STATION_COUNT,
    DEFAULT_FUEL_TYPE,
    DEFAULT_STATION_COUNT,
    DOMAIN,
    FUEL_TYPES,
    MAX_STATIONS,
)
from .coordinator import AtFuelConfigEntry, AtFuelDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtFuelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the rank-based price sensors for a config entry."""
    coordinator = entry.runtime_data

    count = entry.options.get(
        CONF_STATION_COUNT,
        entry.data.get(CONF_STATION_COUNT, DEFAULT_STATION_COUNT),
    )
    count = min(int(count), MAX_STATIONS)

    async_add_entities(
        AtFuelPriceSensor(coordinator, entry, rank) for rank in range(1, count + 1)
    )


class AtFuelPriceSensor(
    CoordinatorEntity[AtFuelDataUpdateCoordinator], SensorEntity
):
    """Represents the Nth-cheapest fuel station for a configured area."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "€/L"
    _attr_suggested_display_precision = 3
    _attr_icon = "mdi:gas-station"

    def __init__(
        self,
        coordinator: AtFuelDataUpdateCoordinator,
        entry: AtFuelConfigEntry,
        rank: int,
    ) -> None:
        """Initialise a single rank sensor."""
        super().__init__(coordinator)
        self._rank = rank
        # Fuel type may be changed later via the options flow.
        self._fuel_type = entry.options.get(
            CONF_FUEL_TYPE, entry.data.get(CONF_FUEL_TYPE, DEFAULT_FUEL_TYPE)
        )

        # Keep the fuel type out of the unique id so changing it later keeps the
        # same entities (only the prices change) instead of orphaning them.
        self._attr_unique_id = f"{entry.entry_id}_{rank}"
        self._attr_translation_key = "fuel_price_rank"
        self._attr_translation_placeholders = {"rank": str(rank)}
        # Fallback name if translations are unavailable.
        self._attr_name = f"Platz {rank}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="E-Control",
            model=FUEL_TYPES.get(self._fuel_type, self._fuel_type),
            entry_type=None,
            configuration_url="https://www.spritpreisrechner.at/",
        )

    @property
    def _station(self) -> dict[str, Any] | None:
        return self.coordinator.station_at(self._rank)

    @property
    def native_value(self) -> float | None:
        """Return the price in EUR per litre."""
        station = self._station
        if not station:
            return None
        return station["prices"][0].get("amount")

    @property
    def available(self) -> bool:
        """Available only when a station exists at this rank."""
        return super().available and self._station is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose station details, including lat/lon for the map card."""
        station = self._station
        if not station:
            return {ATTR_RANK: self._rank}

        location = station.get("location") or {}
        prices = station.get("prices") or [{}]

        return {
            ATTR_RANK: self._rank,
            ATTR_STATION_ID: station.get("id"),
            ATTR_STATION_NAME: station.get("name"),
            ATTR_ADDRESS: location.get("address"),
            ATTR_POSTAL_CODE: location.get("postalCode"),
            ATTR_CITY: location.get("city"),
            ATTR_LATITUDE: location.get("latitude"),
            ATTR_LONGITUDE: location.get("longitude"),
            ATTR_IS_OPEN: station.get("open"),
            ATTR_FUEL_LABEL: prices[0].get("label"),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write state on every coordinator refresh (station may have changed)."""
        self.async_write_ha_state()
