# `ui_dashboard_halo.js` Summary

## Role in Architecture
Manages the "Halo" tab in the Electron dashboard, configuring the radial HUD menu, media widgets, and time widgets.

## Key Classes and Functions
- **`HaloTab` class**:
  - `init()`: Binds settings for Halo activation (keybind, mode), visual theme, dimensions (blur, gap size, hub ratio, scroll sensitivity).
  - Handles Media Widget settings (Art Style, Visualizer, Mosaic Shape, Effect Strength). Specifically, it toggles visibility of certain settings based on the chosen "Art Style" (e.g. showing Mosaic options only if "8-Bit Mosaic" is selected).
  - Binds Time widget settings (mode, 24h format, date, seconds).
  - Injects `getConfig` and `sendUpdate` into the global `window` object so that the SVG radial renderer in `ui_dashboard_common.js` can utilize them.

## Dependencies and Interactions
- Requires utilities from `ui_dashboard_common.js`.
- Modifies `halo` and `hub_config.layers` in the configuration.
