# `config.py` Summary

## Role in Architecture
Provides the configuration management for the application. It handles loading, saving, migrating, and standardizing the JSON-based configuration state used across the entire Pandora app.

## Key Classes and Functions
- `ConfigManager` (Class): Contains static methods for configuration operations.
  - `load()`: Loads the `config.json` from the `AppData` directory. If missing or outdated, it applies extensive migration logic. It sets comprehensive default values for general settings, the halo menu, hub configurations, and folders. It also handles mapping older configurations and auto-importing missing storage items to ensure the config matches the file system state.
  - `save(data)`: Cleans out private/temporary keys (starting with `_`) and saves the configuration back to `config.json` in the `AppData` directory.
- Migration and Path Constants: The script sets up `APPDATA_DIR` to avoid permission issues when run as a compiled executable. It includes global logic to migrate old config files and storage from the project directory into the user's `AppData`.

## Dependencies and Interactions
- Relies heavily on the standard `os`, `json`, and `shutil` libraries for file manipulation.
- Interacts with the `AppData` folder to read/write `config.json` and `internal_storage/`.
- Is imported and utilized by nearly all components in the app (e.g., `main.py`, `ui_utils`, etc.) to get and update the app's state.
