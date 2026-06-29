# `media_daemon.py` Summary

## Role in Architecture
A robust, threaded backend service that bridges Pandora with the Windows 10/11 System Media Transport Controls (SMTC) API. It handles media playback status, timeline scraping, thumbnail extraction, and per-app volume monitoring.

## Key Classes and Functions
- `MediaState` (Dataclass): A container for holding all relevant media info (title, artist, album, status, timeline position/duration, volume, available media sessions).
- `MediaDaemon` (QObject): 
  - Runs its own `asyncio` loop in a background thread to prevent the PyQt UI from lagging due to COM/WinRT marshalling overhead.
  - `_init_gsm()`: Connects to the `GlobalSystemMediaTransportControlsSessionManager` (SMTC).
  - `_refresh_sessions()`: Tracks all available media sessions (e.g., Spotify, Chrome, Apple Music) and assigns UUIDs, picking the "best" active session to lock onto.
  - `_sync_full_state()`, `_sync_playback_state()`, `_sync_timeline()`: Continuously poll and interpolate media states, compensating for delays in the native Windows API.
  - `_safe_extract_thumbnail()`: Asynchronously reads the media thumbnail stream, buffers it, converts it to a `QImage`, and caches it to prevent disk thrashing.
  - `_peak_polling_thread()`: A dedicated thread that uses `pycaw` to constantly monitor the audio peak level for visualizations without blocking the SMTC event loop.

## Dependencies and Interactions
- Emits PyQt `pyqtSignal` events (`state_changed`, `thumbnail_ready`) that are consumed by the UI (e.g., `MediaSessionManager` in `utils.py`).
- Uses `winsdk.windows.media.control` to talk to Windows Media.
- Uses `pycaw` for volume and audio peak polling.
- Uses `asyncio`, `threading`, and `pythoncom`.
