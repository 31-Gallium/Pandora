# `folder_panel.py` Summary

## Role in Architecture
The core visual container (folder) that sits on the desktop, housing multiple `AppIcon` instances arranged in a grid.

## Key Classes and Functions
- **`FolderPanel` (QWidget)**:
  - Frameless, translucent tool window that stays on the bottom of the window stack (desktop level).
  - Uses `ctypes` and `dwmapi` to enable Windows 11 Acrylic blur (`ACCENT_ENABLE_ACRYLICBLURBEHIND`).
  - Contains paging logic (`_get_page_size()`, `page_idx`) to handle folders with more apps than fit on a single page, drawing pagination pills/progress lines.
  - `_layout_icons()`: Calculates positions based on the `grid_cols` and `grid_rows` and triggers `QPropertyAnimation` to smoothly slide icons into place.
  - Handles mouse hover states with a custom top pill (title or icon mode) that slides in from outside the bounds.
  - Implements liquid "drag scroll" indicators using cubic bezier curves when an icon is dragged to the edge of the panel.

## Dependencies and Interactions
- Instantiates `AppIcon` widgets.
- Relies on `WinAPI` for desktop pinning (`pin_to_workerw`).
- Modifies `config.json` via `ConfigManager` when changes occur.
