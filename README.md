# Pandora

**Pandora** is an advanced, highly customizable Windows desktop widget application built with Python and PyQt6. It allows users to create interactive, translucent, and animated "folders" directly on their desktop environment. Unlike standard application windows, Pandora seamlessly integrates with the Windows Shell to act as true desktop content.

## ✨ Key Features

### 🖥️ Native Desktop Integration (Win+D Bypass)
Standard application windows minimize when the user presses **Win+D** ("Show Desktop"). Pandora utilizes advanced Windows API (Win32) hooks to bypass this:
* **Progman / WorkerW Ownership:** Folders are natively reparented/owned by the desktop background layer (`SHELLDLL_DefView`). This ensures they survive the desktop minimization sweep.
* **Stay On Bottom:** Widgets are strictly pinned to the bottom of the Z-order, preventing them from overlapping active applications.

### 🎡 Radial HUD & System Tools
A multi-layered interactive menu for rapid system control.
* **Layered Navigation:** Scroll through different tool sets (Media, System, Apps) while the menu is open.
* **Smart Warmth System:** A built-in "Night Light" that uses high-performance WinAPI gamma manipulation—completely anti-cheat safe and lag-free.
* **Volume/Warmth Arc HUD:** Real-time visual feedback on intensity levels directly within the radial menu.
* **High-Fidelity Snips:** Capture professional screenshots with a built-in delay to ensure a clean desktop, saved directly to your `Pictures\Pandora` folder.

### 💊 Info Pill Guidance
Pandora eliminates traditional clunky tooltips in favor of a centralized guidance system.
* **Floating Info Pill:** A sleek HUD at the bottom right that reveals the secrets of every setting.
* **Dynamic Marquee:** Long descriptions fluidly scroll left and right, ensuring you never miss a detail.
* **Premium Glassmorphism:** Styled with deep space gradients and cyan glows to match the Pandora aesthetic.

### 🧲 Advanced Grid Snapping
Organizing folders is effortless with the built-in magnetic grid system.
* **Symmetrical Centering:** The grid geometry mathematically calculates outward from the absolute center of your primary monitor.
* **Edge Padding:** Configure a global safe margin so folders and grid lines never bleed off-screen.
* **Magnetic Spiral Repulsion:** Dropped folders automatically find the nearest available slot and glide into place.
* **Visual Grid Overlay:** Toggle a transparent, click-through grid overlay from the System Tray to visualize your snapping layout.

### 🎨 Beautiful, Fluid Animations
* **Hover Fan-Out:** Hovering over a folder smoothly fans out its contained applications into a grid.
* **Morph Transitions:** Opening a folder triggers a fluid morphing window that elegantly displays the contents.
* **Trackless UI:** Minimalist, thumb-only scrollbars provide a modern, premium aesthetic throughout the app.

### ⚙️ Ultimate Customizability (Dashboard)
* **Global vs. Individual Settings:** Set a universal theme, or override settings for specific folders.
* **Size Presets:** Quickly switch between Small, Medium, Large, or Custom sizing.
* **Visuals:** Adjust folder glow intensity, glow color, background color, opacity, and corner radius.
* **Hero Covers:** Assign a cover image to a folder with customizable blur and opacity.

---

## 🚀 How to Use

1. **Launch:** Run `python main.py`. The app runs silently in the system tray.
2. **Radial HUD:** Hold the activation key (default: `~` Tilde) to open the HUD. Scroll to switch layers.
3. **Dashboard:** Right-click the Pandora tray icon and select **Settings** to open the customization hub.
4. **Info Pill:** Hover over any setting in the Dashboard to see its description in the bottom-right HUD.
5. **Screenshots:** Activate the **Snip** tool in the Radial Menu. The capture will be saved to your `Pictures\Pandora` folder after a 200ms delay.

---

## 🛠️ Architecture Details

* **Frontend:** PyQt6 (Translucent Widgets, Frameless Windows, QPainter).
* **System Hooks:** `ctypes.windll.user32` for desktop reparenting and low-level mouse tracking.
* **Display Effects:** WinAPI `SetDeviceGammaRamp` for anti-cheat safe blue light filtering.
* **Persistence:** Configs and cached icons are stored in `config.json` and a local `assets` cache.
