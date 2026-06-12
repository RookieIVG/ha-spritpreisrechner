"""Minimal async client for the E-Control Spritpreisrechner API."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import async_timeout

from .const import API_SEARCH_BY_ADDRESS

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class EControlApiError(Exception):
    """Raised when the E-Control API cannot be reached or returns bad data."""


class EControlApiClient:
    """Tiny wrapper around the public E-Control gas-station search endpoint."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialise the client with a shared aiohttp session."""
        self._session = session

    async def async_get_stations(
        self,
        latitude: float,
        longitude: float,
        fuel_type: str,
        include_closed: bool,
    ) -> list[dict[str, Any]]:
        """Return the raw list of stations near the given coordinates.

        Only the cheapest five stations carry price information; this method
        returns the full list unfiltered so the coordinator can decide how to
        handle it.
        """
        params = {
            "latitude": f"{latitude:.6f}",
            "longitude": f"{longitude:.6f}",
            "fuelType": fuel_type,
            "includeClosed": "true" if include_closed else "false",
        }
        headers = {"Accept": "application/json"}

        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(
                    API_SEARCH_BY_ADDRESS, params=params, headers=headers
                )
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientResponseError as err:
            # 403/429 typically means the URL was throttled/banned for polling
            # too often.
            raise EControlApiError(
                f"E-Control API returned HTTP {err.status} "
                "(possible rate-limit ban — increase the scan interval)"
            ) from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EControlApiError(f"Error talking to E-Control API: {err}") from err

        if not isinstance(data, list):
            raise EControlApiError("Unexpected response shape from E-Control API")

        return data
