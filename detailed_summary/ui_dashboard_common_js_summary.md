# `ui_dashboard_common.js` Summary

## Role in Architecture
Provides shared utilities, global UI initialization, and state management functions that are used across all specific tab controllers in the Electron dashboard.

## Key Classes and Functions
- **Input Binding Helpers**: `bindInput` and `bindSlider` map HTML inputs directly to specific nested paths in the JSON configuration, automatically triggering UI and backend updates on change.
- **`initGlobalUI()`**: Sets up tab switching, sidebar toggling, search pill logic (searching for settings by name and scrolling to them), and custom color picker logic.
- **Halo Radial Render**: Contains a significant block of SVG manipulation logic (`renderHaloRadial`) for drawing the interactive radial menu preview in the Sandbox.
- **Sandbox IPC**: Provides `updateSandboxRect()` which asks the Python core to move the transparent `sandbox_server.py` window to overlay the correct area on screen.

## Dependencies and Interactions
- Uses `ipcRenderer` to talk to `main.js`.
- Interacts with all dashboard tabs, acting as the foundation for user interactions.
