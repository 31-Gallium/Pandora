# `ui_dashboard_folders.js` Summary

## Role in Architecture
Manages the "Folders" tab in the Electron dashboard, allowing the user to create, edit, and configure custom folder widgets.

## Key Classes and Functions
- **`FoldersTab`**: A class that encapsulates folder configuration logic.
- `init()`: Binds the "Add Folder" button to create a new folder object with a UUID.
- `updateUI(cfg)`: Renders the list of current folders.
- `renderEditor(folder)`: Populates the folder settings editor view (name, show title, pill mode, pill icon path). Handles switching between the list view and the editor view.
- Supports picking a custom icon file via IPC (`dialog:openFile`).

## Dependencies and Interactions
- Requires utilities from `ui_dashboard_common.js`.
- Modifies the `folders` array in the main configuration.
