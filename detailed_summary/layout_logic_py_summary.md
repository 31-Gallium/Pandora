# `layout_logic.py` Summary

## Role in Architecture
Provides the mathematical layout engines for determining where icons should be positioned inside a folder in various states (collapsed, expanding, paging).

## Key Classes and Functions
- **`LayoutEngine` (Base Class)**: Defines the interface for all layout engines with methods `get_collapsed_positions`, `get_expanded_params`, and `get_paging_positions`.
- **`GridLayoutEngine`**: 
  - Positions icons in a standard 3x3 grid when collapsed.
  - Returns calculated coordinates for transitioning icons vertically when the user scrolls between pages (`get_paging_positions`).
- **`FlowerLayoutEngine`**:
  - Arranges icons in concentric circular patterns around the center.
  - Handles rotational translations during paging instead of linear vertical scrolling.
- **`get_engine(t_type)`**: Factory function to retrieve the correct layout class based on config.

## Dependencies and Interactions
- Consumed heavily by `folder_panel.py` and `ui_utils.py` to position icons dynamically based on hover progression (`hp`) and page indices.
