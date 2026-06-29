# `config.json` Summary

## Role in Architecture
Stores the serialized configuration data of the Pandora application. This file acts as the source of truth for the user's settings, folder structures, and app links.

## Key Contents
- `folders`: An array of folder objects, each defining its location (`pos`), `name`, internal items (`apps`), and visual properties (color, sort type, custom settings).
- `global_settings`: Defines global aesthetic and functional preferences, such as icon sizes, grid sizes, font sizes, opacity, blur settings, and color schemes.

## Dependencies and Interactions
- Managed exclusively through `config.py`'s `ConfigManager`.
- Synced actively to the Electron Dashboard via WebSockets (`ws_server.py`) and updated when changes occur in the UI.
