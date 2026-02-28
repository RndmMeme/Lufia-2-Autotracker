# Lufia 2 Auto Tracker v1.4

A modern, robust manual & auto tracker for **Lufia 2: Rise of the Sinistrals** (SNES), fully refactored in **Python (PyQt6)**.

![Lufia 2 Tracker](https://img.shields.io/badge/Lufia%202-Tracker-blue) ![PyQt6](https://img.shields.io/badge/Built%20With-PyQt6-green) ![Theme](https://img.shields.io/badge/Theme-Dark-black)

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
*   **Free Placement**: Enable **"Edit Layout"** in *Custom* menu to drag-and-drop *any* icon pixel-perfectly.
*   **Theming**: Customize Dock Header colors (with auto-contrast text) and Player Marker colors.

### 🗺️ Interactive Map
*   **Zoom & Pan**: Automatic scaling to fit the window.
*   **Context Aware**: Right-click cities to search/add items; right-click dungeons to assign characters.
*   **Player Tracking**: 
    *   **Auto**: Automatically updates position via USB2SNES.
    *   **Manual**: Custom marker shapes (Triangle, Rhombus, Square, Sprite).

### ⚔️ Comprehensive Tracking
*   **Character & Sprite Logic**: Assign characters to locations, and see their sprites appear on the map.
*   **Item Search**: Built-in database of all Items and Spells. Search, filter, and add them to your inventory.
*   **Scenario Items**: Tracks Keys, Maidens (Claire/Lisa/Marie logic), and Tools.

### 🎮 Supported Emulators
*   **Snes9x** (x64 and nwa versions supported)
*   **bsnes**
*   *Likely compatible with others, but verified on the above.*

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

*   **Left Click (Map)**: Toggle location logic (Red -> Green -> Grey).
*   **Right Click (Map)**: Open Context Menu (City = Item Search, Dungeon = Char Assign).
*   **Drag & Drop (Characters)**: Drag character sprites from the top dock onto map locations to assign them.
*   **Edit Layout Mode**:
    *   Enable in `Custom -> Edit Layout`.
    *   Drag items inside docks to rearrange them.
    *   Layouts are auto-saved to `layout_config.json`.

## Credits
*   **RndmMeme**: Original Creator & Logic.
*   **Abyssonym**: Examples and deep knowledge of Lufia 2 internals.
*   **The3X**: Testing and feedback.
