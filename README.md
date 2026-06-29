# Pandora

**Pandora** is an advanced, highly customizable Windows desktop widget application and radial launcher built with a hybrid architecture of Python (PyQt6) and Electron. It allows users to create interactive, translucent, and animated "folders" directly on their desktop environment, while providing a stunning, full-screen radial HUD for system control. 

Unlike standard application windows, Pandora seamlessly integrates with the Windows Shell to act as true desktop content, surviving "Show Desktop" commands and supporting deep native integrations like Windows 11 Acrylic blur, WinRT Media Transport, and dynamic audio visualization.

---

## ✨ Key Features

### 🖥️ Native Desktop Integration (Win+D Bypass)
Pandora utilizes advanced Windows API (Win32) hooks to bypass standard minimization:
* **Progman / WorkerW Ownership:** Folders are natively reparented/owned by the desktop background layer (`SHELLDLL_DefView`), ensuring they survive the desktop minimization sweep.
* **Stay On Bottom:** Widgets are strictly pinned to the bottom of the Z-order, acting as an interactive wallpaper overlay.
* **Global Hooks:** Low-level keyboard and mouse hooks intercept input globally to seamlessly summon the Radial HUD without focus stealing.

### 🎡 The Halo Menu (Radial HUD)
A massive, full-screen interactive radial menu that acts as Pandora's quick-access launcher.
* **Layered Navigation:** Cycle through different tool sets (Media, System, Apps) simply by scrolling your mouse wheel while the HUD is open.
* **Acrylic Blur Integration:** Leverages `ctypes` to invoke native Windows Acrylic Blur behind the HUD for a premium glassmorphic aesthetic.
* **Smart Dials:** Hovering over specific slices (e.g., Volume, Night Light) temporarily converts the scroll wheel into an adjustment dial for that specific setting.
* **Display Effects Engine:** Real-time, zero-latency visual effects (like "Sunset" or "Eye Saver") achieved through WinAPI hardware gamma ramp manipulation.

### 🎛️ Dynamic Hub Modules
The center of the Halo menu is a dynamic "Hub" that intelligently switches context based on what you are doing.
* **Media Hub:** When music is playing, the center transforms into a rich media controller. 
  * Hooks into Windows System Media Transport Controls (SMTC) via a dedicated background daemon to fetch live track info and album art.
  * **Audio Visualizers:** Renders 60FPS math-driven visualizers (Edge Ring EQ, Voxel Wiggle, Breathing Blur) that react in real-time to audio peak levels via `pycaw`.
* **Time Hub:** When no media is playing, it reverts to a beautiful Digital or Analog clock, supporting quick-swapping between international timezones.

### 📁 Interactive Desktop Folders
* **Dynamic Grid Layout:** Icons inside folders are arranged in a sleek, customizable grid with smooth transitions when expanding or collapsing.
* **Smart Extraction:** Automatically extracts icons from dropped `.exe`, `.lnk`, or UWP apps using COM interop (`win32com`, `shell32`), with fallbacks for missing assets.
* **Drag-and-Drop:** Seamlessly drag apps between folders, to the desktop, or reorder them, complete with "Ghost" tooltip trackers and liquid drag-scroll animations.
* **Paging:** Supports pagination when folders contain too many apps, complete with smooth transitional animations and scroll indicators.

### ⚙️ Hybrid Settings Dashboard
Pandora's settings are managed by an incredibly sleek, standalone **Electron** application.
* **Real-time WebSocket Sync:** The Python backend (`ws_server.py`) and Electron frontend (`renderer.js`) communicate in real-time via WebSockets. Changes made in the dashboard instantly apply to the desktop widgets without requiring a restart.
* **Live Sandbox Preview:** The Electron dashboard spawns an invisible PyQt6 `sandbox_server.py` overlay window right on top of its HTML canvas. This provides a pixel-perfect, live rendering of how your folder or Halo menu will look on the desktop as you tweak settings.
* **JSON State Management:** All configuration is securely managed and migrated by a central `ConfigManager`.

### 🧲 Advanced Grid Snapping
* **Symmetrical Centering:** The desktop grid mathematically calculates outward from the absolute center of your primary monitor.
* **Visual Grid Overlay:** Toggle a full-screen, transparent-for-input grid overlay that pulses and animates to help you align folders perfectly.

---

## 🚀 How to Use

1. **Launch:** Run `python main.py`. The app runs silently in the system tray.
2. **Radial HUD:** Hold the activation key (default: `~` Tilde) to open the Halo menu. Scroll to switch layers.
3. **Dashboard:** Right-click the Pandora tray icon and select **Settings** to open the Electron customization hub.
4. **Create Folders:** Right-click the tray icon and select **Create Folder**, or drag items directly onto existing folders.
5. **Adjust Audio:** Open the Halo menu, hover over the volume slice, and scroll to change system volume.

---

## 🛠️ Architecture Deep Dive

* **Core Engine:** Written in Python using `PyQt6` for rendering translucent widgets, frameless windows, and complex `QPainter` shapes.
* **Dashboard Frontend:** HTML/CSS/JS running in a borderless `Electron` window, themed with custom CSS variables and glassmorphic elements.
* **IPC (Inter-Process Communication):** `websockets` library is used heavily to bridge state between the Python orchestrator and the Electron UI.
* **Media Daemon:** `core_services/media_daemon.py` runs an isolated `asyncio` event loop in a background thread to safely marshal COM/WinRT calls for media playback, preventing UI stuttering.
* **System Integrations:** Deep reliance on `ctypes`, `win32com`, `dwmapi`, and `pycaw` for native Windows functionality (blur, volume, shell integration, system tray).
