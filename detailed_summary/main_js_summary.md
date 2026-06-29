# `main.js` Summary

## Role in Architecture
The main process entry point for the Electron dashboard application. It creates and manages the actual OS-level configuration window.

## Key Classes and Functions
- `createWindow()`: Spawns a frameless, transparent `BrowserWindow` pointing to `index.html`. Sets `nodeIntegration: true` to allow frontend JS to use Node.js modules.
- `ipcMain` Event Listeners:
  - `close-window`: Quits the application.
  - `minimize-window`: Minimizes the dashboard.
  - `dialog:openFile`: Opens a native file dialog specifically configured to select images (png, svg, jpg, jpeg) for custom folder icons or cover art.

## Dependencies and Interactions
- Uses the `electron` API (`app`, `BrowserWindow`, `ipcMain`, `nativeTheme`).
- Does not run the Python core; it is entirely standalone, launched as a subprocess by `main.py` when the user requests settings.
