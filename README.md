<div align="center">

![Pandora Logo](electron_dashboard/assets/Pandora.svg?v=2)

# Pandora

</div>

> [!WARNING]  
> **Development Status: Active Beta / Work In Progress**
> Pandora is currently under heavy development and testing. While core features are functional, you may encounter bugs, unoptimized code, or breaking changes as I finalize the architecture for a 1.0 production release.

**Pandora** is an advanced, highly customizable Windows desktop widget application and radial launcher built with a hybrid architecture of Python (PyQt6) and Electron. It allows users to create interactive, translucent, and animated "folders" directly on their desktop environment, while providing a stunning, full-screen radial HUD for system control. 

Unlike standard application windows, Pandora seamlessly integrates with the Windows Shell to act as true desktop content, surviving "Show Desktop" commands and functioning as an interactive wallpaper overlay.

---

## ✨ Key Features

### ![Native Desktop Integration](electron_dashboard/assets/windows%20settings.svg?v=2) Native Desktop Integration
* **Survives Win+D:** Pandora widgets embed themselves directly into the desktop background layer, meaning they will never be minimized when you use the "Show Desktop" shortcut.
* **Non-Intrusive:** Widgets stay pinned to the absolute bottom of your screen, acting as an interactive extension of your wallpaper.
* **Instant Access:** Summon the Radial HUD at any time without stealing focus from your current active game or application.

### ![Interactive Desktop Folders](electron_dashboard/assets/folders.svg?v=2) Interactive Desktop Folders
* **Nested Folders:** Add an extra layer of organization by creating folders inside of your main folders (supports 1 sub-level of nesting).
* **Custom Folder Headers:** Customize how your folder's title is displayed on hover—hide the title completely for a minimalist look, or display a sleek text or icon pill.
* **Dynamic Grid Layout:** Icons are arranged in a customizable grid that smoothly adapts and animates when you resize the folder.
* **Smart Icon Extraction:** Just drag and drop! Pandora automatically extracts high-quality icons from dropped `.exe`, `.lnk`, or UWP apps.
* **Liquid Drag-and-Drop:** Seamlessly drag apps between folders or reorder them, complete with smooth liquid drag-scroll animations.
* **Paging:** Folders automatically paginate when they contain too many apps, complete with sleek transition animations and scroll indicators.

### ![The Halo Menu](electron_dashboard/assets/halo.svg?v=2) The Halo Menu (Radial HUD)
A massive, full-screen interactive radial menu that acts as Pandora's quick-access launcher.
* **Layered Navigation:** Cycle through different tool sets (Media, System, Apps) simply by scrolling your mouse wheel while the HUD is open.
* **Smart Dials:** Hovering over specific slices (like Volume or Night Light) temporarily converts your scroll wheel into an adjustment dial for that setting.
* **Premium Aesthetics:** Features gorgeous glassmorphic background blur and smooth physics-driven animations.
* **Display Effects Engine:** Real-time, zero-latency visual effects (like "Sunset" or "Eye Saver") that work seamlessly even over full-screen games without causing FPS drops.

### ![Dynamic Hub Modules](electron_dashboard/assets/hub.svg?v=2) Dynamic Hub Modules
The center of the Halo menu intelligently switches context based on what you are doing.
* **Media Hub:** When music is playing, the center transforms into a rich media controller displaying live track info and album art.
* **Audio Visualizers:** Beautiful, math-driven visualizers (Edge Ring EQ, Voxel Wiggle, Breathing Blur) react in real-time to your system's audio output.
* **Time Hub:** Reverts to a gorgeous Digital or Analog clock when no media is playing.

### ![Live Settings Dashboard](electron_dashboard/assets/general.svg?v=2) Live Settings Dashboard
Pandora's settings are managed by an incredibly sleek, standalone Electron application.
* **Instant & Live Updates:** Changes made in the dashboard instantly apply to your desktop widgets without ever requiring a restart.
* **Live Sandbox Preview:** The dashboard renders a pixel-perfect, live preview of your folder or Halo menu directly inside the settings app as you tweak your theme.

### ![Advanced Grid Snapping](electron_dashboard/assets/toggle%20grid.svg?v=2) Advanced Grid Snapping
* **Symmetrical Centering:** The desktop grid mathematically calculates outward from the absolute center of your monitor for perfect symmetry.
* **Visual Grid Overlay:** Toggle a full-screen, animated grid overlay to help you align folders perfectly.

---

## 🚀 How to Use

1. **Launch:** Run `python main.py`. The app runs silently in the system tray.
2. **Radial HUD:** Hold the activation key (default: `~` Tilde) to open the Halo menu. Scroll to switch layers.
3. **Dashboard:** Right-click the Pandora tray icon and select **Settings** to open the customization hub.
4. **Create Folders:** Right-click the tray icon and select **Create Folder**, or drag items directly onto existing folders.
5. **Adjust Audio:** Open the Halo menu, hover over the volume slice, and scroll to change system volume.

---

## ![Architecture & Engineering](electron_dashboard/assets/tools.svg?v=2) Architecture & Engineering

Pandora relies on several advanced, low-level Windows APIs and hybrid architectural patterns to achieve its seamless experience:

* **WorkerW / Progman Ownership:** Pandora sends an undocumented message (`0x052C`) to the `Progman` to split the desktop and spawn a `WorkerW` layer. Reparenting the widgets to this specific layer is what allows them to survive the desktop minimization sweep.
* **Hardware Gamma Ramps:** The Display Effects engine bypasses standard UI overlays (which cause stuttering in full-screen games) by utilizing `gdi32.SetDeviceGammaRamp` for zero-latency, hardware-level color manipulation.
* **Global Input Hooks:** Uses low-level `SetWindowsHookExW` keyboard and mouse hooks to intercept the activation key globally without triggering Windows focus-stealing regulations.
* **Real-time WebSocket Sync:** A background `ws_server.py` bridges the state between the Python orchestrator and the HTML/JS Electron UI for instant IPC communication.
* **WinRT SMTC & Pycaw:** `media_daemon.py` runs an isolated `asyncio` event loop to safely marshal WinRT/COM calls for the System Media Transport Controls, while `pycaw` captures raw audio peak levels for the visualizers.
