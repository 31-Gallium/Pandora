# `sandbox_server.py` Summary

## Role in Architecture
A standalone PyQt6 widget application designed to act as a "Live Preview" (Sandbox) embedded *over* the Electron dashboard. Because Electron uses HTML/CSS but Pandora draws real desktop widgets using PyQt6, this script creates an invisible, always-on-top frameless window that matches the coordinates of a designated area in the Electron UI, rendering a live, pixel-perfect preview of a folder widget.

## Key Classes and Functions
- `SandboxWindow`: 
  - Frameless, transparent, `Tool`, `WindowStaysOnTopHint`.
  - Instantiates actual Pandora UI components (`SandboxFolderIcon`, `SandboxFolderView`) from `ui_dashboard_common.py` to ensure the preview looks exactly like the real desktop widget.
  - Implements a fade-in/fade-out animation when repositioning or hiding.
- `StdinReader`: Runs in a daemon thread. Constantly reads JSON commands from standard input.
  - Commands include: `set_mode` (collapsed/expanded), `set_bg`, `update_config`, `show` (moves the window to specific x, y, width, height coordinates), and `hide`.

## Dependencies and Interactions
- Uses `PyQt6`.
- Is spawned as a child process by the Electron Dashboard, which writes position data and configuration updates into `sandbox_server.py`'s `stdin`.
- Reads `config.json` via `ConfigManager` but primarily updates via `stdin` pipelines.
