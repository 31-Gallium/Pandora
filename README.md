<div align="center">

<img src="assets/Pandora.svg" width="200" alt="Pandora Logo" />

# Pandora

**A premium desktop widget engine & radial launcher for Windows**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Electron](https://img.shields.io/badge/Electron-Dashboard-47848F?logo=electron&logoColor=white)](https://electronjs.org)
[![DirectX](https://img.shields.io/badge/DirectX_11-Vis_Engine-0078D4?logo=windows&logoColor=white)](https://docs.microsoft.com/en-us/windows/win32/direct3d11)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

> [!WARNING]  
> **Development Status: Active Beta / Work In Progress**
> Pandora is currently under heavy development and testing. While core features are functional, you may encounter bugs, unoptimized code, or breaking changes as I finalize the architecture for a 1.0 production release.

> [!NOTE]
> **First Launch Delay:** Since Pandora is not yet code-signed or published, Windows SmartScreen may take a good few seconds to verify the installer/app on first run. This is normal and will go away once the application is signed.

**Pandora** is an advanced, highly customizable Windows desktop widget application and radial launcher built with a hybrid architecture of Python (PyQt6) and Electron. It allows users to create interactive, translucent, and animated "folders" directly on their desktop environment, while providing a stunning, full-screen radial HUD for system control. 

Unlike standard application windows, Pandora seamlessly integrates with the Windows Shell to act as true desktop content, surviving "Show Desktop" commands and functioning as an interactive wallpaper overlay.

---

## Key Features

### Native Desktop Integration
* **Survives Win+D:** Pandora widgets embed themselves directly into the desktop background layer, meaning they will never be minimized when you use the "Show Desktop" shortcut.
* **Non-Intrusive:** Widgets stay pinned to the absolute bottom of your screen, acting as an interactive extension of your wallpaper.
* **Instant Access:** Summon the Radial HUD at any time without stealing focus from your current active game or application.

### Interactive Desktop Folders
* **Nested Folders:** Add an extra layer of organization by creating folders inside of your main folders (supports 1 sub-level of nesting).
* **Custom Folder Headers:** Customize how your folder's title is displayed on hover—hide the title completely for a minimalist look, or display a sleek text or icon pill.
* **Dynamic Grid Layout:** Icons are arranged in a customizable grid that smoothly adapts and animates when you resize the folder.
* **Smart Icon Extraction:** Just drag and drop! Pandora automatically extracts high-quality icons from dropped `.exe`, `.lnk`, or UWP apps.
* **Liquid Drag-and-Drop:** Seamlessly drag apps between folders or reorder them, complete with smooth liquid drag-scroll animations.
* **Paging:** Folders automatically paginate when they contain too many apps, complete with sleek transition animations and scroll indicators.

### The Halo Menu (Radial HUD)
A massive, full-screen interactive radial menu that acts as Pandora's quick-access launcher.
* **Layered Navigation:** Cycle through different tool sets (Media, System, Apps) simply by scrolling your mouse wheel while the HUD is open.
* **Smart Dials:** Hovering over specific slices (like Volume or Night Light) temporarily converts your scroll wheel into an adjustment dial for that setting.
* **Premium Aesthetics:** Features gorgeous glassmorphic background blur and smooth physics-driven animations.
* **Display Effects Engine:** Real-time, zero-latency visual effects (like "Sunset" or "Eye Saver") that work seamlessly even over full-screen games without causing FPS drops.

### Dynamic Hub Modules
The center of the Halo menu intelligently switches context based on what you are doing.
* **Media Hub:** When music is playing, the center transforms into a rich media controller displaying live track info and album art.
* **Audio Visualizers:** Beautiful, math-driven visualizers (Edge Ring EQ, Voxel Wiggle, Breathing Blur) react in real-time to your system's audio output, powered by a custom **DirectX 11 GPU-accelerated rendering engine** (`pandora_vis_engine.dll`).
* **Time Hub:** Reverts to a gorgeous Digital or Analog clock when no media is playing.

### Dashboard Pill
A floating, always-on-top pill-shaped widget that provides quick access to the Settings Dashboard, Grid Overlay, and app restart/quit actions without needing the system tray.

### Live Settings Dashboard
Pandora's settings are managed by an incredibly sleek, standalone Electron application.
* **Instant & Live Updates:** Changes made in the dashboard instantly apply to your desktop widgets without ever requiring a restart.
* **Live Sandbox Preview:** The dashboard renders a pixel-perfect, live preview of your folder or Halo menu directly inside the settings app as you tweak your theme.

### Advanced Grid Snapping
* **Symmetrical Centering:** The desktop grid mathematically calculates outward from the absolute center of your monitor for perfect symmetry.
* **Visual Grid Overlay:** Toggle a full-screen, animated grid overlay to help you align folders perfectly.

*Pandora ships with a custom PyQt6-based installer and uninstaller for a self-contained deployment pipeline—no third-party frameworks required.*

---

## Project Structure

```
Pandora/
├── main.py                     # Main application entry point
├── config.py                   # Configuration management & defaults
├── hub.py                      # Hub module orchestrator
├── utils.py                    # Shared utilities & Win32 helpers
├── installer.py                # Custom PyQt6 installer
├── uninstaller.py              # Custom PyQt6 uninstaller
├── uninstaller_main.py         # Uninstaller entry point
├── launcher.cpp                # Native C++ launcher (GPU preference)
│
├── ui/                         # PyQt6 UI components
│   ├── folder_panel.py         # Desktop folder widget
│   ├── halo.py                 # Radial HUD (Halo menu)
│   ├── pill_window.py          # Floating dashboard pill
│   ├── grid_overlay.py         # Desktop grid overlay
│   ├── app_icon.py             # App icon widget
│   ├── layout_logic.py         # Grid layout calculations
│   └── logic.py                # Folder interaction logic
│
├── core_services/              # Background service daemons
│   ├── ws_server.py            # WebSocket bridge (Python ↔ Electron)
│   ├── media_daemon.py         # WinRT SMTC media controller
│   ├── audio_engine.py         # Audio capture & peak levels
│   └── ipc_server.py           # Named pipe IPC server
│
├── hub_modules/                # Dynamic Halo center modules
│   ├── media.py                # Media hub (track info, album art)
│   ├── clock.py                # Clock hub (digital/analog)
│   ├── vis_engine_bridge.py    # DirectX vis engine Python bridge
│   ├── physics.py              # Physics-driven animations
│   └── default.py              # Default/fallback module
│
├── electron_dashboard/         # Electron settings dashboard
│   ├── main.js                 # Electron main process
│   ├── renderer.js             # Dashboard renderer
│   ├── index.html              # Dashboard UI
│   ├── style.css               # Dashboard styles
│   ├── ui_dashboard_*.js       # Per-section dashboard controllers
│   ├── uninstaller.html        # Uninstaller UI
│   └── sandbox_server.py       # Live preview sandbox
│
├── engine_src/                 # DirectX 11 visualizer engine (C++)
│   ├── visualizer_core.cpp     # Core D3D11/D2D rendering engine
│   ├── hlsl_shaders.h          # HLSL shader source strings
│   ├── build.bat               # MSVC build script
│   └── check_adapter.cpp       # GPU adapter enumeration
│
├── native_engine/              # Native audio capture engine (C++)
│   ├── src/                    # Audio capture, FFT, IPC source
│   └── CMakeLists.txt          # CMake build configuration
│
├── assets/                     # SVG icons and branding
├── docs/                       # GitHub Pages landing site
└── requirements.txt            # Python dependencies
```

---

## How to Use

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch:** Run `python main.py`. The app runs silently in the system tray.
3. **Radial HUD:** Hold the activation key (default: `` ` `` Tilde) to open the Halo menu. Scroll to switch layers.
4. **Dashboard:** Right-click the Pandora tray icon and select **Settings** to open the customization hub.
5. **Create Folders:** Right-click the tray icon and select **Create Folder**, or drag items directly onto existing folders.
6. **Adjust Audio:** Open the Halo menu, hover over the volume slice, and scroll to change system volume.

---

## Architecture & Engineering

Pandora relies on several advanced, low-level Windows APIs and hybrid architectural patterns to achieve its seamless experience:

* **WorkerW / Progman Ownership:** Pandora sends an undocumented message (`0x052C`) to the `Progman` to split the desktop and spawn a `WorkerW` layer. Reparenting the widgets to this specific layer is what allows them to survive the desktop minimization sweep.
* **Hardware Gamma Ramps:** The Display Effects engine bypasses standard UI overlays (which cause stuttering in full-screen games) by utilizing `gdi32.SetDeviceGammaRamp` for zero-latency, hardware-level color manipulation.
* **Global Input Hooks:** Uses low-level `SetWindowsHookExW` keyboard and mouse hooks to intercept the activation key globally without triggering Windows focus-stealing regulations.
* **Real-time WebSocket Sync:** A background `ws_server.py` bridges the state between the Python orchestrator and the HTML/JS Electron UI for instant IPC communication.
* **WinRT SMTC & Pycaw:** `media_daemon.py` runs an isolated `asyncio` event loop to safely marshal WinRT/COM calls for the System Media Transport Controls, while `pycaw` captures raw audio peak levels for the visualizers.
* **DirectX 11 Visualizer Engine:** A custom C++ DLL (`pandora_vis_engine.dll`) compiled with MSVC uses D3D11 and D2D1 for GPU-accelerated rendering of audio visualizers. The Python bridge communicates via `ctypes`, using triple-buffered staging textures for tear-free frame delivery.
* **Native Launcher:** A lightweight C++ launcher (`Pandora.exe`) forces high-performance GPU selection on Optimus/PowerXpress laptops via `NvOptimusEnablement` and `AmdPowerXpressRequestHighPerformance` exports before spawning `PandoraCore.exe`.
