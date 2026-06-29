# `ws_server.py` Summary

## Role in Architecture
The primary WebSocket server used to communicate in real-time between the Python backend and the Electron-based Dashboard frontend.

## Key Classes and Functions
- `WebSocketServerThread` (Inherits from `QThread`):
  - Binds to a dynamically assigned port (if `port=0`) to avoid conflicts.
  - Sends the assigned port to the main application via `port_bound` signal.
  - `handler()`: Accepts connections, immediately pushes an `init_config` payload, and listens for incoming payloads (e.g., `update_config`, `create_folder_at_cursor`).
  - `send_config_to_clients()`, `send_command_to_clients()`: Provide thread-safe methods (using `asyncio.run_coroutine_threadsafe`) for the main PyQt app to push config changes or arbitrary commands (like navigation commands) to the Electron clients.

## Dependencies and Interactions
- Uses the `websockets` package.
- Tightly integrated with PyQt6's `QThread` and signals for thread-safe cross-communication.
- Utilized directly by `ElectronDashboardManager` in `main.py` to sync state with the `ui_dashboard_*.js` frontend.
