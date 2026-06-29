# `ui_dashboard_general.js` Summary

## Role in Architecture
Manages the "General" tab in the Electron dashboard, handling global appearance settings, display effects, and keybinds.

## Key Classes and Functions
- **`applyDashboardTheme(cfg)`**: Reads the configured theme and applies corresponding classes (like `light-theme`) or dynamically injects extracted desktop accent colors as CSS variables.
- **`GeneralTab` class**:
  - `init()`: Binds sliders for grid size, grid opacity, and hierarchical edge padding (syncing uniform/horizontal/vertical padding sliders).
  - Handles the custom color picker for Folder themes (HSV to RGB conversion, canvas dragging for hue/saturation selection).
  - Records global keyboard shortcuts (Launch app, Open folder, Show menu) using a `keydown` listener and maps them to Virtual Key (VK) codes.
  - `updateUI(cfg)`: Applies loaded config values back to the HTML controls.

## Dependencies and Interactions
- Requires utilities from `ui_dashboard_common.js`.
- Modifies `general_settings` and `display_effects` in the config.
