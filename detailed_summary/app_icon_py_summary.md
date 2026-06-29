# `app_icon.py` Summary

## Role in Architecture
Represents an individual application icon or nested folder widget on the desktop. It is a `QWidget` inside a `FolderPanel`.

## Key Classes and Functions
- **`AppIcon` (QWidget)**:
  - Custom painting (`paintEvent`) handles rounded translucent backgrounds, icon extraction (`utils.IconExtractor`), and elided text (app name).
  - Handles drag-and-drop mechanics using `QDrag`. Implements logic to drop on other folder panels, the desktop, or create a `GhostWidget` for internal dragging visualization.
  - Generates mini-mosaics inside the icon for nested folders.
  - Instantiates a context menu (`AnimatedMenu`) on right click for renaming, pinning, and removing.
- **`GhostWidget` (QWidget)**:
  - A frameless, always-on-top tooltip widget that visually follows the cursor during drag operations when moving icons within or between folders.

## Dependencies and Interactions
- Uses `IconExtractor` and `VectorIcon` to get icon images.
- Integrates with `folder_panel.py` to trigger layout refreshes after a drag/drop operation.
