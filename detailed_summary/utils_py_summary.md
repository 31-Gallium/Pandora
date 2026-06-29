# `utils.py` Summary

## Role in Architecture
A massive utility library that provides low-level system integrations, Windows API wrappers, media control hooks, visual effects, and icon management.

## Key Classes and Functions
- `WinAPI`: Static methods to interact with Windows (e.g., `allow_drag_drop`, `set_modern_visuals` using DwmApi and BlurWindow, `pin_to_workerw` to embed windows on the desktop background).
- `IconExtractor`: A robust caching system that extracts and formats icons from executables, shortcuts (`.lnk`, `.url`), and UWP apps using COM (`win32com`, `ole32`, `shell32`). Includes logic for autocropping and generating "missing file" visual badges.
- `VectorIcon`: Loads, tints, caches, and renders SVGs and custom vector shapes (e.g., play, pause, volume, battery icons) dynamically using `QPainter`.
- `MediaSessionManager`: A PyQt-friendly reactive wrapper around the `MediaDaemon`, offering a clean API (signals) for UI components to respond to media/volume changes and scrub timelines without blocking.
- `DisplayEffectsEngine`: A hardware-accelerated screen filter engine using Windows Gamma Ramps (`GetDeviceGammaRamp` / `SetDeviceGammaRamp`) to apply zero-latency visual effects like "Sunset" or "Eye Saver" modes.
- `get_desktop_accent_colors()`: Extracts a palette of dominant accent colors from the user's current Windows desktop wallpaper using PIL and fast octree quantization.
- Volume management functions (`change_system_volume`, `get_system_volume_level`, `get_system_mute`) using `pycaw`.

## Dependencies and Interactions
- Uses `ctypes`, `pythoncom`, `win32com`, `pycaw` for deep Windows integration.
- Relies on `PyQt6` for `QPixmap`, `QPainter`, and `QObject` signals.
- Used pervasively by UI components (like `folder_panel.py`, `halo.py`) to fetch icons and manage window rendering styles.
