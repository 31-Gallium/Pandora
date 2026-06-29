# `ui_common.py` Summary

## Role in Architecture
A collection of reusable, highly customized UI components (PyQt6 widgets) that are shared across different parts of the application, particularly the settings dashboard and custom dialogs.

## Key Classes and Functions
- **`fill_themed_path`**: A helper function to apply gradients and theme colors to QPainterPath shapes.
- **`DropdownButton` and `AnimatedMenu`**: A custom combobox replacement that uses frameless, animated popout menus with opacity fading.
- **`CustomInputDialog`**: A themed dialog for text input (used for creating new folders or renaming apps). Adapts its colors based on the current dashboard theme.
- **`FlowLayout`**: A custom QLayout that automatically wraps widgets to the next line when they run out of horizontal space (similar to flex-wrap in CSS).
- **`ToastNotification`**: An animated, frameless popup that slides in from the top of the screen, displays a brief message, and slides out. Uses Windows 11 Acrylic blur.
- **`IslandRenameDialog` & `IslandConfirmDialog`**: Floating, frameless, animated dialogs (resembling macOS's Dynamic Island) that drop from the top of the screen to handle quick actions (like renaming an icon or confirming deletion). Both utilize custom masking and DwmSetWindowAttribute for native corner rounding and blur.

## Dependencies and Interactions
- Uses `ctypes` for native Windows 11 effects.
- Used heavily by `settings_ui.py` (or the Electron dashboard fallback via `sandbox_server.py` calling Qt overlays).
