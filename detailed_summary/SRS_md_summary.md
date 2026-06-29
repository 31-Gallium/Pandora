# `SRS.md` Summary

## Role in Architecture
The Software Requirements Specification (SRS) document for the Pandora project. It serves as the primary design and requirements documentation.

## Key Contents
- **Introduction**: Defines the purpose (a desktop productivity and customization application) and scope of Pandora.
- **Overall Description**: Details the product's perspective (standalone utility running in the background), functions (custom folder creation, interactive morphing UI, deep customization, radial HUD, Info Pill guidance), and target user base (power users and customization enthusiasts).
- **System Features**: Breaks down features such as Desktop Folder Widgets, Expanded Folder View, Dashboard and Settings Management, Radial HUD, and Info Pill Guidance System.
- **Non-Functional Requirements**: Outlines performance expectations (smooth high-framerate animations), usability, reliability, portability, and visual standards (trackless UI, glassmorphism).

## Dependencies and Interactions
- Documentation file; no code dependencies. Acts as the blueprint for the `PyQt6` and `WinAPI` integrations seen throughout the codebase.
