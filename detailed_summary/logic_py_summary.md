# `logic.py` Summary

## Role in Architecture
Contains the core business logic for handling app drag-and-drop operations across folders, updating configuration state, and triggering UI refreshes.

## Key Classes and Functions
- **`handle_app_drop(cfg, target_folder_data, mime_data, e_source, is_target_pinned, target_idx, dashboard=None)`**:
  - The central coordinator for processing a dropped item.
  - Parses the JSON payload from the `mime_data` payload.
  - Checks if the item is moving between folders, dropping onto the desktop, or just being reordered within the same folder.
  - Moves the physical `.lnk` or executable file via `shutil.move` if crossing folder boundaries and handling name collisions.
  - Updates the shared `cfg` in-memory object (removing from source folder array, inserting into target folder array).
  - Handles preserving the 'pinned' state logic (if standard sort is used) or custom sorting.
  - Calls `refresh()` and `update()` on the relevant UI instances to reflect the changes immediately without restarting.

## Dependencies and Interactions
- Modifies data loaded via `config.py`.
- Manipulates files in `STORAGE_PATH`.
- Triggers UI updates in `folder_panel.py` and `ui/app_icon.py`.
