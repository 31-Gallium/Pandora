# `renderer.js` Summary

## Role in Architecture
The primary renderer process script that glues the HTML DOM to the dashboard logic modules and establishes the WebSocket connection to the Python core.

## Key Classes and Functions
- Initializes the `GeneralTab`, `HaloTab`, and `FoldersTab` objects, passing them a `getConfig()` getter and a `sendConfigUpdate()` trigger function.
- Connects to the local WebSocket server (started by `ws_server.py`) on port 8765 (or whatever is in `process.env.PANDORA_WS_PORT`).
- **WebSocket Handlers**:
  - `init_config` / `update_config`: Receives configuration blobs from Python, saves them locally, and triggers UI updates across all tabs. Hides the loading spinner once data arrives.
  - `show_folder`: Listens for a specific command to jump directly to the "Folders" tab and open a specific folder's editor view.

## Dependencies and Interactions
- Uses `ipcRenderer` to talk to `main.js` (for window controls).
- Uses the `ws` library for the WebSocket client.
- Imports `ui_dashboard_*.js` modules.
