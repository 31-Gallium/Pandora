# `README.md` Summary

## Role in Architecture
The main user-facing documentation for the Pandora repository. It introduces the project, highlights its main features, and provides usage instructions.

## Key Contents
- **Key Features**: Explains native desktop integration (Win+D bypass via `Progman` reparenting), Radial HUD & System Tools (smart warmth system, volume arc), Info Pill Guidance (floating contextual help), Advanced Grid Snapping, Fluid Animations, and Ultimate Customizability.
- **How to Use**: Instructions on how to launch the app (`python main.py`), open the Radial HUD, access the Dashboard via the system tray, and use the Snip tool.
- **Architecture Details**: Briefly outlines the technical stack (PyQt6 frontend, `ctypes` system hooks, WinAPI display effects, and JSON-based persistence).

## Dependencies and Interactions
- Standard markdown file for repository viewers. Reflects the capabilities implemented in `main.py`, `utils.py`, and the `ui/` folder.
