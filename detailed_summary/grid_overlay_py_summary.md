# `grid_overlay.py` Summary

## Role in Architecture
A full-screen, invisible-to-input overlay that draws the snapping grid (crosses and lines) to help the user align folders on the desktop.

## Key Classes and Functions
- **`GridOverlay` (QWidget)**:
  - Frameless, always-on-top, transparent-for-input tool window.
  - `paintEvent`: Computes an offset based on the primary screen's center to ensure the grid aligns perfectly regardless of monitor layout. Draws crosses and lines at `grid_size` intervals.
  - Animates its entrance (`entrance_anim`) using a radial "wave" effect starting from a `wave_origin` point.
  - Uses a hue-shifting animation (`_step_anim`) over time if `grid_animated_color` is enabled.

## Dependencies and Interactions
- Receives config (`grid_size`, `edge_padding`) directly from `main.py` or the `GridOverlay` instantiator.
- Called by `folder_panel.py` during dragging, or globally via a shortcut.
