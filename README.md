# Lufia 2 Auto Tracker v1.4.11

> **Release status:** v1.4.11 is the latest experimental release. A stable designation is pending broader emulator and UI validation.

A modern, robust manual & auto tracker for **Lufia 2: Rise of the Sinistrals** (SNES), fully refactored in **Python (PyQt6)**.

![Lufia 2 Tracker](https://img.shields.io/badge/Lufia%202-Tracker-blue) ![PyQt6](https://img.shields.io/badge/Built%20With-PyQt6-green) ![Theme](https://img.shields.io/badge/Theme-Dark-black)

## New in v1.4.11

*   **Clear Obtained State**: Obtained characters remain fully lit whether active or inactive; location notes already identify where recruits were found.
*   **Editable One-Shot Sync**: Party members from a completed Sync can be manually toggled like every other character. Continuous Auto still restores live emulator state.
*   **Focused Menus**: Layout is grouped into Icon Placement and Panel Arrangement; View and Style options are grouped by purpose.
*   **Current User Guide**: Help documentation now matches independent panels, both grids, current menu paths, syncing, character display, and persistence.

## New in v1.4.10

*   **Readable Canvas Resizing**: Characters and Maidens retain real font and icon sizes while docked; scrollbars appear when a panel is smaller than its content.
*   **Effective Size Controls**: Character/Maiden font and icon controls now change rendered content instead of being cancelled by automatic scene scaling.
*   **Consistent Grid Reset**: Reset and restored picture positions honor the active snap grid.
*   **Independent Panels**: Every panel owns its position, width, and height. Resizing Characters, Maidens, Tools, Keys, Map, Items, or Hints never resizes a neighbour.
*   **Separate Canvas Grid**: The panel workspace has its own optional grid, size, and move/resize snapping, independent from picture placement.
*   **Stable Grid Controls**: Changing either grid's pixel size changes only the ruler; existing pictures and panels are not resized or reflowed.
*   **Window Layout Recovery**: Layout > Reset Window Layout rebuilds the factory free-panel arrangement without changing tracked game state.

## ✨ New in v1.4.9

*   **Durable Diagnostics**: Rotating session and error logs capture Python, Qt, helper, memory-read, emulator-profile, and exception context.
*   **Last-Good-State Protection**: Incomplete or semantically invalid memory snapshots are rejected instead of clearing valid tracker state.
*   **Completion-Only Dungeon Clicks**: Manual clicks now toggle Red/Green ↔ Grey while accessibility remains logic-derived.
*   **Flexible Placement**: Scale-independent positions preserve proportional spacing; optional grids, snapping, grid sizes, and per-canvas auto-align coexist with free placement.
*   **Party Display Filter**: View can hide active human party members from the Characters canvas while leaving inactive recruits and capsule monsters visible.
*   **Normal Floating Windows**: Detached canvases behave as standard windows instead of parent-owned tool windows.

See [LOGGING.md](LOGGING.md) for log locations and diagnostic details.

## ✨ New in v1.4.8

*   **Smaller Standalone Build**: The self-contained helper is trimmed and compressed without requiring users to install .NET.
*   **Trim-Safe Protocol**: Compile-time JSON metadata preserves tracker state, status, and root-hint payloads in optimized builds.
*   **Less Polling Overhead**: Core state changes are compared directly instead of serializing both snapshots every polling cycle.
*   **Release Size Validation**: Self-tests exercise the exact JSON protocol from the final trimmed helper and packaged executable.

## ✨ New in v1.4.7

*   **One Canonical Memory Map**: Every core tracker read now uses a Lufia II WRAM offset instead of an emulator-specific host address.
*   **Root-Based Resolution**: Emulator discovery produces one verified WRAM root and one optional ROM root; all addresses are resolved from those roots.
*   **Single-Anchor Fallbacks**: Historical Snes9x addresses are reduced to root hints. One known gold address reconstructs the WRAM root, which must still pass full validation.
*   **ROM Independence**: ROM discovery uses game signatures and sprite-table validation without assuming a fixed distance from Snes9x WRAM.
*   **Reproducible Diagnostics**: The live verifier can force root-hint-only attachment to test fallback behavior independently.

See [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md) for the address model and contribution rules.

## ✨ New in v1.4.6

*   **Validated Emulator Discovery**: Process names are discovery hints; every candidate must pass Lufia II WRAM validation before the tracker attaches.
*   **WRAM-Only Compatibility**: Inventory, party, dungeon, scenario, and position tracking no longer depend on locating a compatible ROM allocation.
*   **Safer ROM Detection**: Optional ROM features are enabled only after the capsule sprite table is validated.
*   **Automatic Recovery**: Repeated required-memory read failures detach the stale source and trigger a fresh scan.
*   **Visible Status**: The UI reports searching, probing, attached, lost, and error states from the helper.
*   **Reliable Configuration**: Emulator profiles and dungeon mappings resolve from the packaged data directory instead of the current working directory.

## ✨ New in v1.4.5

*   **Scalable Windows**: Converted Maidens and Characters panels to QGraphicsView, allowing contents to scale gracefully when their Dock borders are resized.
*   **Icon Sizing**: Added dedicated (+/-) scaling buttons for picture sizes across all icon-based widgets, including Characters, Maidens, Tools, and Keys.
*   **Recover Widgets**: Centralized accidentally closed docks into a custom 'Recover Widgets' menu options list.
*   **Location Text Toggle**: You can now toggle the text labels identifying where characters are found on/off inside the Custom menu.
*   **City Search Bar**: Formatted the Item Search dropdown as an editable Auto-Complete typing field.
*   **Quality of Life**: Transferred Auto Tracking checkboxes out of the main ribbon into a clean Tracker Dropdown. Purged unreachable map designations from searches.
*   **Bug Fixes & Performance**: 
    *   **Positional Overhead**: Map coordinate tracking has been heavily trimmed to only update when a move occurs without parsing the entire game inventory every frame. 
    *   **Duplicate Sprites**: Prevented auto-tracking from duplicating the same character model across multiple map locations.
    *   **Stability**: Fixed a WRAM pointer truncation math bug in the scanner, implemented port unlocking for rapid app restarts, and prevented UI freezes when the scanner crashes randomly.
    *   **Floating Windows**: Undocked floating windows properly close when terminating the main window.

## ✨ New in v1.4.3

*   **Custom Map Shapes**: You can now define individual map dot shapes for **Cities** and **Dungeons**.
*   **City Color Overrides**: Specify custom colors for unexplored cities, bypassing the default orange.
*   **Layout Recovery**: Added **"Reset Picture Positions"** to quickly restore icon locations to your personalized default.
*   **Instant Tooltips**: Map dot mouse-over delays have been virtually eliminated for lightning-fast location hunting.
*   **Adjustable Logic Rules**: Narvick access rules properly require "Engine" only (formerly allowed "Jade").

## ✨ New in v1.4.2

*   **Active Sprite Marker**: The map player marker can now automatically display the sprite of your **Active Party Leader** (Slot 1).
*   **Global Dark Theme**: A consistent, high-contrast Dark Mode (Fusion Style) ensures readability on all systems.
*   **Persistence**: Your preferences (Colors, Layouts, Marker settings) are now **Auto-Saved** and restored on launch.
*   **Scalable Markers**: Adjust the player marker size from **1x** to **4x**.
*   **Smoother Map**: Improved map rendering quality when resizing the window.
*   **Custom Menu**: All visual settings consolidated into a new "Custom" menu for easy access.

---

## Features

### 🛠️ Architecture
Ported from Tkinter to **PyQt6**, offering superior stability, smooth rendering, and a modular "Domain-Driven" codebase.

### 🎨 Customization
*   **Docking System**: Rearrange every panel (Map, Tools, Keys, Characters) to suit your workflow. Float windows or dock them.
*   **Free or Grid Placement**: Use the *Layout* menu for pixel-perfect dragging, optional grid snapping, and auto-align.
*   **Theming**: Customize Dock Header colors (with auto-contrast text) and Player Marker colors.

### 🗺️ Interactive Map
*   **Zoom & Pan**: Automatic scaling to fit the window.
*   **Context Aware**: Right-click cities to search/add items; right-click dungeons to assign characters.
*   **Player Tracking**: 
    *   **Auto**: Automatically locates a supported emulator and updates position from its WRAM.
    *   **Manual**: Custom marker shapes (Triangle, Rhombus, Square, Sprite).

### ⚔️ Comprehensive Tracking
*   **Character & Sprite Logic**: Assign characters to locations, and see their sprites appear on the map.
*   **Item Search**: Built-in database of all Items and Spells. Search, filter, and add them to your inventory.
*   **Scenario Items**: Tracks Keys, Maidens (Claire/Lisa/Marie logic), and Tools.

### 🎮 Supported Emulators
*   **Snes9x** (x64 and nwa versions supported)
*   **bsnes**
*   **Additional discovery candidates**: RetroArch, Mesen/Mesen-S, higan, ares, and BizHawk/EmuHawk.
*   *Snes9x and bsnes are the verified baseline. Other candidates still require emulator/version-specific validation.*

See [EMULATOR_COMPATIBILITY.md](EMULATOR_COMPATIBILITY.md) for the live verification matrix and reproducible test commands.

---

## Installation & Usage

1.  **Install Python 3.10+**
2.  Install dependencies:
    ```bash
    pip install PyQt6 Pillow
    ```
3.  Run the tracker:
    ```bash
    python src/main.py
    ```
```
Or just use the .exe
```

## Controls

*   **Left Click (Map)**: Toggle dungeon completion (Red/Green ↔ Grey).
*   **Right Click (Map)**: Open Context Menu (City = Item Search, Dungeon = Char Assign).
*   **Drag & Drop (Characters)**: Drag character sprites from the top dock onto map locations to assign them.
*   **Edit Icon Positions**:
    *   Enable in `Layout -> Icon Placement -> Edit Icon Positions`.
    *   Drag items inside docks to rearrange them.
    *   Optionally show a grid, snap while dragging, or auto-align a canvas.
    *   Layouts are auto-saved under `%LOCALAPPDATA%\Lufia2AutoTracker`.

## Development Verification

Run the deterministic helper checks:

```powershell
dotnet run --project src/helper/Lufia2AutoTracker.Helper.csproj --configuration Debug -- --self-test --data-dir src/data
python tools/verify_ui_behaviors.py
```

With an emulator and Lufia II running, verify live discovery and one state payload:

```powershell
python tools/verify_emulator.py
```

Use `python tools/verify_emulator.py --pid <PID>` to isolate one emulator when several are running.

## Credits
*   **RndmMeme**: Original Creator & Logic.
*   **Abyssonym**: Examples and deep knowledge of Lufia 2 internals.
*   **The3X**: Testing and feedback.
