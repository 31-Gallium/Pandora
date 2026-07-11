# Software Requirements Specification (SRS) for Pandora

## 1. Introduction

### 1.1 Purpose
This document outlines the complete software requirements for the "Pandora" application. It describes the system's architecture, functional and non-functional requirements, target environment, deployment model, and user interactions.

### 1.2 Scope
Pandora is a desktop productivity and customization suite built with Python (PyQt6) for the core engine and Electron for the settings dashboard. It provides highly interactive, visually customizable floating "folders" on the desktop, a radial HUD launcher (Halo) with integrated media controls and a world clock, a snap-to-grid alignment system, and a hardware-accelerated display effects engine. The application installs via a custom Electron-based installer and runs as a background system tray application on Windows.

### 1.3 Definitions, Acronyms, and Abbreviations
* **GUI**: Graphical User Interface
* **SRS**: Software Requirements Specification
* **App Icon**: A shortcut, executable, file, or nested folder represented as a visual tile inside a Pandora folder.
* **Dashboard**: The Electron-based central settings and management UI.
* **Halo**: The radial quick-access HUD menu, activated via a configurable hotkey.
* **Hub**: The inner circle of the Halo menu, dynamically displaying media controls, a clock, or the Pandora logo.
* **Dynamic Island**: Floating, frameless, animated dialogs (rename, confirm, hover name pill) that drop from the top of the screen.
* **Info Pill**: The centralized guidance HUD at the bottom of the dashboard.
* **SMTC**: System Media Transport Controls — the Windows API for interacting with media sessions.

---

## 2. Overall Description

### 2.1 Product Perspective
Pandora operates as a standalone desktop utility on the Windows operating system. It runs in the background via the system tray and renders borderless, transparent, frameless PyQt6 windows on the desktop to represent user-created folders. It communicates with an Electron-based settings dashboard over a local WebSocket connection for real-time configuration synchronization. User data and configuration are stored in `%APPDATA%\Pandora`.

### 2.2 Product Functions
* **Creation of Custom Folders**: Users can create multiple independent folder widgets on their desktop.
* **Drag-and-Drop Management**: Users can drag files, URLs, executables, and shortcuts into the folders. Files are physically stored in `%APPDATA%\Pandora\internal_storage\<folder_id>`.
* **Paginated Grid UI**: Folders display their contents in an always-visible paginated grid with smooth animated icon transitions between pages.
* **Deep Customization**: Users can change sizes, colors, glow effects, hover animations, folder themes (Default/Desktop/Custom Color), pagination style, theme intensity, and grid snap for all folders globally or individually.
* **App Search and Sorting**: Quick search inside an opened folder and multiple sorting options (Name, Type, Size, Date, Recently Added, Custom Order).
* **Batch Launching**: Ability to launch all contents of a folder simultaneously.
* **Halo Radial HUD**: Multi-layered circular menu (up to 9 layers) with configurable tools, volume arc, and display effects dial.
* **Integrated Media Controls**: Real-time media playback status, album art, audio-reactive visualizers, timeline scrubbing, and per-app volume control within the Halo hub.
* **World Clock**: Digital and analog clock modes with timezone switching within the Halo hub.
* **Display Effects Engine**: Hardware-accelerated screen filter using Windows Gamma Ramps for Night Light modes (Sunset, Reading, Movie, Eye Saver).
* **Desktop Snap Grid**: A full-screen alignment grid with animated wave entrance, hue-shifting colors, and configurable padding.
* **Dynamic Island Dialogs**: Floating rename, delete confirmation, and folder name hover pill toasts.
* **Custom Installer/Uninstaller**: Electron-based branded installer with data backup and full residue cleanup on uninstall.

### 2.3 User Classes and Characteristics
* **Power Users/Gamers**: Users who want a clean desktop but quick access to games and tools, appreciating high-fidelity animations and visual aesthetics.
* **Customization Enthusiasts**: Users who heavily theme their desktop environments and require deep aesthetic control over widgets.

### 2.4 Operating Environment
* **Platform**: Windows 10/11 (relies on WinAPI, DwmApi, COM, and WinRT for visual hooks, media transport, and monitor gamma control).
* **Runtime**: Python 3.x with PyQt6 (core engine), Electron (settings dashboard and installer).
* **Build**: PyInstaller (Python to exe), electron-packager (dashboard to exe), electron-builder (installer to portable exe).

---

## 3. System Architecture

### 3.1 Process Model
The application runs as multiple cooperating processes:
1. **Pandora.exe** (Python/PyQt6): The main process. Manages the system tray, folder panels, Halo HUD, grid overlay, media daemon, and global hooks.
2. **PandoraUI.exe** (Electron): The settings dashboard. Spawned as a child process when the user opens settings. Communicates via WebSocket.

### 3.2 Communication
* **WebSocket** (`WebSocketServerThread`): A dynamically-bound WebSocket server runs in a QThread. The Electron dashboard connects as a client. Messages include `init_config`, `update_config`, `create_folder_at_cursor`, and `show_folder`.

### 3.3 Data Storage
* **Configuration**: `%APPDATA%\Pandora\config.json` — A single JSON file holding all settings (general, halo, hub, folders). Written atomically via a `.tmp` + `os.replace` pattern to prevent corruption.
* **Internal Storage**: `%APPDATA%\Pandora\internal_storage\<folder_id>\` — Physical files dragged into Pandora folders.
* **Logs**: `%APPDATA%\Pandora\logs\session_<timestamp>.log` — Per-session log files.

---

## 4. System Features

### 4.1 Desktop Folder Widgets
* **Description**: The core visual component. Independent frameless widgets that sit on the desktop, always displaying their contents in a paginated grid.
* **Functional Requirements**:
  * The system shall render borderless, translucent widgets on the desktop using DwmApi Acrylic Blur.
  * The widgets shall be pinned to the desktop background layer via `WorkerW` (`WinAPI.pin_to_workerw`).
  * The widgets shall be draggable and resizable by the user.
  * The position, size, and grid dimensions of each folder shall be saved persistently.
  * The widgets shall display application icons in a paginated grid format with configurable columns and rows.
  * The widgets shall feature interactive hover animations (scaling and glowing via `QRadialGradient`).
  * A title pill or icon pill shall be configurable for folder identification on hover.
  * An optional custom cover image with blur effects may be set per folder.
  * The system shall support scrolling via mouse wheel through pages, with liquid drag-scroll indicators using cubic bezier curves.
  * The user shall be able to drag and drop to reorder icons within the grid, move icons between folders, or drop icons onto the desktop.
  * The view shall provide an inline search bar to filter visible icons.
  * The view shall provide options to sort icons by Name, Type, Size, Date, Recently Added, and Custom Order.
  * Right-click context menus (via a custom frameless `QDialog` based `AnimatedMenu` to bypass Windows 11 DWM bugs) shall offer rename, pin, and remove operations.
  * Rename and delete operations shall use Dynamic Island-style floating dialogs (`IslandRenameDialog`, `IslandConfirmDialog`).
  * The system shall support nested folder navigation (restricted to 1 sub-level of depth) with a back-button history stack.

### 4.2 Dynamic Island Dialogs
* **Description**: Floating, frameless, animated toasts and dialogs at the top of the screen.
* **Functional Requirements**:
  * `IslandRenameDialog` shall provide an inline text field for quick renaming with morphing entry/exit animations.
  * `IslandConfirmDialog` shall present a confirmation prompt (e.g., for folder/file deletion) with Yes/No options.
  * `HoverPillDialog` shall show the folder name when hovering over a folder widget, seamlessly morphing text when moving between folders.
  * The dialogs shall use DWM-based native corner rounding and blur effects.
  * A `GlobalHoverManager` singleton shall coordinate state between all Dynamic Island variants, blocking the hover pill when rename or confirm dialogs are active.

### 4.3 Electron Dashboard (Settings)
* **Description**: The configuration hub, accessed via the system tray or by double-clicking the tray icon.
* **Functional Requirements**:
  * The system shall provide a frameless Electron window with three tabs: General, Folders, and Halo.
  * **General Tab — Appearance**: Grid Size, Edge Padding (hierarchical: uniform → vertical/horizontal → individual top/bottom/left/right), Grid Visibility, Theme Intensity (Subtle/Balanced/Intense/Solid), Folder Theme (Default/Desktop/Custom Color with HSV wheel, lightness, opacity, and hex input), Dashboard Theme (Dark/Light/Gray/Desktop), Pagination Style (Pill & Dots/Progress Line/Floating Progress Arc/Floating Mini Preview/None).
  * **General Tab — Toggles**: Show Grid on Drag, Animated Grid Color, Wave Entrance, Wave Color Fade, Launch at Startup.
  * **General Tab — Display Effects**: Filter Preset (Reading/Sunset/Movie/Eye Saver), Warmth Intensity slider.
  * **Folders Tab**: List of folders with Add New. Per-folder editor: Folder Name, Snap to Grid toggle, Show Hover Pill toggle, Show App Names toggle, Pill Display Mode (Text/Icon), Pill Icon Path (with file browser).
  * **Halo Tab — Activation & Behavior**: Activation Key (keybind recorder), Activation Mode (Hold/Toggle), Visual Theme (Dark/Desktop/Gray), Brightness slider, Blur Level (Low/Medium/High), HUD Arc Gap (0–90°), Show HUD Text toggle.
  * **Halo Tab — Dimensions & Feel**: Menu Diameter, Hub Ratio (%), BG Opacity, Scroll Sensitivity, Mouse Sensitivity.
  * **Halo Tab — Layout**: Interactive SVG-based radial menu preview with layer selector, slice adding/removing, and command bank assignment overlay.
  * **Halo Tab — Media Widget**: Art Style (Gaussian Blur/8-Bit Mosaic), Visualizer (None/Edge Ring EQ/Breathing Blur/Voxel Wiggle/Size Pulsing/Brightness Strobing), Mosaic Style (Flat/Extrusion), Mosaic Shape (Square/Circles/Hexagons/Rounded/Diamonds), Effect Strength slider, Show Timeline toggle, Show Title toggle, Show Controls toggle.
  * **Halo Tab — Time Widget**: Clock Mode (Digital/Analog), 24-Hour Format toggle, Show Date toggle, Show Seconds toggle.
  * The dashboard shall support four color themes: Dark, Light, Gray, and Desktop (using extracted wallpaper accent colors).
  * A search pill shall allow the user to search for any setting by name and scroll to it with a highlight pulse animation.

### 4.4 Halo Radial HUD
* **Description**: A full-screen, quick-access circular menu triggered by a configurable hotkey.
* **Functional Requirements**:
  * The menu shall be activated via a low-level keyboard hook (`SetWindowsHookExW`) supporting configurable keys and modifiers.
  * The menu shall support up to 9 layers of tools, navigable via mouse scroll wheel.
  * Each tool slice shall feature animated entry with glassmorphism styling and Acrylic blur background.
  * The system shall provide real-time feedback for Volume and Night Light adjustments via a dedicated arc HUD.
  * Hovering over specific tools (Mute, Night Light) shall override scroll wheel behavior to act as an adjustment dial.
  * The menu shall emit `command_triggered` signals to execute actions: browser, file explorer, screenshot, grid toggle, night light, mute, empty recycle bin, settings, search, task manager, sticky notes, power menu.
  * The screenshot tool shall save captures as high-quality PNGs in the user's `Pictures\Pandora` folder after a 200ms delay.

### 4.5 Hub (Halo Center Widget)
* **Description**: The dynamic inner circle of the Halo menu.
* **Functional Requirements**:
  * The hub shall automatically switch to `MediaHub` when music is playing, otherwise display `TimeHub` (clock), with `DefaultLogoHub` as fallback.
  * **MediaHub**:
    * Display track title, artist, album art (with dominant color extraction for UI tinting).
    * Implement audio-reactive visualizers: Edge Ring EQ, 8-Bit Mosaic / Voxel Wiggle, Breathing Blur, Size Pulsing.
    * Override the outer Halo ring (via Spacebar) to inject media controls: Previous, Play/Pause, Next, Timeline scrub, Volume.
    * Support mouse scroll for timeline scrubbing or per-app volume adjustment.
    * Support session switching between multiple media sources (Spotify, Chrome, Apple Music, etc.).
  * **TimeHub**:
    * Support digital and analog clock rendering modes.
    * Support 12h/24h format, show/hide date, show/hide seconds.
    * Support world clock timezones (with robust IANA fallbacks).
    * Override the outer Halo ring (via Spacebar) to inject timezone shortcut buttons.

### 4.6 Media Daemon
* **Description**: A background service providing real-time media session data.
* **Functional Requirements**:
  * The daemon shall run its own asyncio event loop in a background thread, using WinRT's `GlobalSystemMediaTransportControlsSessionManager`.
  * The daemon shall track all active media sessions with unique UUIDs, auto-selecting the best session based on a priority list (Spotify > Apple Music > others) and playing status.
  * The daemon shall continuously sync playback state, timeline (with interpolation), and per-app volume.
  * The daemon shall extract album art thumbnails asynchronously, with caching (LRU, 20 entries).
  * A dedicated COM-initialized peak-polling thread shall sample audio levels at ~33Hz for visualizer input.
  * The daemon shall emit `state_changed` and `thumbnail_ready` signals for the UI layer.
  * The daemon shall expose play/pause, next, previous, volume, and session switching controls.

### 4.7 Display Effects Engine
* **Description**: A hardware-accelerated screen color filter.
* **Functional Requirements**:
  * The engine shall use Windows `SetDeviceGammaRamp` API for zero-latency color adjustments.
  * The engine shall support presets: Reading, Sunset, Movie, Eye Saver — each with configurable blue/green reduction multipliers.
  * The engine shall support smooth animated transitions between on/off states using `QPropertyAnimation`.
  * The original gamma ramp shall be captured on startup and restored on exit.

### 4.8 Desktop Snap Grid
* **Description**: A full-screen overlay for aligning folders.
* **Functional Requirements**:
  * The grid shall render as a frameless, always-on-top, transparent-to-input overlay.
  * The grid shall display crosses and lines at configurable `grid_size` intervals, offset from the primary screen center.
  * The grid shall support animated radial wave entrance from a configurable origin point.
  * The grid shall support hue-shifting color animation when `grid_animated_color` is enabled.
  * The grid shall be configurable with per-side edge padding (top, bottom, left, right, with uniform/linked modes).
  * Folder panels shall optionally snap to grid intersections when `grid_snap` is enabled.

### 4.9 Global Keyboard and Mouse Hooks
* **Description**: Low-level input interception for system-wide hotkey support.
* **Functional Requirements**:
  * The system shall install low-level keyboard and mouse hooks via `SetWindowsHookExW` in a dedicated thread.
  * The hooks shall support configurable activation keys and modifiers for the Halo menu.
  * When the Halo is active, the hooks shall intercept and consume relevant input (mouse movement, scroll, keyboard) to prevent pass-through to other applications.
  * The hooks shall be properly unregistered via `UnhookWindowsHookEx` on application shutdown.

### 4.10 Info Pill Guidance System
* **Description**: A persistent status HUD at the bottom right of the Dashboard.
* **Functional Requirements**:
  * The system shall display context-aware tooltips and guidance information in a floating pill.
  * For long descriptions, the system shall implement an automatic marquee (scrolling text) effect.
  * The pill shall use entry/exit animations to maintain a non-intrusive presence.

---

## 5. Installation and Deployment

### 5.1 Build Pipeline
* **Functional Requirements**:
  * The build shall be orchestrated by `build_and_deploy.ps1` (requires Administrator).
  * Step 1: Compile the Electron Dashboard via `electron-packager` into `dist_electron/PandoraUI-win32-x64`.
  * Step 2: Compile the Python core via PyInstaller (`--onedir`) into `dist/Pandora/`, bundling the Electron dashboard and assets.
  * Step 3: Generate a self-signed code signing certificate and sign `Pandora.exe`.
  * Step 4: Zip the payload (`dist/Pandora/*`) into `installer/payload.zip`.
  * Step 5: Compile the custom Electron installer via `electron-builder` (portable mode) into `installer/dist_installer/PandoraSetup.exe`.
  * Step 6: Sign the installer executable.

### 5.2 Custom Installer
* **Functional Requirements**:
  * The installer shall be a frameless, transparent Electron application with a branded UI.
  * The installer shall extract the payload zip into `%LOCALAPPDATA%\Programs\Pandora`.
  * The installer shall kill any running Pandora instances before extraction.
  * The installer shall optionally create a Desktop shortcut and Start Menu shortcut.
  * The installer shall optionally register the application for launch at startup via the Windows Registry.
  * The installer shall register an uninstaller entry in `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\Pandora` so the app appears in "Add or Remove Programs."
  * The installer shall generate an `uninstall.bat` file in the installation directory.

### 5.3 Uninstaller
* **Functional Requirements**:
  * The uninstaller shall kill any running Pandora instances.
  * The uninstaller shall remove the startup registry entry and the uninstaller registry entry.
  * The uninstaller shall back up the user's `%APPDATA%\Pandora\internal_storage` directory to `%USERPROFILE%\Desktop\Pandora_Backup` before deleting anything.
  * The uninstaller shall remove Desktop and Start Menu shortcuts (including OneDrive Desktop).
  * The uninstaller shall delete the installation directory (`%LOCALAPPDATA%\Programs\Pandora`).
  * The uninstaller shall delete the application data directory (`%APPDATA%\Pandora`) to ensure a clean slate for future reinstallation.

---

## 6. Graceful Shutdown

### 6.1 Shutdown Requirements
* **Functional Requirements**:
  * On application quit (tray menu, OS shutdown, or `aboutToQuit`), the system shall execute a comprehensive cleanup routine:
    * Restore the original display gamma ramp.
    * Stop the global keyboard/mouse hook thread (via `PostThreadMessageW(WM_QUIT)`) and call `UnhookWindowsHookEx`.
    * Stop the `MediaDaemon` (set stop flag on peak thread, stop asyncio loop).
    * Stop the `WebSocketServerThread` (resolve stop future to end the server).
    * Delete the `ws_port.txt` file from `%APPDATA%\Pandora`.
    * Force-kill the Electron dashboard child process tree (`taskkill /F /T`).
  * The cleanup routine shall be idempotent (guarded against double execution).
  * The application shall use `QApplication.quit()` and `sys.exit()` (not `os._exit()`) to allow proper Python and Qt cleanup.
  * The `atexit` handler and `app.aboutToQuit` signal shall both trigger the same cleanup function.

---

## 7. Configuration Management

### 7.1 Configuration Requirements
* **Functional Requirements**:
  * All configuration shall be stored in a single JSON file at `%APPDATA%\Pandora\config.json`.
  * Configuration saves shall be atomic: write to `config.json.tmp` then `os.replace` to `config.json`.
  * The system shall perform automatic migration from legacy configuration formats on load (e.g., `global_settings` to `general_settings`, `radial_menu` to `halo`, `dead_zones_config` to `hub_config`, fixed-tools to `menus[]`).
  * The system shall automatically migrate data from the original project directory to `%APPDATA%\Pandora` on first run after installation.
  * The system shall synchronize the on-disk storage state with the configuration on every load (auto-importing new files, pruning missing entries).
  * Private/temporary keys (prefixed with `_`) shall be stripped before saving.

---

## 8. Non-Functional Requirements

### 8.1 Performance Requirements
* The application must launch quietly in the background without noticeable system lag.
* Hover and morph animations must run smoothly at a high frame rate, leveraging PyQt6's rendering engine and a unified `anim_timer`.
* Icon extraction must happen asynchronously or be cached (via `IconExtractor` LRU cache) to avoid freezing the UI during folder navigation or resizing.
* Media state polling must not block the Qt event loop (handled via dedicated asyncio and COM threads).
* Audio peak sampling must run at ~33Hz on a dedicated thread to prevent visualizer stutter.

### 8.2 Usability Requirements
* The application must remain accessible via a system tray icon at all times.
* The dashboard UI must employ modern, themed styling (Dark/Light/Gray/Desktop-accent) with clear contrast and interactive feedback.
* The application shall prevent overlapping edge-cases by confining folder dragging within the screen's available geometry.
* Drag-and-drop between folders shall handle file name collisions by auto-incrementing suffixes.

### 8.3 Reliability
* The application must handle malformed or missing shortcuts gracefully without crashing the expanded view.
* The configuration JSON must be safely written (atomic save) to prevent corruption during power loss or force-kill.
* Media session timeouts (1 second) shall prevent the UI from hanging if a media source becomes unresponsive.
* A crash wrapper (`run_pandora.py`) shall capture stdout/stderr to a crash report log file.

### 8.4 Portability
* While targeted and optimized for Windows 10/11 (using DwmApi, COM, WinRT, ctypes, pycaw, winsdk), the core Qt architecture should be maintained in a way that minimizes cross-platform friction where possible.

### 8.5 Security
* The compiled executable shall be signed with a code-signing certificate (self-signed for local development, real certificate for distribution).
* The manifest shall request `asInvoker` with `uiAccess="true"` to allow interaction with elevated windows without requiring full administrator rights at runtime.

### 8.6 Visual Standards
* The application shall employ a "Trackless" UI aesthetic, replacing standard scrollbars with minimalist thumbs.
* All interactive feedback (Dynamic Island dialogs, Halo HUD) must use glassmorphism and the established Pandora Cyan accent.
* All Halo menu interactions shall feature smooth animated transitions with configurable easing curves.
* The Electron dashboard shall use custom-styled HTML controls (sliders with `--fill` progress, toggles, custom selects) matching the application's visual identity.