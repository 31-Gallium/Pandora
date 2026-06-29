# `main.py` Summary

## Role in Architecture
`main.py` is the main entry point for the Pandora application. It initializes the application, sets up global hooks, integrates core services (media daemon, electron dashboard, halo menu, folder panels), and manages the system tray.

## Key Classes and Functions
- `GlobalHook`: Sets up low-level Windows keyboard and mouse hooks to intercept input (e.g., to activate the Halo menu, block input when active, and support custom hub keybinds).
- `handle_halo_cmd`: Executes commands triggered from the Halo menu (e.g., open browser, toggle grid, take a screenshot, adjust display effects).
- `ElectronDashboardManager`: Manages the Electron-based settings dashboard. It spawns the Electron process, starts a WebSocket server (`ws_thread`) to communicate with it, and handles configuration synchronization and application updates.
- `CustomTrayMenu`: A borderless, custom-styled system tray popup menu that allows quick access to settings, folder creation, grid toggling, restarting, and quitting.
- `create_folder`: Logic to spawn a new folder on the desktop. It calculates available grid space to place the folder without overlapping existing ones, or falls back to cursor position.
- Application initialization (`if __name__ == "__main__":` block): Sets up PyQt6 `QApplication`, configures crash handlers, initializes `MediaDaemon`, `Halo`, `GridOverlay`, tray icons, and instantiates the `FolderPanel` instances based on the loaded configuration.

## Dependencies and Interactions
- Uses `PyQt6` heavily for UI components and application loop.
- Interacts with `core_services.media_daemon.MediaDaemon` and `core_services.ws_server.WebSocketServerThread`.
- Integrates `ui.halo.Halo`, `ui.folder_panel.FolderPanel`, `ui.grid_overlay.GridOverlay`.
- Uses `utils.py` for icon extraction, vector icons, and `DisplayEffectsEngine`.
- Relies on `ctypes` for low-level Windows hooks (`SetWindowsHookExW`).
