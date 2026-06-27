"""Deterministic checks for tracker state transitions and placement behavior."""

import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QWidget

from core.data_loader import DataLoader
from core.logic_engine import LogicEngine
from core.state_manager import StateManager
from gui.main_window import CanvasScrollArea, MainWindow, PersistentDockWidget
from gui.help_dialogs import HelpDialog
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


def send_mouse(widget, event_type, local_pos, global_pos, button, buttons):
    event = QMouseEvent(
        event_type,
        QPointF(local_pos),
        QPointF(global_pos),
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, event)


def max_pixmap_alpha(label):
    image = label.pixmap().toImage()
    return max(
        image.pixelColor(x, y).alpha()
        for y in range(image.height())
        for x in range(image.width())
    )


def submenu_titles(menu):
    return [action.menu().title() for action in menu.actions() if action.menu()]


def main() -> int:
    settings_root = tempfile.TemporaryDirectory()
    os.environ["LUFIA2_TRACKER_SETTINGS_FILE"] = str(Path(settings_root.name) / "tracker-test.ini")
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
    layout.data.setdefault("tools", {})["B"] = (13, 17)
    grid.update_positions()
    require(
        (grid.icons["B"].x(), grid.icons["B"].y()) == (10, 20),
        "saved/reset position ignored active grid",
    )

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
    state._characters = {"Guy": True, "Lexis": True}
    characters.refresh_state()
    characters.set_active_party_visible(False)
    require(characters.cells["Guy"].isHidden(), "active party member remained visible")
    require(not characters.cells["Lexis"].isHidden(), "inactive character was hidden")
    characters.set_active_party_visible(True)
    require(not characters.cells["Guy"].isHidden(), "active party member did not return")
    require(max_pixmap_alpha(characters.cells["Lexis"].icon_label) == 255, "inactive obtained recruit was dimmed")
    characters.toggle_character("Guy")
    require(not state.obtained_characters["Guy"], "one-shot party member could not be toggled off")
    require(max_pixmap_alpha(characters.cells["Guy"].icon_label) < 255, "toggled party member remained fully lit")
    characters.toggle_character("Guy")
    require(state.obtained_characters["Guy"], "one-shot party member could not be toggled on")
    require(max_pixmap_alpha(characters.cells["Guy"].icon_label) == 255, "restored party member remained dimmed")

    guy = characters.cells["Guy"]
    original_icon_width = guy.icon_label.width()
    characters.set_icon_scale(1.2)
    require(guy.icon_label.width() > original_icon_width, "character icon control had no effect")
    characters.set_content_font_size(16)
    require(guy.loc_label.font().pixelSize() >= 15, "character location font did not scale")

    maiden_icon_width = maidens.cells["Claire"].icon_label.width()
    maidens.set_icon_scale(1.2)
    require(maidens.cells["Claire"].icon_label.width() > maiden_icon_width, "maiden icon control had no effect")
    maidens.set_content_font_size(16)
    require(maidens.cells["Claire"].loc_label.font().pixelSize() >= 15, "maiden font control had no effect")

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
    workspace = QWidget(host)
    host.setCentralWidget(workspace)
    dock = PersistentDockWidget("Test", workspace)
    content = QWidget()
    content.setMinimumSize(400, 300)
    dock.setWidget(content)
    dock.setGeometry(10, 10, 300, 200)
    dock.remember_docked_geometry()
    require(isinstance(dock.widget(), CanvasScrollArea), "canvas still uses transform-based scaling")
    require(dock._inner_widget is content, "scroll wrapper lost the real canvas")
    dock.setFloating(True)
    app.processEvents()
    app.processEvents()
    window_type = dock.windowFlags() & Qt.WindowType.WindowType_Mask
    require(dock.isFloating(), "dock stopped floating while normalizing flags")
    require(window_type == Qt.WindowType.Window, "floating dock remained a tool window")
    require(not bool(dock.windowFlags() & Qt.WindowType.WindowStaysOnTopHint), "floating dock stayed topmost")
    host.close()

    window = MainWindow(state, data, state.logic_engine)
    window.resize(1200, 800)
    window.show()
    app.processEvents()

    top_menus = {action.text(): action.menu() for action in window.menu_ribbon.menu_bar.actions()}
    require(submenu_titles(top_menus["Layout"]) == ["Icon Placement", "Panel Arrangement"], "Layout menu groups drifted")
    require(
        "Edit Icon Positions" in [action.text() for action in top_menus["Layout"].actions()[0].menu().actions()],
        "icon editing action was not renamed",
    )
    require(
        submenu_titles(top_menus["View"]) == ["Panel Controls", "Character Display", "Map Sprites"],
        "View menu groups drifted",
    )
    require(
        submenu_titles(top_menus["Style"]) == ["Panel Appearance", "Player Marker", "Map Locations"],
        "Style menu groups drifted",
    )

    guide = HelpDialog()
    guide_text = "\n".join(editor.toPlainText() for editor in guide.findChildren(QTextEdit))
    for expected_guide_text in (
        "New in v1.4.11",
        "Edit Icon Positions",
        "Panel Arrangement",
        "Editable One-Shot Sync",
        "Obtained characters are fully lit",
    ):
        require(expected_guide_text in guide_text, f"User Guide is missing: {expected_guide_text}")
    guide.close()

    picture_widgets = {
        "character": window.characters_widget.canvas.cells["Guy"].icon_label,
        "maiden": window.maiden_widget.cells["Claire"].icon_label,
        "tool": next(iter(window.tools_widget.grid.icons.values())).icon_lbl,
        "key": next(iter(window.scenario_widget.grid.icons.values())).icon_lbl,
    }
    picture_sizes = {name: widget.size() for name, widget in picture_widgets.items()}
    picture_positions = {
        "character": window.characters_widget.canvas.cells["Guy"].pos(),
        "maiden": window.maiden_widget.cells["Claire"].pos(),
        "tool": next(iter(window.tools_widget.grid.icons.values())).pos(),
        "key": next(iter(window.scenario_widget.grid.icons.values())).pos(),
    }
    window._set_grid_snap(True)
    for picture_grid_size in (25, 20, 10, 5, 10, 25):
        window._set_grid_size(picture_grid_size)
        require(
            {name: widget.size() for name, widget in picture_widgets.items()} == picture_sizes,
            "changing picture grid size changed an icon size",
        )
        require(
            {
                "character": window.characters_widget.canvas.cells["Guy"].pos(),
                "maiden": window.maiden_widget.cells["Claire"].pos(),
                "tool": next(iter(window.tools_widget.grid.icons.values())).pos(),
                "key": next(iter(window.scenario_widget.grid.icons.values())).pos(),
            } == picture_positions,
            "changing picture grid size reflowed existing pictures",
        )

    require(window.items_dock.maximumWidth() > 350, "Items width remained artificially capped")
    require(window.hints_dock.maximumWidth() > 350, "Hints width remained artificially capped")
    require(
        all(panel.parentWidget() is window.panel_workspace for panel in window._panels),
        "a docked panel was not placed in the independent workspace",
    )

    maiden_geometry = window.maidens_dock.geometry()
    character_height = window.chars_dock.height()
    edge = QPoint(window.chars_dock.width() // 2, character_height - 2)
    edge_global = window.chars_dock.mapToGlobal(edge)
    send_mouse(
        window.chars_dock, QEvent.Type.MouseButtonPress, edge, edge_global,
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
    )
    send_mouse(
        window.chars_dock, QEvent.Type.MouseMove, edge + QPoint(0, 80), edge_global + QPoint(0, 80),
        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
    )
    send_mouse(
        window.chars_dock, QEvent.Type.MouseButtonRelease, edge + QPoint(0, 80), edge_global + QPoint(0, 80),
        Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
    )
    require(window.chars_dock.height() == character_height + 80, "Character border drag did not resize panel")
    require(window.maidens_dock.geometry() == maiden_geometry, "Character height changed Maiden geometry")

    tools_geometry = window.tools_dock.geometry()
    window.scenario_dock.resize(420, window.scenario_dock.height())
    require(window.tools_dock.geometry() == tools_geometry, "Keys width changed Tools geometry")
    require(window.scenario_dock.width() == 420, "Keys width could not be adjusted independently")

    hints_geometry = window.hints_dock.geometry()
    window.items_dock.resize(450, window.items_dock.height())
    require(window.items_dock.width() == 450, "Items width could not exceed the old cap")
    require(window.hints_dock.geometry() == hints_geometry, "Items width changed Hints geometry")

    map_geometry = window.map_dock.geometry()
    tools_start = window.tools_dock.geometry()
    title_point = QPoint(40, window.tools_dock.title_bar.height() // 2)
    title_global = window.tools_dock.title_bar.mapToGlobal(title_point)
    send_mouse(
        window.tools_dock.title_bar, QEvent.Type.MouseButtonPress, title_point, title_global,
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
    )
    send_mouse(
        window.tools_dock.title_bar, QEvent.Type.MouseMove, title_point + QPoint(30, 20),
        title_global + QPoint(30, 20), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
    )
    send_mouse(
        window.tools_dock.title_bar, QEvent.Type.MouseButtonRelease, title_point + QPoint(30, 20),
        title_global + QPoint(30, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
    )
    require(window.tools_dock.pos() == tools_start.topLeft() + QPoint(30, 20), "panel title drag failed")
    require(window.map_dock.geometry() == map_geometry, "moving Tools changed Map geometry")

    window.panel_workspace.set_grid_size(20)
    window.panel_workspace.set_snap_to_grid(True)
    window.tools_dock.move(293, 242)
    window.tools_dock.finish_geometry_change()
    require(window.tools_dock.pos() == QPoint(300, 240), "panel move did not snap to canvas grid")
    window.scenario_dock.setGeometry(260, 565, 413, 155)
    window.scenario_dock.finish_geometry_change({"right"})
    require(window.scenario_dock.width() == 420, "panel resize did not snap to canvas grid")
    snapped_panel_geometry = window.scenario_dock.geometry()
    window.panel_workspace.set_grid_size(5)
    require(
        window.scenario_dock.geometry() == snapped_panel_geometry,
        "changing canvas grid size resized an existing panel",
    )

    keys_geometry = window.scenario_dock.geometry()
    window.map_dock.resize(window.map_dock.width(), window.map_dock.height() - 100)
    app.processEvents()
    require(window.scenario_dock.geometry() == keys_geometry, "Map height changed Keys geometry")
    window.menu_ribbon.show_canvas_grid_action.setChecked(True)
    window.menu_ribbon.snap_canvas_grid_action.setChecked(True)
    next(
        action for action in window.menu_ribbon.canvas_grid_size_group.actions()
        if action.text() == "20 px"
    ).setChecked(True)
    saved_character_geometry = window.chars_dock.geometry()
    saved_keys_geometry = window.scenario_dock.geometry()
    window.close()

    restored_data = DataLoader()
    restored_logic = LogicEngine(restored_data)
    restored_state = StateManager(restored_logic)
    restored = MainWindow(restored_state, restored_data, restored_logic)
    restored.show()
    app.processEvents()
    require(restored.chars_dock.geometry() == saved_character_geometry, "Character panel geometry was not restored")
    require(restored.scenario_dock.geometry() == saved_keys_geometry, "Keys panel geometry was not restored")
    require(restored.panel_workspace._grid_visible, "Canvas Grid visibility was not restored")
    require(restored.panel_workspace.snap_to_grid, "Canvas Grid snapping was not restored")
    require(restored.panel_workspace.grid_size == 20, "Canvas Grid size was not restored")
    restored.close()
    os.environ.pop("LUFIA2_TRACKER_SETTINGS_FILE", None)
    settings_root.cleanup()

    print("UI behavior verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
