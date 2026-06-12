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
    LocationSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)

from .const import (
    CONF_FUEL_TYPE,
    CONF_INCLUDE_CLOSED,
    CONF_LOCATION,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_STATION_COUNT,
    DEFAULT_FUEL_TYPE,
    DEFAULT_INCLUDE_CLOSED,
    DEFAULT_STATION_COUNT,
    DOMAIN,
    FUEL_TYPES,
    MAX_STATIONS,
    MIN_SCAN_INTERVAL_MINUTES,
)

FUEL_OPTIONS = [
    SelectOptionDict(value=code, label=label) for code, label in FUEL_TYPES.items()
]


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


class AtFuelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect location, fuel type and number of stations."""
        errors: dict[str, str] = {}

        if user_input is not None:
            location = user_input[CONF_LOCATION]
            fuel_type = user_input[CONF_FUEL_TYPE]

            # Prevent duplicate entries for the same spot + fuel type.
            unique_id = (
                f"{location[CONF_LATITUDE]:.4f}_"
                f"{location[CONF_LONGITUDE]:.4f}_{fuel_type}"
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_LOCATION: {
                        CONF_LATITUDE: location[CONF_LATITUDE],
                        CONF_LONGITUDE: location[CONF_LONGITUDE],
                    },
                    CONF_FUEL_TYPE: fuel_type,
                    CONF_STATION_COUNT: int(user_input[CONF_STATION_COUNT]),
                    CONF_INCLUDE_CLOSED: user_input[CONF_INCLUDE_CLOSED],
                },
            )

        default_location = {
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
        }

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Spritpreise"): str,
                vol.Required(CONF_LOCATION, default=default_location): LocationSelector(),
                vol.Required(
                    CONF_FUEL_TYPE, default=DEFAULT_FUEL_TYPE
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=FUEL_OPTIONS, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
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
    """Allow changing scan interval, station count and closed-stations toggle."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            user_input[CONF_STATION_COUNT] = int(user_input[CONF_STATION_COUNT])
            user_input[CONF_SCAN_INTERVAL_MINUTES] = int(
                user_input[CONF_SCAN_INTERVAL_MINUTES]
            )
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data
        options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_STATION_COUNT,
                    default=options.get(
                        CONF_STATION_COUNT,
                        data.get(CONF_STATION_COUNT, DEFAULT_STATION_COUNT),
                    ),
                ): _station_count_selector(),
                vol.Required(
                    CONF_INCLUDE_CLOSED,
                    default=options.get(
                        CONF_INCLUDE_CLOSED,
                        data.get(CONF_INCLUDE_CLOSED, DEFAULT_INCLUDE_CLOSED),
                    ),
                ): BooleanSelector(),
                vol.Required(
                    CONF_SCAN_INTERVAL_MINUTES,
                    default=options.get(CONF_SCAN_INTERVAL_MINUTES, 30),
                ): _scan_interval_selector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
