# Lufia 2 Auto Tracker v1.4

A modern, robust manual tracker for Lufia 2: Rise of the Sinistrals (SNES), fully refactored in **Python (PyQt6)**.

![Lufia 2 Tracker](https://img.shields.io/badge/Lufia%202-Tracker-blue) ![PyQt6](https://img.shields.io/badge/Built%20With-PyQt6-green)

> [!IMPORTANT]
> **Auto Tracking Status**:
> While this version includes the UI and logic for "Auto Tracking" (via the "Auto" menu), **the feature is currently passive**. It requires an external helper program (or specific emulator Lua script) to send data to its listening port. Without this external data source, the tracker functions purely as a high-quality **Manual Tracker**.

## Features

### 🛠️ Completely Refactored Architecture
Ported from Tkinter to **PyQt6**, offering superior stability, smooth rendering, and a modular "Domain-Driven" codebase.

### 🎨 Fully Customizable UI
*   **Docking System**: Rearrange every panel (Map, Tools, Keys, Characters) to suit your workflow. Create your perfect layout.
*   **Free Placement**: Enable **"Edit Layout"** in Options to drag-and-drop *any* icon (Characters, Tools, Keys) pixel-perfectly within its widget.
*   **Theming**: Customize Dock Header colors and adjust font sizes globally.

### 🗺️ Interactive Map
*   **Zoom & Pan**: Smooth, high-performance map navigation.
*   **Context Aware**: Right-click cities to search/add items; right-click dungeons to assign characters.
*   **Player Tracking**: Manually set your position or customize the player arrow color.

### ⚔️ Comprehensive Tracking
*   **Character & Sprite Logic**: Assign characters to locations, and see their sprites appear on the map.
*   **Item Search**: Built-in database of all Items and Spells. Search, filter, and add them to your inventory.
*   **Scenario Items**: Tracks Keys, Maidens (Claire/Lisa/Marie logic), and Tools.

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

## Controls

*   **Left Click (Map)**: Toggle location logic (Red -> Green -> Grey).
*   **Right Click (Map)**: Open Context Menu (City = Item Search, Dungeon = Char Assign).
*   **Drag & Drop (Characters)**: Drag character sprites from the top dock onto map locations to assign them.
*   **Edit Layout Mode**:
    *   Enable in `Options -> Edit Layout`.
    *   Drag items inside docks to rearrange them.
    *   Layouts are auto-saved to `layout_config.json`.

## Credits
*   **RndmMeme**: Original Creator & Logic.
*   **Abyssonym**: Examples and deep knowledge of Lufia 2 internals.
*   **The3X**: Testing and feedback.
