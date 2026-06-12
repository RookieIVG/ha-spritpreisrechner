# Austrian Fuel Prices (E-Control) – Home Assistant Integration

A native Home Assistant integration that fetches Austrian fuel prices from the
[E-Control Spritpreisrechner](https://www.spritpreisrechner.at/) API – the same
source ÖAMTC, ARBÖ and friends use. Replaces the usual `rest:` + `template:`
sensor setup with a proper config-flow integration and a `DataUpdateCoordinator`.

## Features

- UI setup via config flow (pick the search location on a map).
- Diesel (`DIE`), Super 95 (`SUP`) and Autogas (`GAS`).
- Up to 5 rank-based price sensors (cheapest → 5th cheapest).
- Rich attributes per station: name, address, postal code, city, latitude,
  longitude, open/closed, fuel label, station id.
- Latitude/longitude attributes so stations show up on the Map card.
- Configurable update interval (with a 15-minute safety floor).

## Why only 5 stations?

E-Control deliberately only returns prices for the **five cheapest** stations
around a location, so individual stations can't be price-scraped. Therefore 5
is the hard maximum.

> ⚠️ Keep the update interval reasonable. If the API is polled too aggressively
> the **request URL** (not your IP) gets banned for about a day. The default is
> 30 minutes; the minimum is 15.

## Installation (HACS)

1. HACS → ⋮ → *Custom repositories*.
2. Add `https://github.com/RookieIVG/ha-at-fuel-prices`, category *Integration*.
3. Install, restart Home Assistant.
4. *Settings → Devices & Services → Add Integration → Austrian Fuel Prices*.

## Entities

For an instance named `Spritpreise Graz` with fuel type Diesel you get:

| Entity | State | Key attributes |
| --- | --- | --- |
| `sensor.spritpreise_graz_platz_1` | cheapest price (€/L) | `station_name`, `city`, `latitude`, … |
| `sensor.spritpreise_graz_platz_2` | 2nd cheapest | … |
| … | … | … |

(Entity ids depend on the name you choose.)

## Dashboard examples

### Price list (requires [`template-entity-row`](https://github.com/thomasloven/lovelace-template-entity-row))

```yaml
type: entities
title: Spritpreise Graz
entities:
  - type: custom:template-entity-row
    icon: mdi:gas-station-outline
    entity: sensor.spritpreise_graz_platz_1
    state: "{{ states('sensor.spritpreise_graz_platz_1') }} €/L"
    name: "{{ state_attr('sensor.spritpreise_graz_platz_1', 'station_name') }}"
    secondary: >-
      {{ state_attr('sensor.spritpreise_graz_platz_1', 'postal_code') }}
      {{ state_attr('sensor.spritpreise_graz_platz_1', 'city') }},
      {{ state_attr('sensor.spritpreise_graz_platz_1', 'address') | title }}
  # … repeat for platz_2 … platz_5
```

### Map of the cheapest stations

```yaml
type: map
title: Günstigste Tankstellen
entities:
  - sensor.spritpreise_graz_platz_1
  - sensor.spritpreise_graz_platz_2
  - sensor.spritpreise_graz_platz_3
  - sensor.spritpreise_graz_platz_4
  - sensor.spritpreise_graz_platz_5
```

The Map card reads the `latitude`/`longitude` attributes automatically.

## Notes on migrating from REST/template sensors

This integration replaces the old `rest:` + `template:` blocks entirely. The
biggest change vs. the template approach: attribute keys are now snake_case
(`postal_code`, `station_name`, `is_open`) and the price sensor's unit is
`€/L` with `state_class: measurement`, so you get proper long-term history
instead of `device_class: monetary`.

## License

MIT
