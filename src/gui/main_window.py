from PyQt6.QtWidgets import QMainWindow, QDockWidget, QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QMenu, QToolBar, QMessageBox, QFileDialog, QInputDialog, QGraphicsView, QGraphicsScene, QGraphicsProxyWidget
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QSettings
import logging

from core.state_manager import StateManager
from core.data_loader import DataLoader
from core.logic_engine import LogicEngine
from core.layout_manager import LayoutManager
from .map_widget import MapWidget
from .dock_title_bar import DockTitleBar
from .inventory_widgets import ToolsWidget, ScenarioWidget
from .menu_ribbon import MenuRibbon
from utils.constants import STATE_ORDER
from .widgets.items_widget import ItemsWidget
from .widgets.characters_widget import CharactersWidget
from .widgets.maiden_widget import MaidenWidget
from .widgets.hint_widget import HintWidget
from .dialogs.item_search_dialog import ItemSearchDialog
from PyQt6.QtWidgets import QMenu

class MainWindow(QMainWindow):
    def __init__(self, state_manager, data_loader, logic_engine):
        super().__init__()
        self.state_manager = state_manager
        self.data_loader = data_loader
        self.logic_engine = logic_engine
        self.layout_manager = LayoutManager()
        
        self.setWindowTitle("Lufia 2 Auto Tracker v1.4")
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

        self._active_search_dialogs = {}
        self._is_closing = False

        # Initial Refresh to apply Logic
        # Initial Refresh to apply Logic
        self._load_settings()
        self._refresh_all()

    def _setup_ui(self):
        """Initializes the main UI layout."""
        # For now, just a wrapper around the docking setup
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
        self.menu_ribbon.edit_layout_toggled.connect(self._set_edit_mode)
        self.menu_ribbon.restore_windows_requested.connect(self._restore_closed_windows)
        self.menu_ribbon.icon_adj_toggled.connect(self._toggle_icon_controls)
        self.menu_ribbon.locations_text_toggled.connect(self._toggle_locations_text)
        
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
        # Iterate over all dock widgets
        for dock in self.findChildren(PersistentDockWidget):
            dock.title_bar.set_font_controls_visible(visible)

    def _toggle_icon_controls(self, visible):
        for dock in self.findChildren(PersistentDockWidget):
            dock.title_bar.set_icon_controls_visible(visible)
            
    def _toggle_locations_text(self, visible):
        if hasattr(self, 'characters_widget'):
            self.characters_widget.canvas.set_locations_visible(visible)
        if hasattr(self, 'maiden_widget'):
            self.maiden_widget.set_locations_visible(visible)
            
    def _restore_closed_windows(self):
        for dock in self.findChildren(PersistentDockWidget):
            if dock.isHidden():
                dock.show()

    def _pick_header_color(self):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(initial=Qt.GlobalColor.darkGray, parent=self, title="Pick Header Color")
        if color.isValid():
            hex_color = color.name()
            self._header_color = hex_color # Store for persistence
            for dock in self.findChildren(PersistentDockWidget):
                dock.title_bar.set_header_color(hex_color)

    def _pick_player_color(self):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(initial=Qt.GlobalColor.magenta, parent=self, title="Pick Player Color")
        if color.isValid():
            hex_color = color.name()
            self._player_color = hex_color # Store for persistence
            self.map_widget.set_player_arrow_color(hex_color)

    def _set_edit_mode(self, enabled: bool):
        """Toggles 'Edit Layout' mode for draggable widgets."""
        self.tools_widget.set_edit_mode(enabled)
        self.scenario_widget.set_edit_mode(enabled)
        self.characters_widget.set_edit_mode(enabled)
        self.maiden_widget.set_edit_mode(enabled)
        
    def _handle_reset(self):
        self.state_manager.reset_state()

    def _handle_save(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save Tracker State", "", "JSON Files (*.json)")
        if path:
            try:
                self.state_manager.save_state(path)
            except Exception as e:
                logging.error(f"Save Failed: {e}")

    def _handle_load(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Load Tracker State", "", "JSON Files (*.json)")
        if path:
            try:
                self.state_manager.load_state(path)
                self._refresh_all()
            except Exception as e:
                logging.error(f"Load Failed: {e}")

    def _handle_auto_toggle(self, active: bool):
        """
        Auto: Full tracking.
        Active = Start Listening.
        Inactive = Stop Listening.
        """
        self.state_manager.toggle_auto_tracking(active)

    def _handle_sync_request(self, category):
        """
        Sync: Fetch snapshot.
        If Auto is OFF: Start Helper momentarily.
        If Auto is ON: Ping the helper to bypass diff-cache and send current payload immediately.
        """
        print(f"Sync Requested: {category}")
        if not self.state_manager.helper.running:
             self.state_manager.toggle_auto_tracking(True)
             self._is_syncing = True
        else:
             # Already running, just force a cache flush
             self.state_manager.force_sync()

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
        if hasattr(self, 'characters_widget'):
            self.characters_widget.canvas._reflow_grid()
        if hasattr(self, 'maiden_widget'):
            self.maiden_widget.update_positions()
        if hasattr(self, 'tools_widget'):
            self.tools_widget.grid.update_positions()
        if hasattr(self, 'scenario_widget'):
            self.scenario_widget.grid.update_positions()

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
        # If we were doing a one-shot sync, stop now.
        if getattr(self, '_is_syncing', False):
            self.state_manager.toggle_auto_tracking(False)
            self._is_syncing = False
            print("Sync Snapshot Complete")
        
        # Just refresh the UI to show new states
        self._refresh_all()
        # Ensure sprite image is up to date if reusing "sprite" mode
        self._update_player_sprite_if_active()

    def _setup_docking_ui(self):
        # Allow nested docks
        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AnimatedDocks)

        # --- Items Dock (Left, Top) ---
        self.items_dock = PersistentDockWidget("Items / Spells", self, scale_contents=False)
        self.items_dock.setObjectName("items_dock")
        self.items_widget = ItemsWidget(self.state_manager)
        self.items_dock.setWidget(self.items_widget)
        self.items_dock.setMinimumSize(100, 100)
        self.items_dock.setMaximumWidth(350) # Prevent taking too much horizontal space
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.items_dock)

        # --- Hints Dock (Left, Bottom) ---
        self.hints_dock = PersistentDockWidget("Hints", self, scale_contents=False)
        self.hints_dock.setObjectName("hints_dock")
        self.hint_widget = HintWidget()
        self.hints_dock.setWidget(self.hint_widget)
        self.hints_dock.setMinimumSize(100, 100)
        self.hints_dock.setMaximumWidth(350) # Prevent taking too much horizontal space
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.hints_dock)
        
        # --- Characters Dock (Top Right for T-Shape) ---
        self.chars_dock = PersistentDockWidget("Characters", self)
        self.chars_dock.setObjectName("chars_dock")
        self.characters_widget = CharactersWidget(self.data_loader, self.state_manager, self.layout_manager)
        self.chars_dock.setWidget(self.characters_widget)
        self.chars_dock.setMinimumSize(100, 150)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.chars_dock)
        
        # --- Tools Dock ---
        self.tools_dock = PersistentDockWidget("Tools", self, scale_contents=False)
        self.tools_dock.setObjectName("tools_dock")
        self.tools_widget = ToolsWidget(self.data_loader, self.layout_manager)
        self.tools_dock.setWidget(self.tools_widget)
        self.tools_dock.setMinimumSize(100, 60)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.tools_dock)

        # --- Maidens Dock ---
        self.maidens_dock = PersistentDockWidget("Maidens", self)
        self.maidens_dock.setObjectName("maidens_dock")
        self.maiden_widget = MaidenWidget(self.data_loader, self.state_manager, self.layout_manager)
        self.maidens_dock.setWidget(self.maiden_widget)
        self.maidens_dock.setMinimumSize(100, 60)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.maidens_dock)
        
        # --- Keys Dock ---
        self.scenario_dock = PersistentDockWidget("Keys", self, scale_contents=False)
        self.scenario_dock.setObjectName("scenario_dock")
        self.scenario_widget = ScenarioWidget(self.data_loader, self.layout_manager)
        self.scenario_dock.setWidget(self.scenario_widget)
        self.scenario_dock.setMinimumSize(100, 80)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.scenario_dock)
        
        # --- Map Dock (Far Right) ---
        self.map_dock = PersistentDockWidget("World Map", self, scale_contents=False)
        self.map_dock.setObjectName("map_dock")
        self.map_widget = MapWidget(self.data_loader)
        self.map_dock.setWidget(self.map_widget)
        self.map_dock.setMinimumSize(200, 200)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.map_dock)
        
        # --- Layout Construction (T-Shape) ---
        
        # 1. Left Area: Items / Hints
        self.splitDockWidget(self.items_dock, self.hints_dock, Qt.Orientation.Vertical)
        
        # 2. Right Area T-Shape:
        # Chars occupies the Top sector.
        # Tools/Maidens/Keys occupies Bottom-Left.
        # Map occupies Bottom-Right.
        
        # Split Chars (which is on Right) with Tools (Vertical) -> Chars on Top, Tools on Bottom.
        self.splitDockWidget(self.chars_dock, self.tools_dock, Qt.Orientation.Vertical)
        
        # Split Tools with Map (Horizontal) -> Tools Left, Map Right.
        self.splitDockWidget(self.tools_dock, self.map_dock, Qt.Orientation.Horizontal)
        
        # Stack Maidens and Keys under Tools (Vertical split of Tools)
        self.splitDockWidget(self.tools_dock, self.maidens_dock, Qt.Orientation.Vertical)
        self.splitDockWidget(self.maidens_dock, self.scenario_dock, Qt.Orientation.Vertical)
        
        # --- Resizing ---
        # 1. Bottom Section Horizontal Split (Tools etc vs Map)
        self.resizeDocks(
            [self.tools_dock, self.map_dock],
            [200, 500], # Prefer Map wider
            Qt.Orientation.Horizontal
        )
        
        # 2. Right Side Vertical Split (Chars vs Bottom Section)
        self.resizeDocks(
            [self.chars_dock, self.tools_dock], 
            [250, 450],
            Qt.Orientation.Vertical
        )
        
        # --- Fluidity Policies ---
        from PyQt6.QtWidgets import QSizePolicy
        for dock in [self.items_dock, self.hints_dock, self.chars_dock, self.tools_dock, 
                     self.maidens_dock, self.scenario_dock, self.map_dock]:
             policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
             policy.setVerticalStretch(1)
             policy.setHorizontalStretch(1)
             dock.setSizePolicy(policy)

        # Map Stretch
        self.map_dock.sizePolicy().setHorizontalStretch(3)
        # Chars shrinking logic
        self.characters_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)


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
        """User clicked a dot: Cycle the state (Manual Override)."""
        current_state = self.state_manager.locations.get(name)
        
        cycle_order = list(STATE_ORDER)
        if name in self.data_loader.get_cities():
             cycle_order = ["city"]
        else:
             cycle_order = ["not_accessible", "fully_accessible", "cleared"]

        if not current_state or current_state not in cycle_order:
             new_state = cycle_order[0]
        else:
             idx = cycle_order.index(current_state)
             new_state = cycle_order[(idx + 1) % len(cycle_order)]
                
        self.state_manager.set_manual_location_state(name, new_state)

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
        settings = QSettings("Lufia2Tracker", "MainWindow")
        try:
             settings.setValue("geometry", self.saveGeometry())
             settings.setValue("windowState", self.saveState())
             
             # Save Persistence preferences
             settings.setValue("headerColor", getattr(self, "_header_color", ""))
             settings.setValue("playerColor", getattr(self, "_player_color", ""))
             settings.setValue("playerShape", getattr(self.map_widget, "_player_shape", "triangle"))
             settings.setValue("playerScale", getattr(self.map_widget, "_player_scale", 1.0))

        except Exception as e:
             logging.error(f"Failed to save settings: {e}")
        
        # Shutdown logic
        if hasattr(self, 'auto_tracker_thread') and self.auto_tracker_thread and self.auto_tracker_thread.isRunning():
            self.auto_tracker_thread.stop()
            self.auto_tracker_thread.wait()
            
        # Force close all docks (Floating docks become top-level windows and might persist)
        self._is_closing = True
        for dock in self.findChildren(QDockWidget):
            dock.close()
            
        super().closeEvent(event)

    def _load_settings(self):
        settings = QSettings("Lufia2Tracker", "MainWindow")
        geometry = settings.value("geometry")
        state = settings.value("windowState")
        
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)
            
        # Restore Preferences
        h_color = settings.value("headerColor")
        if h_color:
            self._header_color = h_color
            for dock in self.findChildren(PersistentDockWidget):
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


class ScalableView(QGraphicsView):
    def __init__(self, widget):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Transparent background so it blends nicely
        self.setStyleSheet("background: transparent;")
        
        self.proxy = self.scene.addWidget(widget)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Initial fit: force layout to resolve first
        # Initial fit: force layout to resolve first
        widget.resize(widget.sizeHint())
        self.scene.setSceneRect(self.proxy.boundingRect())

    def update_scale(self):
        self.scene.setSceneRect(self.proxy.boundingRect())
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        transform = self.transform()
        if transform.m11() > 1.0 or transform.m22() > 1.0:
            self.resetTransform()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_scale()

class PersistentDockWidget(QDockWidget):
    """
    A DockWidget that doesn't delete itself on close, 
    but instead un-floats (docks back) or hides.
    User requested: 'on close reintegrate into main window'.
    """
    def __init__(self, title, parent=None, scale_contents=True):
        super().__init__(title, parent)
        self.scale_contents = scale_contents
        self._inner_widget = None
        # Set custom title bar for "Pin" functionality
        self.title_bar = DockTitleBar(title, self)
        self.setTitleBarWidget(self.title_bar)
        
        self.current_font_size = 11 # Default
        self.current_icon_scale = 1.0 # Default
        
        # Border Style (Global for the dock)
        self.setStyleSheet(f"""
            QDockWidget {{
                border: 1px solid #444; 
                titlebar-close-icon: url(none);
                titlebar-normal-icon: url(none);
            }}
            QWidget {{ font-size: {self.current_font_size}px; }}
        """)

    def setWidget(self, widget):
        if not widget:
            super().setWidget(None)
            self._inner_widget = None
            return
            
        self._inner_widget = widget
        if self.scale_contents:
            view = ScalableView(widget)
            super().setWidget(view)
        else:
            super().setWidget(widget)

    def adjust_font_size(self, delta):
        self.current_font_size += delta
        if self.current_font_size < 8: self.current_font_size = 8
        if self.current_font_size > 24: self.current_font_size = 24
        
        # Apply to children via stylesheet (generic fallback)
        self.setStyleSheet(f"""
            QDockWidget {{
                border: 1px solid #444;
            }}
            QWidget {{ font-size: {self.current_font_size}px; }}
        """)
        
        # Try specific update method for known widgets
        widget = self._inner_widget
        if widget and hasattr(widget, "set_content_font_size"):
             widget.set_content_font_size(self.current_font_size)
             # Rescale the graphics view bounding rect if layout changed slightly
             if isinstance(self.widget(), ScalableView):
                 self.widget().update_scale()

    def adjust_icon_size(self, delta):
        self.current_icon_scale += (delta * 0.1)
        if self.current_icon_scale < 0.5: self.current_icon_scale = 0.5
        if self.current_icon_scale > 3.0: self.current_icon_scale = 3.0
        
        widget = self._inner_widget
        if widget and hasattr(widget, "set_icon_scale"):
             widget.set_icon_scale(self.current_icon_scale)
             if isinstance(self.widget(), ScalableView):
                 self.widget().update_scale()

    def closeEvent(self, event):
        # Allow global app termination to close floating docks
        if self.parent() and getattr(self.parent(), '_is_closing', False):
             super().closeEvent(event)
             return
             
        if self.isFloating():
            # If floating, 'restore' it to the dock area instead of hiding
            self.setFloating(False)
            event.ignore() # Prevent the default close (hide) event/deletion
        else:
            # If already docked and user clicks X, standard behavior is Hide.
            # We can allow hide, or ignore if we want them 'undeletable'. 
            # Let's allow hide so they can clear clutter, but they can re-open via View menu (TODO).
            super().closeEvent(event)




