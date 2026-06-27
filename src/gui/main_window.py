from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QMenu, QToolBar, QMessageBox, QFileDialog, QInputDialog
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QSettings, QRect, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen
import logging
import os

from core.state_manager import StateManager
from core.data_loader import DataLoader
from core.logic_engine import LogicEngine
from core.layout_manager import LayoutManager
from .map_widget import MapWidget
from .dock_title_bar import DockTitleBar
from .inventory_widgets import ToolsWidget, ScenarioWidget
from .menu_ribbon import MenuRibbon
from utils.version import APP_TITLE
from .widgets.items_widget import ItemsWidget
from .widgets.characters_widget import CharactersWidget
from .widgets.maiden_widget import MaidenWidget
from .widgets.hint_widget import HintWidget
from .dialogs.item_search_dialog import ItemSearchDialog
from PyQt6.QtWidgets import QMenu


def tracker_settings():
    """Use normal registry settings, with an explicit file override for isolated tests."""
    override = os.environ.get("LUFIA2_TRACKER_SETTINGS_FILE")
    if override:
        return QSettings(override, QSettings.Format.IniFormat)
    return QSettings("Lufia2Tracker", "MainWindow")


class PanelWorkspace(QWidget):
    """Free panel surface with an optional, independently configured grid."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid_visible = False
        self._snap_to_grid = False
        self._grid_size = 10

    @property
    def grid_size(self):
        return self._grid_size

    @property
    def snap_to_grid(self):
        return self._snap_to_grid

    def set_grid_visible(self, visible):
        self._grid_visible = bool(visible)
        self.update()

    def set_snap_to_grid(self, enabled):
        self._snap_to_grid = bool(enabled)

    def set_grid_size(self, size):
        self._grid_size = max(5, int(size))
        self.update()

    def snap_value(self, value):
        grid = self._grid_size
        return max(0, ((int(value) + grid // 2) // grid) * grid)

    def snap_geometry(self, geometry, resize_edges=None):
        if not self._snap_to_grid:
            return QRect(geometry)
        rect = QRect(geometry)
        edges = set(resize_edges or ())
        if not edges:
            rect.moveTopLeft(QPoint(self.snap_value(rect.x()), self.snap_value(rect.y())))
            return rect

        if "left" in edges:
            rect.setLeft(self.snap_value(rect.left()))
        if "right" in edges:
            rect.setRight(self.snap_value(rect.right() + 1) - 1)
        if "top" in edges:
            rect.setTop(self.snap_value(rect.top()))
        if "bottom" in edges:
            rect.setBottom(self.snap_value(rect.bottom() + 1) - 1)
        return rect

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._grid_visible:
            return
        painter = QPainter(self)
        pen = QPen(QColor(255, 255, 255, 30))
        pen.setWidth(1)
        painter.setPen(pen)
        for x in range(0, self.width(), self._grid_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), self._grid_size):
            painter.drawLine(0, y, self.width(), y)
        painter.end()

class MainWindow(QMainWindow):
    def __init__(self, state_manager, data_loader, logic_engine):
        super().__init__()
        self.state_manager = state_manager
        self.data_loader = data_loader
        self.logic_engine = logic_engine
        self.layout_manager = LayoutManager()
        
        self.setWindowTitle(APP_TITLE)
        from PyQt6.QtGui import QIcon
        self.setWindowIcon(QIcon("Lufia_2_Auto_Tracker.ico"))
        self.resize(1024, 768)
        
        # --- Menu Ribbon ---
        self.menu_ribbon = MenuRibbon()
        self.setMenuWidget(self.menu_ribbon) # Use setMenuWidget for custom QWidget ribbon

        self._setup_ui()
        self._connect_menu_signals()
        self._connect_signals()
        
        # Connect Listener Signals to UI Feedback
        self.state_manager.auto_update_received.connect(self._on_auto_update_received)
        self.state_manager.tracker_status_changed.connect(self._on_tracker_status_changed)

        self._active_search_dialogs = {}
        self._is_closing = False

        # Initial Refresh to apply Logic
        # Initial Refresh to apply Logic
        self._load_settings()
        self._refresh_all()

    def _setup_ui(self):
        """Initializes the main UI layout."""
        self.panel_workspace = PanelWorkspace(self)
        self.panel_workspace.setObjectName("panel_workspace")
        self.panel_workspace.setMinimumSize(1020, 720)
        self.workspace_scroll = QScrollArea(self)
        self.workspace_scroll.setWidgetResizable(True)
        self.workspace_scroll.setWidget(self.panel_workspace)
        self.workspace_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(self.workspace_scroll)
        self._setup_docking_ui()

    def _connect_menu_signals(self):
        # Auto Toggle
        self.menu_ribbon.auto_toggled.connect(self._handle_auto_toggle)
        self.menu_ribbon.auto_options_changed.connect(self.state_manager.update_tracking_options)
        
        # Font Toggle
        self.menu_ribbon.font_adj_toggled.connect(self._toggle_font_controls)
        self.menu_ribbon.header_color_requested.connect(self._pick_header_color)
        self.menu_ribbon.player_color_requested.connect(self._pick_player_color)
        self.menu_ribbon.player_shape_requested.connect(self._on_player_shape_requested)
        self.menu_ribbon.player_size_requested.connect(self.map_widget.set_player_scale)
        self.menu_ribbon.edit_layout_toggled.connect(self._set_icon_edit_mode)
        self.menu_ribbon.grid_visibility_toggled.connect(self._set_grid_visible)
        self.menu_ribbon.grid_snap_toggled.connect(self._set_grid_snap)
        self.menu_ribbon.grid_size_changed.connect(self._set_grid_size)
        self.menu_ribbon.canvas_grid_visibility_toggled.connect(self.panel_workspace.set_grid_visible)
        self.menu_ribbon.canvas_grid_snap_toggled.connect(self.panel_workspace.set_snap_to_grid)
        self.menu_ribbon.canvas_grid_size_changed.connect(self.panel_workspace.set_grid_size)
        self.menu_ribbon.auto_align_requested.connect(self._auto_align)
        self.menu_ribbon.open_log_folder_requested.connect(self._open_log_folder)
        self.menu_ribbon.restore_windows_requested.connect(self._restore_closed_windows)
        self.menu_ribbon.dock_all_requested.connect(self._dock_all_windows)
        self.menu_ribbon.reset_window_layout_requested.connect(self._reset_window_layout)
        self.menu_ribbon.icon_adj_toggled.connect(self._toggle_icon_controls)
        self.menu_ribbon.locations_text_toggled.connect(self._toggle_locations_text)
        self.menu_ribbon.active_party_visibility_toggled.connect(self._toggle_active_party_visibility)
        
        # Custom Styling overrides
        self.menu_ribbon.city_color_requested.connect(self._pick_city_color)
        self.menu_ribbon.city_shape_requested.connect(self._on_city_shape_requested)
        self.menu_ribbon.dungeon_shape_requested.connect(self._on_dungeon_shape_requested)
        
        # Reset / Save Layout
        self.menu_ribbon.reset_pictures_requested.connect(self._on_reset_pictures_requested)
        self.menu_ribbon.save_layout_default_requested.connect(self._on_save_layout_default_requested)
        
        # Sync Requests
        self.menu_ribbon.sync_requested.connect(self._handle_sync_request)
        
        # Save/Load/Reset
        self.menu_ribbon.reset_requested.connect(self._handle_reset)
        self.menu_ribbon.save_requested.connect(self._handle_save)
        self.menu_ribbon.load_requested.connect(self._handle_load)

    def _toggle_font_controls(self, visible):
        for dock in self._panels:
            dock.title_bar.set_font_controls_visible(visible)

    def _toggle_icon_controls(self, visible):
        for dock in self._panels:
            dock.title_bar.set_icon_controls_visible(visible)
            
    def _toggle_locations_text(self, visible):
        if hasattr(self, 'characters_widget'):
            self.characters_widget.canvas.set_locations_visible(visible)
        if hasattr(self, 'maiden_widget'):
            self.maiden_widget.set_locations_visible(visible)

    def _toggle_active_party_visibility(self, visible):
        self.characters_widget.set_active_party_visible(visible)
            
    def _restore_closed_windows(self):
        for dock in self._panels:
            if dock.isHidden():
                dock.show()

    def _dock_all_windows(self):
        for dock in self._panels:
            if dock.isFloating():
                dock.setFloating(False)
            if dock.isHidden():
                dock.show()

    def _reset_window_layout(self):
        """Restore the independently resizable factory panel arrangement."""
        self._apply_default_dock_layout()
        logging.info("Default window layout restored")

    def _pick_header_color(self):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(initial=Qt.GlobalColor.darkGray, parent=self, title="Pick Header Color")
        if color.isValid():
            hex_color = color.name()
            self._header_color = hex_color # Store for persistence
            for dock in self._panels:
                dock.title_bar.set_header_color(hex_color)

    def _pick_player_color(self):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(initial=Qt.GlobalColor.magenta, parent=self, title="Pick Player Color")
        if color.isValid():
            hex_color = color.name()
            self._player_color = hex_color # Store for persistence
            self.map_widget.set_player_arrow_color(hex_color)

    def _set_icon_edit_mode(self, enabled: bool):
        """Allow icon movement inside panels; panel movement is always separate."""
        self.tools_widget.set_edit_mode(enabled)
        self.scenario_widget.set_edit_mode(enabled)
        self.characters_widget.set_edit_mode(enabled)
        self.maiden_widget.set_edit_mode(enabled)

    def _positioning_canvases(self):
        return {
            "tools": self.tools_widget.grid,
            "keys": self.scenario_widget.grid,
            "characters": self.characters_widget.canvas,
            "maidens": self.maiden_widget,
        }

    def _set_grid_visible(self, visible: bool):
        for canvas in self._positioning_canvases().values():
            canvas.set_grid_visible(visible)

    def _set_grid_snap(self, enabled: bool):
        for canvas in self._positioning_canvases().values():
            canvas.set_snap_to_grid(enabled)

    def _set_grid_size(self, size: int):
        for canvas in self._positioning_canvases().values():
            canvas.set_grid_size(size)

    def _refresh_picture_positions(self):
        """Reapply saved/default positions using the current scale and grid."""
        self.characters_widget.canvas._reflow_grid()
        self.maiden_widget.update_positions()
        self.tools_widget.grid.update_positions()
        self.scenario_widget.grid.update_positions()

    def _auto_align(self, canvas_id: str):
        canvases = self._positioning_canvases()
        targets = canvases.values() if canvas_id == "all" else [canvases[canvas_id]]
        for canvas in targets:
            canvas.auto_align()
        logging.info("Canvas auto-align complete | target=%s", canvas_id)

    def _open_log_folder(self):
        try:
            import os
            from utils.logging_config import get_log_directory
            os.startfile(get_log_directory())
        except Exception:
            logging.exception("Failed to open log folder")
        
    def _handle_reset(self):
        self.state_manager.reset_state()

    def _handle_save(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save Tracker State", "", "JSON Files (*.json)")
        if path:
            try:
                self.state_manager.save_state(path)
            except Exception:
                logging.exception("Tracker state save failed | path=%s", path)

    def _handle_load(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Load Tracker State", "", "JSON Files (*.json)")
        if path:
            try:
                self.state_manager.load_state(path)
                self._refresh_all()
            except Exception:
                logging.exception("Tracker state load failed | path=%s", path)

    def _handle_auto_toggle(self, active: bool):
        """
        Auto: Full tracking.
        Active = Start Listening.
        Inactive = Stop Listening.
        """
        if active:
            self.menu_ribbon.set_scanning_status(True)
        else:
            self.menu_ribbon.set_scanning_status(False)
        self.state_manager.toggle_auto_tracking(active)

    def _handle_sync_request(self, category):
        """
        Sync: Fetch snapshot.
        If Auto is OFF: Start Helper momentarily.
        """
        logging.info("Sync requested | category=%s | helper_running=%s", category, self.state_manager.helper.running)
        self.menu_ribbon.set_scanning_status(True)
        if self.state_manager.helper.running:
            self.state_manager.request_rescan()
            return

        self._is_syncing = True
        self._sync_category = category
        self.state_manager.toggle_auto_tracking(True)

    def _pick_city_color(self):
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QColor
        color = QColorDialog.getColor(initial=QColor("orange"), parent=self, title="Pick City Color")
        if color.isValid():
            hex_color = color.name()
            self._city_color = hex_color
            self.map_widget.set_city_color_override(hex_color)

    def _on_city_shape_requested(self, shape):
        self._city_shape = shape
        self.map_widget.set_city_shape(shape)

    def _on_dungeon_shape_requested(self, shape):
        self._dungeon_shape = shape
        self.map_widget.set_dungeon_shape(shape)

    def _on_save_layout_default_requested(self):
        """Saves current drag-and-drop widget layout as the user's default fallback configuration."""
        self.layout_manager.save_custom_as_default()

    def _on_reset_pictures_requested(self):
        self.layout_manager.reset_layout()
        self._refresh_picture_positions()

    def _on_player_shape_requested(self, shape):
        if shape == "sprite":
             self._update_player_sprite_if_active()
             self.map_widget.set_player_arrow_shape("sprite")
        else:
             self.map_widget.set_player_arrow_shape(shape)

    def _update_player_sprite_if_active(self):
        leader = self.state_manager.get_active_party_leader()
        if leader:
             chars_data = self.data_loader.load_json("characters.json")
             if leader in chars_data:
                  path = self.data_loader.resolve_image_path(chars_data[leader]["image_path"])
                  self.map_widget.set_player_sprite_image(path)

    def _on_auto_update_received(self, payload):
        """Called when StateManager processes an update."""
        try:
            # Hide scanning indicator
            self.menu_ribbon.set_scanning_status(False)
            
            # A one-shot sync stops only after a complete helper snapshot.
            valid_snapshot = (
                "error" not in payload and
                payload.get("inventory") is not None and
                bool(payload.get("characters"))
            )
            if getattr(self, '_is_syncing', False) and valid_snapshot:
                self.state_manager.toggle_auto_tracking(False)
                self._is_syncing = False
                logging.info("Sync snapshot complete | category=%s", getattr(self, "_sync_category", "all"))
            
            # StateManager processes this signal first; this slot refreshes the UI once.
            self._refresh_all()
            # Ensure sprite image is up to date if reusing "sprite" mode
            self._update_player_sprite_if_active()
        except Exception:
            logging.exception("Auto-update UI refresh failed")

    def _on_tracker_status_changed(self, status):
        """Display structured helper discovery and attachment status."""
        self.menu_ribbon.set_tracker_status(
            status.get("state", "scanning"),
            status.get("message", "Scanning for emulator...")
        )

    def _setup_docking_ui(self):
        # Each panel is an absolute child of the workspace. No splitter owns a
        # neighbour's border, so every width and height is independent.
        self.items_dock = PersistentDockWidget("Items / Spells", self.panel_workspace, scale_contents=False)
        self.items_dock.setObjectName("items_dock")
        self.items_widget = ItemsWidget(self.state_manager)
        self.items_dock.setWidget(self.items_widget)
        self.items_dock.setMinimumSize(100, 100)

        self.hints_dock = PersistentDockWidget("Hints", self.panel_workspace, scale_contents=False)
        self.hints_dock.setObjectName("hints_dock")
        self.hint_widget = HintWidget()
        self.hints_dock.setWidget(self.hint_widget)
        self.hints_dock.setMinimumSize(100, 100)
        
        self.chars_dock = PersistentDockWidget("Characters", self.panel_workspace)
        self.chars_dock.setObjectName("chars_dock")
        self.characters_widget = CharactersWidget(self.data_loader, self.state_manager, self.layout_manager)
        self.chars_dock.setWidget(self.characters_widget)
        self.chars_dock.setMinimumSize(100, 150)
        
        self.tools_dock = PersistentDockWidget("Tools", self.panel_workspace, scale_contents=False)
        self.tools_dock.setObjectName("tools_dock")
        self.tools_widget = ToolsWidget(self.data_loader, self.layout_manager)
        self.tools_dock.setWidget(self.tools_widget)
        self.tools_dock.setMinimumSize(100, 60)

        self.maidens_dock = PersistentDockWidget("Maidens", self.panel_workspace)
        self.maidens_dock.setObjectName("maidens_dock")
        self.maiden_widget = MaidenWidget(self.data_loader, self.state_manager, self.layout_manager)
        self.maidens_dock.setWidget(self.maiden_widget)
        self.maidens_dock.setMinimumSize(100, 60)
        
        self.scenario_dock = PersistentDockWidget("Keys", self.panel_workspace, scale_contents=False)
        self.scenario_dock.setObjectName("scenario_dock")
        self.scenario_widget = ScenarioWidget(self.data_loader, self.layout_manager)
        self.scenario_dock.setWidget(self.scenario_widget)
        self.scenario_dock.setMinimumSize(100, 80)
        
        self.map_dock = PersistentDockWidget("World Map", self.panel_workspace, scale_contents=False)
        self.map_dock.setObjectName("map_dock")
        self.map_widget = MapWidget(self.data_loader)
        self.map_dock.setWidget(self.map_widget)
        self.map_dock.setMinimumSize(200, 200)

        self._panels = [
            self.items_dock, self.hints_dock, self.chars_dock, self.tools_dock,
            self.maidens_dock, self.scenario_dock, self.map_dock,
        ]

        self._apply_default_dock_layout()

    def _apply_default_dock_layout(self):
        """Place independent panels with gaps instead of shared splitters."""
        for dock in self._panels:
            if dock.isFloating():
                dock.setFloating(False)
            dock.show()
        defaults = {
            self.items_dock: QRect(0, 0, 255, 260),
            self.hints_dock: QRect(0, 265, 255, 455),
            self.chars_dock: QRect(260, 0, 760, 220),
            self.tools_dock: QRect(260, 225, 280, 200),
            self.maidens_dock: QRect(260, 430, 280, 130),
            self.scenario_dock: QRect(260, 565, 280, 155),
            self.map_dock: QRect(545, 225, 475, 495),
        }
        for panel, geometry in defaults.items():
            panel.setGeometry(geometry)
            panel.remember_docked_geometry()
            panel.raise_()
        self.panel_workspace.setMinimumSize(1020, 720)
        viewport = self.workspace_scroll.viewport().size()
        self.panel_workspace.resize(max(1020, viewport.width()), max(720, viewport.height()))


    def _connect_signals(self):
        # State Manager Signals -> UI Updates
        self.state_manager.location_changed.connect(self.map_widget.update_dot_color)
        self.state_manager.player_position_changed.connect(self.map_widget.update_player_position)
        # Inventory Widgets connect themselves
        self.tools_widget.connect_signals(self.state_manager)
        self.scenario_widget.connect_signals(self.state_manager)
        
        # Logic Loop Trigger (Inventory Change -> Refresh All)
        self.state_manager.inventory_changed.connect(lambda _: self._refresh_all())
        
        # UI Signals -> State Manager Overrides
        self.menu_ribbon.reset_requested.connect(self.state_manager.reset_state)
        self.map_widget.location_clicked.connect(self._handle_location_click)
        self.map_widget.location_right_clicked.connect(self._handle_location_right_click)
        self.items_widget.add_requested.connect(self._open_item_search)

        # Character Signals
        self.state_manager.character_assigned.connect(self._on_character_assigned)
        self.state_manager.character_unassigned.connect(self.map_widget.remove_character_sprite)
        self.state_manager.character_changed.connect(lambda n, o: self.characters_widget.refresh_state())
        
        # Map Sprite Removal Interactivity
        self.map_widget.sprite_removed.connect(self.state_manager.remove_character_assignment)
        
        # Reset Signal
        self.state_manager.reset_occurred.connect(self._on_reset_occurred)
        
        # New Signals (v1.4 Refinements)
        self.menu_ribbon.sprite_visibility_toggled.connect(self.map_widget.set_sprites_visibility)
        self.state_manager.shop_items_changed.connect(lambda _: self.items_widget.refresh_from_state())
        
        # Hints
        if self.hint_widget:
            self.hint_widget.hints_changed.connect(self.state_manager.update_hints)
            self.state_manager.hints_changed.connect(self.hint_widget.set_hints)

    def _on_reset_occurred(self):
        """Clears UI elements that aren't strictly data-bound to StateManager properties (like Hints/Map Sprites)."""
        # Clear Hints
        if self.hint_widget:
            self.hint_widget.set_hints("")
            
        # Clear Map Sprites/Player
        if self.map_widget:
            self.map_widget.reset()
            
        # Clear Items/Spells
        if self.items_widget:
            self.items_widget.clear_all()
            
        # Reflow/Clear Characters (Bugfix: They weren't wiping cleanly on tracker reset)
        if self.characters_widget:
            self.characters_widget.refresh_state()
            
        # Refresh Logic (Just in case)
        self._refresh_all()
        logging.info("MainWindow: Reset UI elements.")

    def _refresh_all(self):
        """Re-runs logic engine and pushes updates."""
        # Get Accessibility Map
        accessibility = self.logic_engine.calculate_accessibility(self.state_manager.inventory)
        
        # Current Location States (Overrides + Cleared)
        current_loc_states = self.state_manager.locations
        
        # Update every dot on the map
        locations_data = self.data_loader.get_locations() # {name: coords}
        for name in locations_data.keys():
            is_accessible = accessibility.get(name, False)
            
            # Check if this location is "cleared" in the state
            is_cleared = (current_loc_states.get(name) == "cleared")
            
            # Determine color
            final_color = self.logic_engine.determine_color(name, is_accessible, is_cleared)
            
            # Use StateManager's effective state if present
            effective_state = current_loc_states.get(name)
            if effective_state:
                final_color = effective_state
            
            # Tooltip Info
            tooltip_text = name
            if not is_accessible and final_color == "not_accessible":
                # Get missing info
                reqs = self.logic_engine.get_missing_requirements(name, self.state_manager.inventory)
                if reqs:
                    req_str = " OR ".join(reqs)
                    tooltip_text += f"\nRequires: {req_str}"
            
            self.map_widget.update_dot_color(name, final_color)
            self.map_widget.update_dot_tooltip(name, tooltip_text)

    def _handle_location_click(self, name):
        """Toggle dungeon completion while leaving accessibility logic-derived."""
        if name in self.data_loader.get_cities():
            return
        self.state_manager.toggle_manual_location_cleared(name)

    def _handle_location_right_click(self, name):
        """Show Context Menu."""
        logging.info(f"Right clicked {name}")
        
        cities = self.data_loader.get_cities()
        if name in cities:
            return # Context menu removed for cities
        else:
            self._open_character_assignment(name)

    def _open_character_assignment(self, location_name):
        menu = QMenu(self)
        menu.setTitle(f"Assign to {location_name}")
        
        # Get all chars
        chars_data = self.data_loader.load_json("characters.json")
        sorted_names = sorted(chars_data.keys())
        
        # Filter: Exclude characters currently in active party
        # StateManager knows "active_party" (The 4 humans).
        active_party = self.state_manager.active_party
        
        # Also exclude characters that are already obtained/assigned?
        # v1.3: "not active and not colored". Colored = Obtained/Assigned.
        obtained_map = self.state_manager.obtained_characters 
        
        # Get assigned chars
        assigned_chars = set(self.state_manager._character_locations.values())

        for char in sorted_names:
            if char in ["Claire", "Lisa", "Marie"]: continue
            
            # Allow active party members IF they are not currently assigned to a location
            # (Matches v1.3 "User can assign them map locations")
                
            # If already assigned to ANY location, skip (must remove first to re-assign)
            if char in assigned_chars:
                continue
                
            action = menu.addAction(char)
            action.triggered.connect(lambda c, ch=char: self.state_manager.assign_character_to_location(location_name, ch))
        
        # Option to Remove existing?
        existing = self.state_manager.get_character_at_location(location_name)
        if existing:
            menu.addSeparator()
            rem_action = menu.addAction(f"Remove {existing}")
            rem_action.triggered.connect(lambda: self.state_manager.remove_character_assignment(location_name))
            
        if menu.isEmpty():
            disabled = menu.addAction("No characters available")
            disabled.setEnabled(False)

        menu.exec(self.map_widget.cursor().pos())

    def _on_character_assigned(self, location, name):
        # Resolve path
        chars_data = self.data_loader.load_json("characters.json")
        
        # Fix for crash if name not in json (e.g. Shaggy)
        if name not in chars_data:
            logging.warning(f"Character '{name}' not found in characters.json. Skipping map sprite.")
            return

        rel_path = chars_data[name]["image_path"]
        full_path = self.data_loader.resolve_image_path(rel_path)
        
        self.map_widget.add_character_sprite(location, name, full_path)


    def _open_item_search(self, location_name=None):
        if not location_name:
            cities = getattr(self, '_cities_cache', None)
            if not cities:
                 cities = self.data_loader.get_cities()
                 self._cities_cache = cities
            
            # Sort for deterministic first element or use first
            sorted_cities = sorted(list(cities))
            location_name = sorted_cities[0] if sorted_cities else ""

        # Parent=None to allow independent window (Taskbar entry, Alt-Tab, free movement)
        dlg = ItemSearchDialog(location_name, self.data_loader, parent=None)
        dlg.item_added.connect(self._on_shop_item_added)
        
        def highlight_loc(name):
             self.map_widget.highlight_location(name)
             
        dlg.location_changed.connect(highlight_loc)
        highlight_loc(location_name)
        
        dlg.exec() # Blocking
        self.map_widget.clear_highlight()
        
        self.map_widget.clear_highlight()
        
        # Cleanup
        dlg.deleteLater()

    # removed _on_search_dialog_closed as not needed with blocking exec

    def _on_shop_item_added(self, location, item_name):
        # Add to Items Widget
        self.items_widget.add_item(location, item_name)
        # Future: Update StateManager if needed?

    def closeEvent(self, event):
        # Save Window State
        settings = tracker_settings()
        try:
             settings.setValue("geometry", self.saveGeometry())
             settings.setValue("panelLayoutV3", True)
             for panel in self._panels:
                 key = f"panelsV3/{panel.objectName()}"
                 panel.remember_docked_geometry()
                 settings.setValue(f"{key}/dockedGeometry", panel.docked_geometry())
                 settings.setValue(f"{key}/floating", panel.isFloating())
                 settings.setValue(f"{key}/visible", panel.isVisible())
                 settings.setValue(f"{key}/fontSize", panel.current_font_size)
                 settings.setValue(f"{key}/iconScale", panel.current_icon_scale)
                 if panel.isFloating():
                     settings.setValue(f"{key}/floatingGeometry", panel.geometry())
             
             # Save Persistence preferences
             settings.setValue("headerColor", getattr(self, "_header_color", ""))
             settings.setValue("playerColor", getattr(self, "_player_color", ""))
             settings.setValue("playerShape", getattr(self.map_widget, "_player_shape", "triangle"))
             settings.setValue("playerScale", getattr(self.map_widget, "_player_scale", 1.0))
             settings.setValue("showPlacementGrid", self.menu_ribbon.show_grid_action.isChecked())
             settings.setValue("snapToPlacementGrid", self.menu_ribbon.snap_grid_action.isChecked())
             settings.setValue("placementGridSize", self._positioning_canvases()["tools"].grid_size)
             settings.setValue("showCanvasGrid", self.menu_ribbon.show_canvas_grid_action.isChecked())
             settings.setValue("snapPanelsToCanvasGrid", self.menu_ribbon.snap_canvas_grid_action.isChecked())
             settings.setValue("canvasGridSize", self.panel_workspace.grid_size)
             settings.setValue("showActivePartyMembers", self.menu_ribbon.active_party_action.isChecked())

        except Exception:
             logging.exception("Failed to save window settings")
        
        # Shutdown logic
        if hasattr(self, 'auto_tracker_thread') and self.auto_tracker_thread and self.auto_tracker_thread.isRunning():
            self.auto_tracker_thread.stop()
            self.auto_tracker_thread.wait()
            
        # Force close all docks (Floating docks become top-level windows and might persist)
        self._is_closing = True
        for dock in self._panels:
            dock.close()
            
        super().closeEvent(event)

    def _load_settings(self):
        settings = tracker_settings()
        geometry = settings.value("geometry")
        
        if geometry:
            self.restoreGeometry(geometry)

        if settings.value("panelLayoutV3", False, type=bool):
            for panel in self._panels:
                key = f"panelsV3/{panel.objectName()}"
                docked_geometry = settings.value(f"{key}/dockedGeometry")
                if isinstance(docked_geometry, QRect) and docked_geometry.isValid():
                    panel.setGeometry(docked_geometry)
                    panel.remember_docked_geometry()

                font_size = settings.value(f"{key}/fontSize", 11, type=int)
                panel.current_font_size = max(8, min(24, font_size))
                panel._apply_panel_style()
                if panel._inner_widget and hasattr(panel._inner_widget, "set_content_font_size"):
                    panel._inner_widget.set_content_font_size(panel.current_font_size)

                icon_scale = settings.value(f"{key}/iconScale", 1.0, type=float)
                panel.current_icon_scale = max(0.5, min(3.0, icon_scale))
                if panel._inner_widget and hasattr(panel._inner_widget, "set_icon_scale"):
                    panel._inner_widget.set_icon_scale(panel.current_icon_scale)

                if settings.value(f"{key}/floating", False, type=bool):
                    panel.setFloating(True)
                    floating_geometry = settings.value(f"{key}/floatingGeometry")
                    if isinstance(floating_geometry, QRect) and floating_geometry.isValid():
                        panel.setGeometry(floating_geometry)
                if not settings.value(f"{key}/visible", True, type=bool):
                    panel.hide()
            
        # Restore Preferences
        h_color = settings.value("headerColor")
        if h_color:
            self._header_color = h_color
            for dock in self._panels:
                dock.title_bar.set_header_color(h_color)
                
        p_color = settings.value("playerColor")
        if p_color:
            self._player_color = p_color
            self.map_widget.set_player_arrow_color(p_color)
            
        p_shape = settings.value("playerShape")
        if p_shape:
            # If shape was sprite, this might fail if leader isn't ready, but logic handles update later?
            # self.map_widget.set_player_arrow_shape(p_shape)
            # Actually, MainWindow._on_player_shape_requested calls set_player_arrow_shape AND logic.
            # Let's call our handler to ensure consistency
            self._on_player_shape_requested(p_shape)
        
        p_scale = settings.value("playerScale", type=float)
        if p_scale:
            self.map_widget.set_player_scale(p_scale)

        grid_size = settings.value("placementGridSize", 10, type=int)
        for action in self.menu_ribbon.grid_size_group.actions():
            if action.text() == f"{grid_size} px":
                action.setChecked(True)
                break
        self.menu_ribbon.show_grid_action.setChecked(
            settings.value("showPlacementGrid", False, type=bool)
        )
        self.menu_ribbon.snap_grid_action.setChecked(
            settings.value("snapToPlacementGrid", False, type=bool)
        )

        canvas_grid_size = settings.value("canvasGridSize", 10, type=int)
        for action in self.menu_ribbon.canvas_grid_size_group.actions():
            if action.text() == f"{canvas_grid_size} px":
                action.setChecked(True)
                break
        self.menu_ribbon.show_canvas_grid_action.setChecked(
            settings.value("showCanvasGrid", False, type=bool)
        )
        self.menu_ribbon.snap_canvas_grid_action.setChecked(
            settings.value("snapPanelsToCanvasGrid", False, type=bool)
        )
        self.menu_ribbon.active_party_action.setChecked(
            settings.value("showActivePartyMembers", True, type=bool)
        )


class CanvasScrollArea(QScrollArea):
    """Keep canvas text and icons at their requested size; scroll when space is tight."""
    def __init__(self, widget):
        super().__init__()
        self.setWidgetResizable(True)
        self.setWidget(widget)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent; border: none;")

    def refresh_content_size(self):
        content = self.widget()
        if content:
            content.updateGeometry()
        self.viewport().update()

class PersistentDockWidget(QFrame):
    """Free-positioned panel with independent resizing and optional top-level floating."""
    topLevelChanged = pyqtSignal(bool)
    RESIZE_MARGIN = 6

    def __init__(self, title, parent=None, scale_contents=True):
        super().__init__(parent)
        self.scale_contents = scale_contents
        self._inner_widget = None
        self._display_widget = None
        self._workspace = parent
        self._main_window = parent.window() if parent else None
        self._floating = False
        self._docked_geometry = QRect()
        self.movement_locked = False
        self._resize_edges = set()
        self._resize_start_global = None
        self._resize_start_geometry = None
        self.current_font_size = 11
        self.current_icon_scale = 1.0

        self.setWindowTitle(title)
        self.setMouseTracking(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._panel_layout = QVBoxLayout(self)
        self._panel_layout.setContentsMargins(
            self.RESIZE_MARGIN, self.RESIZE_MARGIN,
            self.RESIZE_MARGIN, self.RESIZE_MARGIN,
        )
        self._panel_layout.setSpacing(0)
        self.title_bar = DockTitleBar(title, self)
        self._panel_layout.addWidget(self.title_bar)
        self.topLevelChanged.connect(self._normalize_floating_window)
        self._apply_panel_style()

    def _apply_panel_style(self):
        self.setStyleSheet(f"""
            PersistentDockWidget {{ border: 1px solid #555; background-color: #2b2b2b; }}
            QWidget {{ font-size: {self.current_font_size}px; }}
        """)

    def setWidget(self, widget):
        if self._display_widget is not None:
            self._panel_layout.removeWidget(self._display_widget)
            self._display_widget.setParent(None)
        self._inner_widget = widget
        if widget is None:
            self._display_widget = None
            return
        self._display_widget = CanvasScrollArea(widget) if self.scale_contents else widget
        self._panel_layout.addWidget(self._display_widget, 1)

    def widget(self):
        return self._display_widget

    def set_movement_locked(self, locked: bool):
        self.movement_locked = bool(locked)

    def move_panel(self, position: QPoint):
        if self._floating:
            self.move(position)
            return
        self.move(max(0, position.x()), max(0, position.y()))
        self._grow_workspace_to_fit()

    def finish_geometry_change(self, resize_edges=None):
        if not self._floating:
            if hasattr(self._workspace, "snap_geometry"):
                snapped = self._workspace.snap_geometry(self.geometry(), resize_edges)
                if snapped.width() < self.minimumWidth():
                    snapped.setWidth(self.minimumWidth())
                if snapped.height() < self.minimumHeight():
                    snapped.setHeight(self.minimumHeight())
                self.setGeometry(snapped)
            self.remember_docked_geometry()
            self._fit_workspace_to_panels()

    def remember_docked_geometry(self):
        if not self._floating:
            self._docked_geometry = QRect(self.geometry())

    def docked_geometry(self):
        return QRect(self._docked_geometry)

    def _grow_workspace_to_fit(self):
        if self._floating or self._workspace is None:
            return
        required_width = max(self._workspace.minimumWidth(), self.x() + self.width())
        required_height = max(self._workspace.minimumHeight(), self.y() + self.height())
        self._workspace.setMinimumSize(required_width, required_height)

    def _fit_workspace_to_panels(self):
        if self._floating or self._workspace is None:
            return
        panels = self._workspace.findChildren(
            PersistentDockWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
        )
        required_width = max([1020] + [panel.x() + panel.width() for panel in panels])
        required_height = max([720] + [panel.y() + panel.height() for panel in panels])
        self._workspace.setMinimumSize(required_width, required_height)

    def _edges_at(self, position):
        edges = set()
        if position.x() <= self.RESIZE_MARGIN:
            edges.add("left")
        elif position.x() >= self.width() - self.RESIZE_MARGIN:
            edges.add("right")
        if position.y() <= self.RESIZE_MARGIN:
            edges.add("top")
        elif position.y() >= self.height() - self.RESIZE_MARGIN:
            edges.add("bottom")
        return edges

    def _set_resize_cursor(self, edges):
        if edges in ({"left", "top"}, {"right", "bottom"}):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges in ({"right", "top"}, {"left", "bottom"}):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif "left" in edges or "right" in edges:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif "top" in edges or "bottom" in edges:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        edges = self._edges_at(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and edges:
            self._resize_edges = edges
            self._resize_start_global = event.globalPosition().toPoint()
            self._resize_start_geometry = QRect(self.geometry())
            self.raise_()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_start_global is not None:
            delta = event.globalPosition().toPoint() - self._resize_start_global
            rect = QRect(self._resize_start_geometry)
            minimum_width = self.minimumWidth()
            minimum_height = self.minimumHeight()
            if "left" in self._resize_edges:
                new_left = min(rect.right() - minimum_width + 1, rect.left() + delta.x())
                rect.setLeft(new_left)
            if "right" in self._resize_edges:
                rect.setRight(max(rect.left() + minimum_width - 1, rect.right() + delta.x()))
            if "top" in self._resize_edges:
                new_top = min(rect.bottom() - minimum_height + 1, rect.top() + delta.y())
                rect.setTop(new_top)
            if "bottom" in self._resize_edges:
                rect.setBottom(max(rect.top() + minimum_height - 1, rect.bottom() + delta.y()))
            if not self._floating:
                if rect.left() < 0:
                    rect.moveLeft(0)
                if rect.top() < 0:
                    rect.moveTop(0)
            self.setGeometry(rect)
            self._grow_workspace_to_fit()
            event.accept()
            return
        self._set_resize_cursor(self._edges_at(event.position().toPoint()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_start_global is not None:
            resized_edges = set(self._resize_edges)
            self._resize_edges.clear()
            self._resize_start_global = None
            self._resize_start_geometry = None
            self.finish_geometry_change(resized_edges)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if self._resize_start_global is None:
            self.unsetCursor()
        super().leaveEvent(event)

    def adjust_font_size(self, delta):
        self.current_font_size = max(8, min(24, self.current_font_size + delta))
        self._apply_panel_style()
        if self._inner_widget and hasattr(self._inner_widget, "set_content_font_size"):
            self._inner_widget.set_content_font_size(self.current_font_size)
            if isinstance(self.widget(), CanvasScrollArea):
                self.widget().refresh_content_size()

    def adjust_icon_size(self, delta):
        self.current_icon_scale = max(0.5, min(3.0, self.current_icon_scale + (delta * 0.1)))
        if self._inner_widget and hasattr(self._inner_widget, "set_icon_scale"):
            self._inner_widget.set_icon_scale(self.current_icon_scale)
            if isinstance(self.widget(), CanvasScrollArea):
                self.widget().refresh_content_size()

    def isFloating(self):
        return self._floating

    def setFloating(self, floating: bool):
        floating = bool(floating)
        if floating == self._floating:
            return
        if floating:
            self.remember_docked_geometry()
            global_position = self._workspace.mapToGlobal(self.pos())
            self.hide()
            self.setParent(None)
            self.setWindowFlags(Qt.WindowType.Window)
            self._floating = True
            self.move(global_position)
            self.show()
        else:
            self.hide()
            self.setParent(self._workspace)
            self.setWindowFlags(Qt.WindowType.Widget)
            self._floating = False
            geometry = self._docked_geometry if self._docked_geometry.isValid() else QRect(0, 0, 300, 200)
            self.setGeometry(geometry)
            self.show()
            self.raise_()
            self._fit_workspace_to_panels()
        self.topLevelChanged.emit(self._floating)

    def _normalize_floating_window(self, is_floating: bool):
        if is_floating:
            QTimer.singleShot(0, self._clear_native_window_owner)

    def _clear_native_window_owner(self):
        if not self.isFloating():
            return
        try:
            import ctypes
            import sys
            if sys.platform != "win32":
                return
            set_owner = ctypes.windll.user32.SetWindowLongPtrW
            set_owner.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p)
            set_owner.restype = ctypes.c_void_p
            ctypes.set_last_error(0)
            previous_owner = set_owner(int(self.winId()), -8, 0)
            error = ctypes.get_last_error()
            if previous_owner == 0 and error:
                logging.warning(
                    "Could not clear floating-window owner | dock=%s | win32Error=%s",
                    self.objectName() or self.windowTitle(), error,
                )
        except Exception:
            logging.exception("Failed to normalize floating-window ownership")

    def closeEvent(self, event):
        if self._main_window and getattr(self._main_window, "_is_closing", False):
            event.accept()
            return
        if self.isFloating():
            self.setFloating(False)
            event.ignore()
            return
        event.accept()




