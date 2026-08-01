# Pandora Release 0.9.10 Patch Notes

### 1. Stability and Reliability Improvements
- Launcher Validation: The launcher now validates the existence of PandoraCore.exe before selecting an application folder, preventing execution failures.
- Update Error Recovery: Added automatic cleanup of partial or corrupt update folders if the update process fails, ensuring the launcher selects a valid version on restart.
- Thread Safety: Added guards to prevent concurrent creation of update threads, avoiding duplicate workers and crashes.
- State Recovery: The dashboard now properly restores the update status and progress if it reconnects to the Python backend during an active update.
- Crash Fix: Resolved a NoneType AttributeError that occurred when accessing the update worker state before initialization.

### 2. Halo UI & Dashboard Fixes
- Halo Scroll Optimization: Scrolling the Halo Sandbox in the dashboard to switch layers now only re-renders the UI locally and no longer saves the configuration unnecessarily. This prevents config-spamming and keeps the interface highly responsive.
- Custom App Icon Extraction: Fixed an issue where selecting a custom application for the Halo Sandbox failed to extract its icon. The dashboard now delegates the icon extraction to the Python backend, natively handling UWP apps and complex shortcuts.
- Mouse Trail Freezing: Fixed an animation bug where the mouse trail in the Halo UI would freeze and remain static on screen when the mouse stopped moving. The trail now correctly dissipates and fades away when stationary.
- Empty Slice Filtering: Empty slices configured in the dashboard are now automatically hidden from the main Halo UI, smoothly spacing the remaining active slices into a perfect circle without gaps.
- Keyboard Navigation: Fixed an issue where WASD and Arrow key navigation for slice selection would fail to register if the physical mouse was stationary.
- Sticky Slice Selection: Slices highlighted using WASD/Arrow keys are now properly deselected immediately upon releasing the keys, preventing sticky highlights.
- Halo Visual Artifacts: Fixed a rendering bug where a square boundary artifact appeared when the mouse trail hit the outer edges of the Halo UI. The active rendering region has been expanded to prevent edge clipping.
- Initial Cursor Visibility: Fixed an issue where the native mouse cursor would flash when opening the Halo over another application. The teleportation of the physical cursor is now deferred until the UI is fully composited by the OS, guaranteeing a seamless transition.
- Closing Cursor Visibility: Fixed a bug where the native mouse cursor would reappear in the center of the screen during the fade-out animation when closing the Halo. The cursor shape is now properly preserved until the fade-out completes.
- Halo DWM Blur Blink: Fixed a visual artifact where the Halo background blur panel would flash at full intensity for a millisecond before the fade-in animation started. The initial window opacity is now bridged seamlessly into the animation loop.
