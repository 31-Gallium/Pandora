# Graph Report - .  (2026-06-14)

## Corpus Check
- 178 files · ~167,323 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1123 nodes · 2406 edges · 95 communities (74 shown, 21 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 382 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Halo|Halo]]
- [[_COMMUNITY_Electron Dashboard|Electron Dashboard]]
- [[_COMMUNITY_Ws Server|Ws Server]]
- [[_COMMUNITY_Qmainwindow|Qmainwindow]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Hub|Hub]]
- [[_COMMUNITY_Qdialog|Qdialog]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Folder View|Folder View]]
- [[_COMMUNITY_Qlineedit|Qlineedit]]
- [[_COMMUNITY_Qimage|Qimage]]
- [[_COMMUNITY_Core Services|Core Services]]
- [[_COMMUNITY_Folder Icon|Folder Icon]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Ui Dz|Ui Dz]]
- [[_COMMUNITY_Qframe|Qframe]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Qmenu|Qmenu]]
- [[_COMMUNITY_Hub Modules|Hub Modules]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Folderview|Folderview]]
- [[_COMMUNITY_Electron Dashboard|Electron Dashboard]]
- [[_COMMUNITY_Electron Dashboard|Electron Dashboard]]
- [[_COMMUNITY_Hub Modules|Hub Modules]]
- [[_COMMUNITY_Qlayout|Qlayout]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Hub Modules|Hub Modules]]
- [[_COMMUNITY_Hub Modules|Hub Modules]]
- [[_COMMUNITY_Hub Modules|Hub Modules]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Hub Modules|Hub Modules]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Layout Logic|Layout Logic]]
- [[_COMMUNITY_Grid Overlay|Grid Overlay]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Core Services|Core Services]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Htmlparser|Htmlparser]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Scratch Analyze|Scratch Analyze]]
- [[_COMMUNITY_Scratch Test|Scratch Test]]
- [[_COMMUNITY_Backup Refactor|Backup Refactor]]
- [[_COMMUNITY_Electron Dashboard|Electron Dashboard]]
- [[_COMMUNITY_Hub Modules|Hub Modules]]
- [[_COMMUNITY_Scratch Minimize|Scratch Minimize]]

## God Nodes (most connected - your core abstractions)
1. `DashboardUI` - 95 edges
2. `FolderView` - 73 edges
3. `VectorIcon` - 49 edges
4. `FolderView` - 48 edges
5. `FlowLayout` - 45 edges
6. `DisplayEffectsEngine` - 44 edges
7. `ConfigManager` - 42 edges
8. `IconExtractor` - 42 edges
9. `WinAPI` - 40 edges
10. `AnimatedMenu` - 39 edges

## Surprising Connections (you probably didn't know these)
- `AppIcon` --uses--> `AnimatedMenu`  [INFERRED]
  app_icon.py → backup_refactor/ui_common.py
- `AppIcon` --uses--> `IconExtractor`  [INFERRED]
  app_icon.py → backup_refactor/utils.py
- `AppIcon` --uses--> `VectorIcon`  [INFERRED]
  app_icon.py → backup_refactor/utils.py
- `FolderIcon` --uses--> `AppIcon`  [INFERRED]
  backup_refactor/folder_icon.py → app_icon.py
- `FolderView` --uses--> `AppIcon`  [INFERRED]
  backup_refactor/folder_view.py → app_icon.py

## Import Cycles
- None detected.

## Communities (95 total, 21 thin omitted)

### Community 0 - "Halo"
Cohesion: 0.05
Nodes (25): AppIcon, draw_folder_thumbnail(), Shared drawing logic for folder thumbnails., ConfigManager, get_engine(), handle_app_drop(), Centralized logic for dropping Pandora apps into a folder.     Handles physical, AnimatedButton (+17 more)

### Community 1 - "Electron Dashboard"
Cohesion: 0.07
Nodes (32): currentConfig, { FoldersTab }, { GeneralTab }, { HaloTab }, { HubTab }, { initGlobalUI }, { ipcRenderer }, tabs (+24 more)

### Community 2 - "Ws Server"
Cohesion: 0.05
Nodes (11): GridOverlay, GlobalHook, DesktopMonitor, create_folder(), ElectronDashboardManager, GlobalHook, handle_halo_cmd(), Open the Electron dashboard and navigate to a specific folder's settings. (+3 more)

### Community 3 - "Qmainwindow"
Cohesion: 0.09
Nodes (3): DashboardUI, Install a low-level mouse hook to catch wheel events during Windows DoDragDrop l, QMainWindow

### Community 4 - "Backup Refactor"
Cohesion: 0.08
Nodes (4): Halo, HubManager, Hub Manager — orchestrates the modular central hub system. Individual modules l, Returns the module corresponding to the current radial menu layer index.

### Community 5 - "Hub"
Cohesion: 0.08
Nodes (4): Halo, HubManager, Hub Manager — orchestrates the modular central hub system. Individual modules l, Returns the module corresponding to the current radial menu layer index.

### Community 6 - "Qdialog"
Cohesion: 0.06
Nodes (11): QDialog, QObject, QRunnable, QThread, AppFetcherThread, AppSelectorDialog, IconLoaderSignals, IconLoaderWorker (+3 more)

### Community 9 - "Qlineedit"
Cohesion: 0.13
Nodes (9): AnimatedStackedWidget, InfoPill, PreviewPanel, SmoothScrollArea, AnimatedButton, QLineEdit, QPushButton, QScrollArea (+1 more)

### Community 10 - "Qimage"
Cohesion: 0.08
Nodes (4): MediaSessionManager, Reactive wrapper for the centralized MediaDaemon service.     Decouples UI modu, MediaHub, QImage

### Community 11 - "Core Services"
Cohesion: 0.13
Nodes (3): MediaDaemon, MediaState, Dedicated thread for all COM audio-peak work.                  COM objects are

### Community 14 - "Ui Dz"
Cohesion: 0.12
Nodes (4): DZCard, DZGrid, DZGridSlot, map_icon_color()

### Community 15 - "Qframe"
Cohesion: 0.17
Nodes (4): Show/hide API key field based on selected provider., QFrame, QWidget, DropdownButton

### Community 17 - "Backup Refactor"
Cohesion: 0.11
Nodes (5): AppFetcherThread, AppSelectorDialog, IconLoaderSignals, IconLoaderWorker, WinAPI

### Community 18 - "Qmenu"
Cohesion: 0.15
Nodes (5): ToolGridButton, AnimatedMenu, CustomInputDialog, DropdownButton, QMenu

### Community 19 - "Hub Modules"
Cohesion: 0.18
Nodes (4): BaseHubModule, Override to render module content inside the radial center., Base class for all Hub HUD modules., Called when the module is unloaded.

### Community 20 - "Backup Refactor"
Cohesion: 0.15
Nodes (6): TemplateTile, get_system_mute(), IconExtractor, COM Callback for Master Volume/Mute changes, VectorIcon, VolumeChangeHandler

### Community 21 - "Backup Refactor"
Cohesion: 0.14
Nodes (3): DropLineEdit, DZGrid, DZGridSlot

### Community 22 - "Folderview"
Cohesion: 0.14
Nodes (3): SandboxFolderIcon, SandboxFolderView, FolderView

### Community 23 - "Electron Dashboard"
Cohesion: 0.12
Nodes (15): author, dependencies, electron-acrylic-window, sortablejs, description, devDependencies, electron, ws (+7 more)

### Community 24 - "Electron Dashboard"
Cohesion: 0.17
Nodes (3): main(), SandboxWindow, StdinReader

### Community 25 - "Hub Modules"
Cohesion: 0.23
Nodes (5): LauncherHub, Circular launcher module for quick app/file launching., Determine which item index the mouse is hovering over., Launch an app/file/command., Get icon pixmap — either extracted from file or custom SVG.

### Community 28 - "Backup Refactor"
Cohesion: 0.13
Nodes (3): Sidebar, SidebarButton, SidebarToggle

### Community 30 - "Hub Modules"
Cohesion: 0.20
Nodes (4): Clock module with digital and analog modes, plus world timezone presets., Swaps the main clock's timezone with the world clock slice at idx., Permanently locks the timezone to the selected clock, saving to config., TimeHub

### Community 31 - "Hub Modules"
Cohesion: 0.16
Nodes (3): Fire completion notification in a background thread., Countdown timer with circular arc, color transitions, and toast notification., TimerHub

### Community 32 - "Hub Modules"
Cohesion: 0.18
Nodes (6): _match_icon(), Match a weather condition string to an icon name., Weather module with hybrid provider support (free wttr.in or user API key)., Free provider: wttr.in (no API key needed)., User API key provider: OpenWeatherMap., WeatherHub

### Community 35 - "Backup Refactor"
Cohesion: 0.17
Nodes (5): ConfigManager, FolderThumbnail, NativeWheelFilter, Small thumbnail used in individual folder settings., QAbstractNativeEventFilter

### Community 36 - "Backup Refactor"
Cohesion: 0.26
Nodes (4): DisplayEffectsEngine, Pandora's internal hardware-accelerated screen filter engine.     Uses WinAPI G, Sets the warmth intensity (0.0 to 1.0), restore_display_effects()

### Community 37 - "Layout Logic"
Cohesion: 0.17
Nodes (3): FlowerLayoutEngine, GridLayoutEngine, LayoutEngine

### Community 45 - "Scratch Analyze"
Cohesion: 0.40
Nodes (4): acorn, ast, code, fs

### Community 50 - "Scratch Minimize"
Cohesion: 0.83
Nodes (3): get_window_title(), is_window_visible(), main()

## Knowledge Gaps
- **36 isolated node(s):** `{ app, BrowserWindow, ipcMain, nativeTheme }`, `path`, `name`, `version`, `main` (+31 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VectorIcon` connect `Backup Refactor` to `Halo`, `Ws Server`, `Qmainwindow`, `Backup Refactor`, `Hub`, `Backup Refactor`, `Folder View`, `Qlineedit`, `Qimage`, `Folder Icon`, `Backup Refactor`, `Ui Dz`, `Backup Refactor`, `Backup Refactor`, `Qmenu`, `Backup Refactor`, `Folderview`, `Hub Modules`, `Backup Refactor`, `Backup Refactor`, `Hub Modules`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`?**
  _High betweenness centrality (0.141) - this node is a cross-community bridge._
- **Why does `DashboardUI` connect `Qmainwindow` to `Halo`, `Backup Refactor`, `Ws Server`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Qlineedit`, `Backup Refactor`, `Backup Refactor`, `Qframe`, `Backup Refactor`, `Backup Refactor`, `Qmenu`, `Backup Refactor`, `Backup Refactor`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `FolderView` connect `Backup Refactor` to `Halo`, `Qmainwindow`, `Qlineedit`, `Folder Icon`, `Backup Refactor`, `Qframe`, `Backup Refactor`, `Backup Refactor`, `Qmenu`, `Backup Refactor`, `Backup Refactor`, `Folderview`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`, `Backup Refactor`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `DashboardUI` (e.g. with `ConfigManager` and `FolderView`) actually correct?**
  _`DashboardUI` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `FolderView` (e.g. with `AnimatedStackedWidget` and `AppFetcherThread`) actually correct?**
  _`FolderView` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Are the 46 inferred relationships involving `VectorIcon` (e.g. with `AppIcon` and `AppIcon`) actually correct?**
  _`VectorIcon` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `FolderView` (e.g. with `AppIcon` and `ConfigManager`) actually correct?**
  _`FolderView` has 6 INFERRED edges - model-reasoned connections that need verification._