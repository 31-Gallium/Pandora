# Software Requirements Specification (SRS) for CusFolder

## 1. Introduction

### 1.1 Purpose
The purpose of this document is to outline the software requirements for the "CusFolder" application. It describes the system's functional and non-functional requirements, target environment, and user interactions.

### 1.2 Scope
CusFolder is a desktop productivity and customization application built with Python and PyQt6. It allows users to create highly interactive, visually customizable floating "folders" directly on their desktop. These folders act as visually appealing containers for application shortcuts, files, and games, providing a stylish alternative to the native Windows desktop icon system.

### 1.3 Definitions, Acronyms, and Abbreviations
* **GUI**: Graphical User Interface
* **SRS**: Software Requirements Specification
* **App Icon**: A shortcut or executable file contained within a CusFolder.
* **Morph Animation**: The visual transition when a collapsed desktop folder expands into its grid view.
* **Dashboard**: The central settings and management UI.

---

## 2. Overall Description

### 2.1 Product Perspective
CusFolder operates as a standalone desktop utility on the Windows operating system. It runs in the background (via the system tray) and draws borderless, transparent, frameless windows on the desktop to represent user-created folders. It manages its own internal storage for dragged-and-dropped shortcuts.

### 2.2 Product Functions
* **Creation of Custom Folders**: Users can create multiple independent folder widgets on their desktop.
* **Drag-and-Drop Management**: Users can drag files, URLs, and shortcuts into the folders.
* **Interactive Morphing UI**: Clicking a folder smoothly morphs it into a larger grid view containing its apps.
* **Deep Customization**: Users can change sizes, colors, glow effects, hover animations, and cover images (with blur effects) for all folders globally or individually.
* **Live Preview**: A sandbox environment within the settings dashboard to preview customizations in real-time.
* **App Search and Sorting**: Quick search inside an opened folder and multiple sorting options (Name, Type, Size, Date, Custom).
* **Batch Launching**: Ability to launch all contents of a folder simultaneously.

### 2.3 User Classes and Characteristics
* **Power Users/Gamers**: Users who want a clean desktop but quick access to games and tools, appreciating high-fidelity animations and visual aesthetics.
* **Customization Enthusiasts**: Users who heavily theme their desktop environments and require deep aesthetic control over widgets.

### 2.4 Operating Environment
* **Platform**: Windows Operating System (relies on WinAPI for specific visual hooks and shortcut parsing).
* **Framework**: Python 3.x with PyQt6.

---

## 3. System Features

### 3.1 Desktop Folder Widgets
* **Description**: The core visual component. Independent widgets that sit on the desktop.
* **Functional Requirements**:
  * The system shall render borderless, translucent widgets on the desktop.
  * The widgets shall be draggable by the user to any position on the screen.
  * The position of each folder shall be saved persistently.
  * The widgets shall display a mini-grid preview of their contents and a custom cover image if set.
  * The widgets shall feature interactive hover animations (scaling and glowing).

### 3.2 Expanded Folder View
* **Description**: The view presented when a folder widget is clicked.
* **Functional Requirements**:
  * The system shall animate the transition from the folder widget to the expanded view seamlessly.
  * The expanded view shall display application icons in a paginated grid format.
  * The system shall support scrolling (via mouse wheel) through pages of icons.
  * The user shall be able to drag and drop to reorder icons within the grid.
  * The view shall provide an inline search bar to filter visible icons.
  * The view shall provide options to sort icons by Name, Type, Size, Date, Recently Added, and Custom Order.

### 3.3 Dashboard and Settings Management
* **Description**: The configuration hub accessed via the system tray.
* **Functional Requirements**:
  * The system shall provide a dashboard with a "Global" tab and an "Individual" tab for folder settings.
  * The dashboard shall include a "Live Preview" window demonstrating the visual changes in real-time.
  * **Customizable attributes must include**: Size presets, folder size, mini icon size, font size, expanded icon size, glow intensity, border radius, opacity, cover blur, cover opacity, hover speed, morph speed, and color properties (glow, background, title, highlight).
  * The user shall be able to upload custom images as folder covers.
  * The system shall allow users to reset settings to default values.

### 3.4 Data Persistence and Storage
* **Description**: Handling of configuration and internal shortcut storage.
* **Functional Requirements**:
  * The system shall save all configurations, folder states, and layout positions in a local `config.json` file.
  * The system shall extract and cache icons from executables and shortcuts for fast rendering.
  * Dragged and dropped items shall be moved to an `internal_storage` directory to keep the user's native desktop clean.

---

## 4. Non-Functional Requirements

### 4.1 Performance Requirements
* The application must launch quietly in the background without noticeable system lag.
* Hover and morph animations must run smoothly at a high frame rate without dropping frames, leveraging PyQt6's rendering engine.
* Icon extraction must happen asynchronously or be cached to avoid freezing the UI during folder expansion.

### 4.2 Usability Requirements
* The application must remain accessible via a system tray icon at all times.
* The dashboard UI must employ modern, dark-themed styling with clear contrast and interactive feedback (animated buttons, tooltips).
* The application shall prevent overlapping edge-cases by confining folder dragging within the screen's available geometry.

### 4.3 Reliability
* The application must handle malformed or missing shortcuts gracefully without crashing the expanded view.
* The configuration JSON must be safely written to prevent corruption.

### 4.4 Portability
* While currently targeted and optimized for Windows (using `win32com` and `WinAPI`), the core Qt architecture should be maintained in a way that minimizes cross-platform friction where possible.