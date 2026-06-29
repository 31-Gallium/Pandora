# Graph Report - .  (2026-06-21)

## Corpus Check
- 62 files · ~206,376 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 878 nodes · 1456 edges · 101 communities (86 shown, 15 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 111 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]

## God Nodes (most connected - your core abstractions)
1. `FolderView` - 45 edges
2. `FolderView` - 45 edges
3. `FolderIcon` - 39 edges
4. `MediaDaemon` - 39 edges
5. `FolderIcon` - 36 edges
6. `VectorIcon` - 35 edges
7. `Halo` - 33 edges
8. `Halo` - 33 edges
9. `IconExtractor` - 30 edges
10. `ConfigManager` - 27 edges

## Surprising Connections (you probably didn't know these)
- `AppIcon` --uses--> `IconExtractor`  [INFERRED]
  backup_ui_refactor/app_icon.py → utils.py
- `AppIcon` --uses--> `VectorIcon`  [INFERRED]
  backup_ui_refactor/app_icon.py → utils.py
- `FolderIcon` --uses--> `AppIcon`  [INFERRED]
  ui/folder_icon.py → backup_ui_refactor/app_icon.py
- `FolderView` --uses--> `AppIcon`  [INFERRED]
  ui/folder_view.py → backup_ui_refactor/app_icon.py
- `FolderIcon` --uses--> `ConfigManager`  [INFERRED]
  backup_ui_refactor/folder_icon.py → config.py

## Import Cycles
- None detected.

## Communities (101 total, 15 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (28): currentConfig, { FoldersTab }, { GeneralTab }, { HaloTab }, { initGlobalUI }, { ipcRenderer }, tabs, { TemplatesTab } (+20 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (12): BaseHubModule, BaseHubModule, Override to render module content inside the radial center., Base class for all Hub HUD modules., Called when the module is unloaded., Clock module with digital and analog modes, plus world timezone presets., Swaps the main clock's timezone with the world clock slice at idx., Permanently locks the timezone to the selected clock, saving to config. (+4 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (4): QWidget, BlurTest, TestWin, FolderView

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (10): AnimatedButton, AnimatedMenu, CustomInputDialog, DropdownButton, QDialog, QMenu, QPushButton, AnimatedButton (+2 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (4): MediaDaemon, MediaState, Dedicated thread for all COM audio-peak work.                  COM objects are, main()

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (4): GridOverlay, Send an arbitrary JSON command to all connected Electron clients., WebSocketServerThread, GlobalHook

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (9): AppFetcherThread, AppSelectorDialog, IconLoaderSignals, IconLoaderWorker, Send an arbitrary JSON command to all connected Electron clients., WebSocketServerThread, QFrame, QRunnable (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (3): FlowLayout, QLayout, FlowLayout

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (4): DZCard, DZGrid, DZGridSlot, map_icon_color()

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (7): create_folder(), ElectronDashboardManager, GlobalHook, handle_halo_cmd(), Open the Electron dashboard and navigate to a specific folder's settings., Remove a folder widget from the app_instances list., restore_display_effects()

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (22): 1.1 Purpose, 1.2 Scope, 1.3 Definitions, Acronyms, and Abbreviations, 1. Introduction, 2.1 Product Perspective, 2.2 Product Functions, 2.3 User Classes and Characteristics, 2.4 Operating Environment (+14 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (5): HubManager, DefaultLogoHub, Displays the Pandora logo in the dead zone center., Hub Manager — orchestrates the central hub system. Intelligently switches betwee, Returns MediaHub if track info exists, else TimeHub.

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (8): create_folder(), ElectronDashboardManager, handle_halo_cmd(), HookSignals, Open the Electron dashboard and navigate to a specific folder's settings., Remove a folder widget from the app_instances list., QObject, DesktopMonitor

### Community 18 - "Community 18"
Cohesion: 0.23
Nodes (7): draw_folder_thumbnail(), Shared drawing logic for folder thumbnails., change_system_volume(), get_battery_info(), get_desktop_accent_colors(), get_system_volume_level(), VectorIcon

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (15): author, dependencies, electron-acrylic-window, sortablejs, description, devDependencies, electron, ws (+7 more)

### Community 20 - "Community 20"
Cohesion: 0.17
Nodes (3): main(), SandboxWindow, StdinReader

### Community 24 - "Community 24"
Cohesion: 0.16
Nodes (3): FlowerLayoutEngine, GridLayoutEngine, LayoutEngine

### Community 25 - "Community 25"
Cohesion: 0.35
Nodes (6): get_engine(), handle_app_drop(), Centralized logic for dropping Pandora apps into a folder.     Handles physical, AnimatedMenu, draw_folder_thumbnail(), Shared drawing logic for folder thumbnails.

### Community 26 - "Community 26"
Cohesion: 0.17
Nodes (3): FlowerLayoutEngine, GridLayoutEngine, LayoutEngine

### Community 27 - "Community 27"
Cohesion: 0.25
Nodes (3): handle_app_drop(), Centralized logic for dropping Pandora apps into a folder.     Handles physical, ConfigManager

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (10): 🧲 Advanced Grid Snapping, 🛠️ Architecture Details, 🎨 Beautiful, Fluid Animations, 🚀 How to Use, 💊 Info Pill Guidance, ✨ Key Features, 🖥️ Native Desktop Integration (Win+D Bypass), Pandora (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.31
Nodes (3): DisplayEffectsEngine, Pandora's internal hardware-accelerated screen filter engine.     Uses WinAPI G, Sets the warmth intensity (0.0 to 1.0)

### Community 35 - "Community 35"
Cohesion: 0.40
Nodes (4): acorn, ast, code, fs

### Community 36 - "Community 36"
Cohesion: 0.70
Nodes (4): capture(), press_tilde(), release_tilde(), run_test()

### Community 38 - "Community 38"
Cohesion: 0.83
Nodes (3): get_window_title(), is_window_visible(), main()

## Knowledge Gaps
- **58 isolated node(s):** `{ app, BrowserWindow, ipcMain, nativeTheme }`, `path`, `name`, `version`, `main` (+53 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VectorIcon` connect `Community 18` to `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 14`, `Community 17`, `Community 22`, `Community 23`, `Community 25`, `Community 27`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Why does `ConfigManager` connect `Community 27` to `Community 32`, `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 10`, `Community 11`, `Community 13`, `Community 17`, `Community 20`, `Community 25`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `FolderView` connect `Community 2` to `Community 34`, `Community 3`, `Community 11`, `Community 18`, `Community 22`, `Community 25`, `Community 27`, `Community 31`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `FolderView` (e.g. with `FolderIcon` and `AppIcon`) actually correct?**
  _`FolderView` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `FolderView` (e.g. with `AppIcon` and `AnimatedMenu`) actually correct?**
  _`FolderView` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `FolderIcon` (e.g. with `AppIcon` and `FolderView`) actually correct?**
  _`FolderIcon` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `MediaDaemon` (e.g. with `ElectronDashboardManager` and `GlobalHook`) actually correct?**
  _`MediaDaemon` has 5 INFERRED edges - model-reasoned connections that need verification._