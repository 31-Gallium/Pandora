# `clock.py` (hub_modules) Summary

## Role in Architecture
A Hub Module that renders a highly customized Clock (both digital and analog) in the center of the Halo menu. It supports world clocks and timezones.

## Key Classes and Functions
- **`TimeHub(BaseHubModule)`**:
  - `draw()`: Calculates the current time (factoring in the active timezone) and routes rendering to `_draw_analog` or `_draw_digital`.
  - `_draw_digital()`: Renders the digital clock with sweeping progress rings for seconds.
  - `_draw_analog()`: Renders a traditional analog clock face with hour/minute/second hands and tick marks.
  - Handles key presses (Spacebar) to trigger an override menu on the main Halo radial UI, injecting world clock shortcuts to allow the user to quickly swap timezones.
  - Supports robust timezone fallbacks with hardcoded offsets if the IANA database is unavailable.

## Dependencies and Interactions
- Imports from `datetime`, `zoneinfo`.
- Mutates the main configuration via `ConfigManager` when a new timezone is selected.
- Uses `HubManager.halo.set_override_tools()` to dynamically change the outer radial menu into a timezone selector.
