# `hub.py` Summary

## Role in Architecture
`hub.py` acts as the orchestrator for the central radial menu hub (`HubManager`). It acts as a bridge between the core `Halo` radial menu and its inner content modules, intelligently switching the active context (e.g., MediaHub vs. TimeHub) based on what the user is currently doing.

## Key Classes and Functions
- `HubManager`:
  - `__init__`: Instantiates the inner hub variants (e.g., `MediaHub`, `TimeHub`, `DefaultLogoHub`) from the `hub_modules` package.
  - `reload_config`: Reads and applies settings specific to each layer from the `hub_config` section of the main settings.
  - `get_active_module`: Determines which module should be drawn and interacted with in the center of the Halo menu. It dynamically switches to `MediaHub` if media is currently playing, otherwise it defaults to `TimeHub`.
  - Event Handlers (`draw_active`, `handle_scroll`, `handle_mouse_move`, `handle_press`, `handle_key_press`, etc.): Routes UI and input events from the main `Halo` overlay down to the active internal module.

## Dependencies and Interactions
- Uses components from `hub_modules` (e.g., `MODULE_MAP`, `DefaultLogoHub`).
- Is instantiated and held by `ui.halo.Halo`.
- Examines `media_mgr.current_track` state to decide the active layout.
