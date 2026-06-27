"""Deterministic checks for tracker state transitions and placement behavior."""

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow

from core.data_loader import DataLoader
from core.logic_engine import LogicEngine
from core.state_manager import StateManager
from gui.main_window import PersistentDockWidget
from gui.widgets.characters_widget import CharactersCanvas
from gui.widgets.item_grid import ItemGrid
from gui.widgets.maiden_widget import MaidenWidget
from utils.constants import IMAGES_DIR


class MemoryLayout:
    def __init__(self):
        self.data = {}

    def get_position(self, widget_id, name, scale=1.0):
        position = self.data.get(widget_id, {}).get(name)
        if position is None:
            return None
        return round(position[0] * scale), round(position[1] * scale)

    def set_position(self, widget_id, name, x, y, scale=1.0):
        self.data.setdefault(widget_id, {})[name] = (x / scale, y / scale)

    def clear_positions(self, widget_id):
        self.data.pop(widget_id, None)

    def replace_positions(self, widget_id, positions, scale=1.0):
        self.data[widget_id] = {
            name: (position[0] / scale, position[1] / scale)
            for name, position in positions.items()
        }


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    layout = MemoryLayout()

    grid = ItemGrid(
        {"A": {"image_path": "missing.png"}, "B": {"image_path": "missing.png"}},
        IMAGES_DIR,
        "tools",
        layout,
    )
    grid.set_snap_to_grid(False)
    grid._on_item_moved("A", 13, 17)
    require((grid.icons["A"].x(), grid.icons["A"].y()) == (13, 17), "free placement changed coordinates")
    grid.set_icon_scale(2.0)
    require((grid.icons["A"].x(), grid.icons["A"].y()) == (26, 34), "saved placement did not scale")
    grid.set_icon_scale(1.0)
    grid.set_grid_size(10)
    grid.set_snap_to_grid(True)
    grid._on_item_moved("A", 13, 17)
    require((grid.icons["A"].x(), grid.icons["A"].y()) == (10, 20), "grid snap failed")

    data = DataLoader()
    state = StateManager(LogicEngine(data))
    characters = CharactersCanvas(data, state, layout)
    maidens = MaidenWidget(data, state, layout)
    for canvas in (grid, characters, maidens):
        canvas.set_grid_size(10)
        canvas.auto_align()
        widgets = getattr(canvas, "icons", getattr(canvas, "cells", {}))
        require(
            all(widget.x() % 10 == 0 and widget.y() % 10 == 0 for widget in widgets.values()),
            f"auto-align failed for {type(canvas).__name__}",
        )

    state._active_party = {"Guy"}
    state._active_party_list = ["Guy"]
    characters.set_active_party_visible(False)
    require(characters.cells["Guy"].isHidden(), "active party member remained visible")
    require(not characters.cells["Lexis"].isHidden(), "inactive character was hidden")
    characters.set_active_party_visible(True)
    require(not characters.cells["Guy"].isHidden(), "active party member did not return")

    state.refresh_logic()
    cities = set(data.get_cities())
    candidates = {
        name: state.locations[name]
        for name in data.get_locations()
        if name not in cities and state.locations.get(name) in {"not_accessible", "accessible", "fully_accessible"}
    }
    red_dungeon = next((name for name, value in candidates.items() if value == "not_accessible"), None)
    green_dungeon = next((name for name, value in candidates.items() if value in {"accessible", "fully_accessible"}), None)
    require(red_dungeon is not None, "no inaccessible dungeon fixture found")
    require(green_dungeon is not None, "no accessible dungeon fixture found")
    for dungeon in (red_dungeon, green_dungeon):
        initial = candidates[dungeon]
        state.toggle_manual_location_cleared(dungeon)
        require(state.locations[dungeon] == "cleared", "dungeon was not marked cleared")
        state.toggle_manual_location_cleared(dungeon)
        require(state.locations[dungeon] == initial, "dungeon did not return to logic-derived state")

    state._inventory = {"Hammer": True}
    state._characters = {"Lexis": True}
    state.process_auto_update({
        "inventory": [],
        "characters": [],
        "capsules": [],
        "cleared_locations": [],
        "scenario": [],
    })
    require(state._inventory == {"Hammer": True}, "invalid snapshot erased inventory")
    require(state._characters == {"Lexis": True}, "invalid snapshot erased characters")

    host = QMainWindow()
    dock = PersistentDockWidget("Test", host)
    host.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    dock.setFloating(True)
    app.processEvents()
    app.processEvents()
    window_type = dock.windowFlags() & Qt.WindowType.WindowType_Mask
    require(dock.isFloating(), "dock stopped floating while normalizing flags")
    require(window_type == Qt.WindowType.Window, "floating dock remained a tool window")
    require(not bool(dock.windowFlags() & Qt.WindowType.WindowStaysOnTopHint), "floating dock stayed topmost")
    host.close()

    print("UI behavior verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
