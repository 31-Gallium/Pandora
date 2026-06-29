# `base.py` (hub_modules) Summary

## Role in Architecture
Defines the `BaseHubModule` class, which serves as the interface and foundational class for all modules that can be displayed in the center "dead zone" of the Halo menu.

## Key Classes and Functions
- **`BaseHubModule`**:
  - `__init__(self, manager)`: Accepts a `HubManager` reference.
  - `load_settings(self, settings)`: Populates module-specific configuration.
  - `draw(self, p, cx, cy, inner_radius)`: Overridable method where the module handles its own painting within the center of the radial menu.
  - Event handlers: `on_mouse_press`, `on_mouse_release`, `on_wheel` allow the module to intercept input when the user interacts with the center of the Halo menu.

## Dependencies and Interactions
- Inherited by `clock.py`, `default.py`, and `media.py`.
