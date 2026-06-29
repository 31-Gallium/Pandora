# `default.py` (hub_modules) Summary

## Role in Architecture
The simplest Hub Module, acting as a fallback when no specific module is selected or active.

## Key Classes and Functions
- **`DefaultLogoHub(BaseHubModule)`**:
  - `draw()`: Renders the Pandora SVG logo (`assets/Pandora.svg`) directly in the center of the screen using `QSvgRenderer`. If the logo file is missing, it falls back to rendering the text "PANDORA".

## Dependencies and Interactions
- Uses `QSvgRenderer`.
- Inherits from `BaseHubModule`.
