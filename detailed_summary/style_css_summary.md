# `style.css` Summary

## Role in Architecture
Provides the complete visual styling for the Electron dashboard, governing the look and feel of the settings interface.

## Key Classes and Functions
- **Theming**: Supports three themes: `light-theme`, `gray-theme`, and `desktop-theme` via CSS variables (`--bg`, `--text-1`, `--accent`, etc.).
- **Layout**: Implements a `shell` layout with a custom `titlebar`, collapsible `sidebar`, and a `main` scrolling content area for the tab pages.
- **Custom Controls**: Styles custom components like ranges (sliders) with dynamic `--fill` progress, toggles, custom selects, and the hierarchical settings layout.
- **Search Pill**: Styles the search pill drop-down and result highlighting (`.highlight-pulse`).

## Dependencies and Interactions
- Consumed by `index.html`.
- Dynamic styles (e.g. `--fill`, theme variables) are updated in real-time by JavaScript modules like `ui_dashboard_common.js` and `ui_dashboard_general.js`.
