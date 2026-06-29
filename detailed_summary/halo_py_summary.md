# `halo.py` Summary

## Role in Architecture
The massive full-screen radial HUD (Halo Menu) that acts as Pandora's quick-access launcher and system controller.

## Key Classes and Functions
- **`Halo` (QWidget)**:
  - Renders a multi-layered, customizable radial menu with animated slices, icons, and text labels.
  - Intercepts mouse movement globally (when active) using a unified `anim_timer` to interpolate the cursor's logical position within the radial menu bounds.
  - Supports dynamic layers (`menus`) that can be cycled through using the mouse scroll wheel.
  - Integrates deeply with Windows Acrylic Blur via `ctypes` for its background.
  - Detects hovering over specific tools (like 'Mute' or 'Night Light') and overrides scroll wheel behavior to act as an adjustment dial (e.g., changing volume instead of changing layers).
  - Contains a `HubManager` (`hub_manager.py`) which manages the inner circle (Media visualizer, Clock).

## Dependencies and Interactions
- Heavily relies on `utils.py` (e.g. `VectorIcon`, `change_system_volume`, `DisplayEffectsEngine`).
- Relies on `hub.py`/`HubManager` for the center widget logic.
- Emits a `command_triggered` signal back to `main.py` when an action is selected.
