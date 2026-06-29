# `index.html` Summary

## Role in Architecture
The core layout and structure of the Pandora settings dashboard, built to be rendered within an Electron `BrowserWindow`.

## Key Classes and Functions
- Organized into specific layout sections: Titlebar (custom window controls), Sidebar (navigation), and Main Body (tab pages).
- **Tabs**:
  - `General`: Appearance (Grid size, Edge padding, Folder Themes, Wave entrance animations, Display effects presets).
  - `Folders`: Allows adding/editing specific folders. Contains the folder editor layout.
  - `Halo`: Settings for the Radial HUD (Activation key, Mode, Blur level, Arc gap). Features a dynamic `halo-sandbox` area for previewing and modifying radial slices.
- Uses standard HTML5, heavily styled with custom CSS (`style.css`), relying on a `data-tab` and `id` mapping system to interact with JavaScript.

## Dependencies and Interactions
- Relies on `style.css` for presentation.
- Bootstrapped by `renderer.js` and controlled by modules like `ui_dashboard_common.js`, `ui_dashboard_general.js`, etc.
