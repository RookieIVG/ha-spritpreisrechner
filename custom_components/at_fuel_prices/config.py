"""Config and options flow for Austrian Fuel Prices."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    LocationSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_FUEL_TYPE,
    CONF_INCLUDE_CLOSED,
    CONF_LOCATION,
    CONF_LOCATION_MODE,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_STATION_COUNT,
    CONF_TRACKED_ENTITY,
    DEFAULT_FUEL_TYPE,
    DEFAULT_INCLUDE_CLOSED,
    DEFAULT_LOCATION_MODE,
    DEFAULT_STATION_COUNT,
    DOMAIN,
    FUEL_TYPES,
    LOCATION_MODE_ENTITY,
    LOCATION_MODE_FIXED,
    MAX_STATIONS,
    MIN_SCAN_INTERVAL_MINUTES,
)

FUEL_OPTIONS = [
    SelectOptionDict(value=code, label=label) for code, label in FUEL_TYPES.items()
]

LOCATION_MODE_VALUES = [LOCATION_MODE_FIXED, LOCATION_MODE_ENTITY]


def _fuel_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=FUEL_OPTIONS, mode=SelectSelectorMode.DROPDOWN)
    )


def _location_mode_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=LOCATION_MODE_VALUES,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="location_mode",
        )
    )


def _entity_selector() -> EntitySelector:
    return EntitySelector(
        EntitySelectorConfig(
            filter=EntityFilterSelectorConfig(domain=["person", "device_tracker"])
        )
    )


def _station_count_selector() -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=1, max=MAX_STATIONS, step=1, mode=NumberSelectorMode.SLIDER
        )
    )


def _scan_interval_selector() -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=MIN_SCAN_INTERVAL_MINUTES,
            max=720,
            step=5,
            unit_of_measurement="min",
            mode=NumberSelectorMode.BOX,
        )
    )


def _normalise(user_input: dict[str, Any]) -> dict[str, Any]:
    """Coerce numeric fields and ensure the tracked-entity key always exists."""
    user_input[CONF_STATION_COUNT] = int(user_input[CONF_STATION_COUNT])
    if CONF_SCAN_INTERVAL_MINUTES in user_input:
        user_input[CONF_SCAN_INTERVAL_MINUTES] = int(
            user_input[CONF_SCAN_INTERVAL_MINUTES]
        )
    user_input.setdefault(CONF_TRACKED_ENTITY, None)
    location = user_input.get(CONF_LOCATION) or {}
    user_input[CONF_LOCATION] = {
        CONF_LATITUDE: location.get(CONF_LATITUDE),
        CONF_LONGITUDE: location.get(CONF_LONGITUDE),
    }
    return user_input


class AtFuelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect location source, fuel type and number of stations."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mode = user_input[CONF_LOCATION_MODE]
            tracked = user_input.get(CONF_TRACKED_ENTITY)

            if mode == LOCATION_MODE_ENTITY and not tracked:
                errors["base"] = "no_tracked_entity"
            else:
                user_input = _normalise(user_input)
                fuel_type = user_input[CONF_FUEL_TYPE]
                location = user_input[CONF_LOCATION]

                if mode == LOCATION_MODE_ENTITY:
                    unique_id = f"{tracked}_{fuel_type}"
                else:
                    unique_id = (
                        f"{location[CONF_LATITUDE]:.4f}_"
                        f"{location[CONF_LONGITUDE]:.4f}_{fuel_type}"
                    )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        default_location = {
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
        }

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Spritpreise"): str,
                vol.Required(
                    CONF_LOCATION_MODE, default=DEFAULT_LOCATION_MODE
                ): _location_mode_selector(),
                vol.Required(
                    CONF_LOCATION, default=default_location
                ): LocationSelector(),
                vol.Optional(CONF_TRACKED_ENTITY): _entity_selector(),
                vol.Required(
                    CONF_FUEL_TYPE, default=DEFAULT_FUEL_TYPE
                ): _fuel_selector(),
                vol.Required(
                    CONF_STATION_COUNT, default=DEFAULT_STATION_COUNT
                ): _station_count_selector(),
                vol.Required(
                    CONF_INCLUDE_CLOSED, default=DEFAULT_INCLUDE_CLOSED
                ): BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> AtFuelOptionsFlow:
        """Return the options flow handler."""
        return AtFuelOptionsFlow()


class AtFuelOptionsFlow(OptionsFlow):
    """Allow changing the location source and all operational settings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        data = self.config_entry.data
        options = self.config_entry.options

        def current(key: str, default: Any = None) -> Any:
            return options.get(key, data.get(key, default))

        if user_input is not None:
            mode = user_input[CONF_LOCATION_MODE]
            if mode == LOCATION_MODE_ENTITY and not user_input.get(CONF_TRACKED_ENTITY):
                errors["base"] = "no_tracked_entity"
            else:
                return self.async_create_entry(title="", data=_normalise(user_input))

        default_location = current(
            CONF_LOCATION,
            {
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
            },
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_LOCATION_MODE,
                    default=current(CONF_LOCATION_MODE, DEFAULT_LOCATION_MODE),
                ): _location_mode_selector(),
                vol.Required(
                    CONF_LOCATION, default=default_location
                ): LocationSelector(),
                vol.Optional(
                    CONF_TRACKED_ENTITY,
                    description={"suggested_value": current(CONF_TRACKED_ENTITY)},
                ): _entity_selector(),
                vol.Required(
                    CONF_FUEL_TYPE,
                    default=current(CONF_FUEL_TYPE, DEFAULT_FUEL_TYPE),
                ): _fuel_selector(),
                vol.Required(
                    CONF_STATION_COUNT,
                    default=current(CONF_STATION_COUNT, DEFAULT_STATION_COUNT),
                ): _station_count_selector(),
                vol.Required(
                    CONF_INCLUDE_CLOSED,
                    default=current(CONF_INCLUDE_CLOSED, DEFAULT_INCLUDE_CLOSED),
                ): BooleanSelector(),
                vol.Required(
                    CONF_SCAN_INTERVAL_MINUTES,
                    default=options.get(CONF_SCAN_INTERVAL_MINUTES, 30),
                ): _scan_interval_selector(),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
