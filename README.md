# Pandora

**Pandora** is an advanced, highly customizable Windows desktop widget application built with Python and PyQt6. It allows users to create interactive, translucent, and animated "folders" directly on their desktop environment. Unlike standard application windows, Pandora seamlessly integrates with the Windows Shell to act as true desktop content.

## ✨ Key Features

### 🖥️ Native Desktop Integration (Win+D Bypass)
Standard application windows minimize when the user presses **Win+D** ("Show Desktop"). Pandora utilizes advanced Windows API (Win32) hooks to bypass this:
* **Progman / WorkerW Ownership:** Folders are natively reparented/owned by the desktop background layer (`SHELLDLL_DefView`). This ensures they survive the desktop minimization sweep.
* **Stay On Bottom:** Widgets are strictly pinned to the bottom of the Z-order, preventing them from overlapping active applications.

### 🧲 Advanced Grid Snapping
Organizing folders is effortless with the built-in magnetic grid system.
* **Symmetrical Centering:** The grid geometry mathematically calculates outward from the absolute center of your primary monitor, ensuring perfectly balanced margins on all edges.
* **Edge Padding:** Users can configure a global safe margin (Edge Padding) so folders and grid lines never bleed off-screen or crowd the taskbar.
* **Magnetic Spiral Repulsion:** If you drop a folder onto an occupied grid intersection, the system uses a spiral search algorithm to automatically find the nearest available slot and gracefully glides the folder into place.
* **Visual Grid Overlay:** Toggle a transparent, click-through grid overlay from the System Tray. It projects faint white lines and crosshairs onto your desktop to visualize the grid layout.

### 🎨 Beautiful, Fluid Animations
The application emphasizes a polished, "alive" feel using Qt's `QPropertyAnimation` and `QVariantAnimation` frameworks.
* **Hover Fan-Out:** Hovering over a folder smoothly fans out its contained applications into a grid.
* **Dynamic Titles:** Folder titles sit snugly underneath the icons and smoothly fade out during the fan-out animation to reduce visual clutter.
* **Morph Transitions:** Opening a folder triggers a fluid morphing window that elegantly displays the contents.

### ⚙️ Ultimate Customizability (Dashboard)
A modern, frosted-glass dashboard lets you tweak every aspect of your folders.
* **Global vs. Individual Settings:** Set a universal theme, or override settings for specific folders.
* **Size Presets:** Quickly switch between Small, Medium, Large, or Custom sizing.
* **Visuals:** Adjust folder glow intensity, glow color, background color, opacity, and corner radius.
* **Hero Covers:** Assign a cover image to a folder with customizable blur and opacity to create gorgeous visual tiles.
* **Kinetics:** Change the animation pacing (Snappy, Fluid, Relaxed) for hovers and window morphing.

### 📂 Intuitive Drag & Drop
* Add new apps simply by dragging executable files, shortcuts (`.lnk`, `.url`), or regular files directly into a folder.
* Pandora automatically copies shortcuts into its internal storage, keeping your actual Desktop directory clean and organized.

---

## 🚀 How to Use

1. **Launch:** Run `python main.py` or the compiled executable. The app runs silently in the system tray.
2. **Dashboard:** Right-click the Pandora icon in the System Tray and select **Settings**, or right-click any folder and hit **Settings**.
3. **Add Folders:** Use the System Tray menu to create a new folder.
4. **Add Apps:** Drag and drop any file or shortcut directly onto a folder widget to add it.
5. **Snap to Grid:** In the Dashboard, toggle **"Snap to Grid"**. Adjust the **Grid Size** (default: 110) and **Edge Padding** (default: 0).
6. **Show Grid:** Right-click the Tray Icon and toggle **Show Grid** to visualize the snapping layout on your wallpaper.

---

## 🛠️ Architecture Details

* **Frontend:** PyQt6 (Translucent Widgets, Frameless Windows, QPainter for custom rendering).
* **Backend Storage:** Configurations and internal storage are kept in `AppData/Roaming/Pandora`.
* **System Tray:** `QSystemTrayIcon` for background lifecycle management.
* **WinAPI Integrations:** `ctypes.windll.user32` is heavily utilized for:
  * Sending `0x052C` to Progman to spawn desktop layers.
  * Modifying window styles (`GWL_EXSTYLE`, `GWLP_HWNDPARENT`) to pin widgets to the desktop.
  * Disabling modern DWM drag-and-drop visuals that conflict with customized transparent windows.
