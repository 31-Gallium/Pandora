# `ui_utils.py` Summary

## Role in Architecture
Provides shared drawing utilities for rendering the visual representation of a folder, primarily focusing on drawing the collapsed thumbnail view.

## Key Classes and Functions
- **`resolve_folder_setting`**: Resolves styling parameters (size, colors, glow intensity) by falling back through a hierarchy: local instance settings -> size presets -> hardcoded defaults (`_DEFAULTS`).
- **`draw_folder_thumbnail(p, rect, data, cfg, local_settings=None, hover_progress=0.0, paging_params=None)`**:
  - The core drawing routine for a folder's icon.
  - Draws the glowing backdrop (using `QRadialGradient`).
  - Scales the entire composition based on `hover_progress` for smooth interactive zoom.
  - Draws the glassmorphism background rounded rectangle.
  - Iterates over the first N apps (based on page index) and uses the selected layout engine (`grid` or `flower`) to position and draw miniature versions of their icons using `IconExtractor`.
  - Animates the icon transitions during a page scroll by blending `p_pos` and `opacity`.

## Dependencies and Interactions
- Retrieves icons using `IconExtractor`.
- Uses layout engines from `layout_logic.py`.
- Called directly by `AppIcon.paintEvent` when rendering a nested folder.
