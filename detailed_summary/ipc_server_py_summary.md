# `ipc_server.py` Summary

## Role in Architecture
Provides an asynchronous WebSocket server specifically designed for Inter-Process Communication (IPC). This enables separate processes (like the Electron dashboard) to send and receive real-time configuration updates.

## Key Classes and Functions
- `IPCServer` (Class):
  - `handler(websocket)`: Async coroutine that registers clients, sends the initial config upon connection, and listens for `update_config` and `get_config` messages. When a config update is received, it saves it and triggers a callback.
  - `_main()`: Uses `websockets.serve` to run the server on `localhost:8765`.
  - `start()`: Launches the `asyncio` event loop in a separate background daemon `threading.Thread`.
  - `broadcast_config()`: A thread-safe method to push the current `ConfigManager` state to all connected clients.

## Dependencies and Interactions
- Relies on the `asyncio` and `websockets` libraries.
- Interacts with `ConfigManager` to load/save data.
- While `ws_server.py` seems to be the primary WebSocket handler used by `main.py`, `ipc_server.py` provides similar functionality and may be a legacy or alternate implementation.
