from PyQt6.QtWidgets import QMenuBar, QMenu, QWidget, QHBoxLayout, QCheckBox, QLabel, QFrame
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import pyqtSignal, Qt
from .help_dialogs import HelpDialog, AboutDialog

class MenuRibbon(QWidget):
    """
    Replicates the v1.3 Menu Ribbon.
    Wraps a QMenuBar and a Custom Panel in a QHBoxLayout to control positioning.
    """
    # Signals
    reset_requested = pyqtSignal()
    save_requested = pyqtSignal()
    load_requested = pyqtSignal()
    
    sync_requested = pyqtSignal(str) # "all", "tools", "keys", etc.
    auto_toggled = pyqtSignal(bool) # True=Show Checkboxes/Start, False=Hide/Stop
    player_color_requested = pyqtSignal()
    player_shape_requested = pyqtSignal(str)
    player_size_requested = pyqtSignal(float) # New Signal
    
    # New Signals for City/Location Styling & Reset
    city_color_requested = pyqtSignal()
    city_shape_requested = pyqtSignal(str)
    dungeon_shape_requested = pyqtSignal(str)
    reset_pictures_requested = pyqtSignal()
    save_layout_default_requested = pyqtSignal()
    
    sprite_visibility_toggled = pyqtSignal(str, bool) # category, visible
    font_adj_toggled = pyqtSignal(bool)
    header_color_requested = pyqtSignal()
    
    # Edit Layout Signal
    edit_layout_toggled = pyqtSignal(bool)
    grid_visibility_toggled = pyqtSignal(bool)
    grid_snap_toggled = pyqtSignal(bool)
    grid_size_changed = pyqtSignal(int)
    canvas_grid_visibility_toggled = pyqtSignal(bool)
    canvas_grid_snap_toggled = pyqtSignal(bool)
    canvas_grid_size_changed = pyqtSignal(int)
    auto_align_requested = pyqtSignal(str)
    open_log_folder_requested = pyqtSignal()
    
    restore_windows_requested = pyqtSignal()
    dock_all_requested = pyqtSignal()
    reset_window_layout_requested = pyqtSignal()
    icon_adj_toggled = pyqtSignal(bool)
    locations_text_toggled = pyqtSignal(bool)
    active_party_visibility_toggled = pyqtSignal(bool)
    
    # Checkbox signals (state changes)
    auto_options_changed = pyqtSignal(dict) # {chars: bool, tools: bool...}

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ... (Init Layout) ...
        # Main Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # --- Internal Menu Bar ---
        self.menu_bar = QMenuBar()
        self.menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #2b2b2b;
                color: #ffffff;
                border: none;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 10px;
                margin: 2px;
            }
            QMenuBar::item:selected {
                background-color: #3d3d3d;
            }
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)
        # We need to ensure the menu bar doesn't expand infinitely if we want stuff next to it.
        self.menu_bar.setSizePolicy(self.menu_bar.sizePolicy().horizontalPolicy(), self.menu_bar.sizePolicy().verticalPolicy())
        layout.addWidget(self.menu_bar)

        # ... (Options and Tracker Menus - Unchanged) ...
        # --- Options (Left) ---
        options_menu = self.menu_bar.addMenu("Options")
        options_menu.addAction("Reset", self.reset_requested.emit)
        options_menu.addAction("Save", self.save_requested.emit)
        options_menu.addAction("Load", self.load_requested.emit)
        
        # --- Tracker (Left) ---
        tracker_menu = self.menu_bar.addMenu("Tracker")
        
        # Sync Submenu
        sync_menu = QMenu("Sync", self)
        sync_menu.addAction("All", lambda: self.sync_requested.emit("all"))
        sync_menu.addSeparator()
        sync_menu.addAction("Tools", lambda: self.sync_requested.emit("tools"))
        sync_menu.addAction("Keys", lambda: self.sync_requested.emit("keys"))
        sync_menu.addAction("Chars", lambda: self.sync_requested.emit("chars"))
        sync_menu.addAction("Maiden", lambda: self.sync_requested.emit("maidens"))
        sync_menu.addAction("Pos", lambda: self.sync_requested.emit("pos"))
        tracker_menu.addMenu(sync_menu)
        
        # Auto Action
        self.auto_active = False
        self.auto_menu = QMenu("Auto", self)
        
        self.auto_tracking_action = QAction("Enable Auto Tracking", self)
        self.auto_tracking_action.setCheckable(True)
        self.auto_tracking_action.toggled.connect(self._toggle_auto)
        self.auto_menu.addAction(self.auto_tracking_action)
        self.auto_menu.addSeparator()
        
        self.checkboxes = {}
        for key in ["All", "Chars", "Tools", "Keys", "Maidens", "Pos"]:
            action = QAction(key, self)
            action.setCheckable(True)
            action.setChecked(False)
            action.toggled.connect(self._on_checkbox_change)
            self.checkboxes[key] = action
            self.auto_menu.addAction(action)
            if key == "All":
                action.toggled.connect(self._on_all_toggled)

        tracker_menu.addMenu(self.auto_menu)

        # --- Layout (Middle) ---
        layout_menu = self.menu_bar.addMenu("Layout")
        icon_placement_menu = QMenu("Icon Placement", self)

        self.edit_layout_action = QAction("Edit Icon Positions", self)
        self.edit_layout_action.setCheckable(True)
        self.edit_layout_action.toggled.connect(self.edit_layout_toggled.emit)
        icon_placement_menu.addAction(self.edit_layout_action)

        self.show_grid_action = QAction("Show Picture Placement Grid", self)
        self.show_grid_action.setCheckable(True)
        self.show_grid_action.toggled.connect(self.grid_visibility_toggled.emit)
        icon_placement_menu.addAction(self.show_grid_action)

        self.snap_grid_action = QAction("Snap Pictures to Grid", self)
        self.snap_grid_action.setCheckable(True)
        self.snap_grid_action.toggled.connect(self.grid_snap_toggled.emit)
        icon_placement_menu.addAction(self.snap_grid_action)

        grid_size_menu = QMenu("Picture Grid Size", self)
        self.grid_size_group = QActionGroup(self)
        self.grid_size_group.setExclusive(True)
        for size in (5, 10, 20, 25):
            action = QAction(f"{size} px", self)
            action.setCheckable(True)
            action.setChecked(size == 10)
            action.toggled.connect(
                lambda checked, value=size: self.grid_size_changed.emit(value) if checked else None
            )
            self.grid_size_group.addAction(action)
            grid_size_menu.addAction(action)
        icon_placement_menu.addMenu(grid_size_menu)

        panel_arrangement_menu = QMenu("Panel Arrangement", self)
        canvas_grid_menu = QMenu("Canvas Grid", self)
        self.show_canvas_grid_action = QAction("Show Canvas Grid", self)
        self.show_canvas_grid_action.setCheckable(True)
        self.show_canvas_grid_action.toggled.connect(self.canvas_grid_visibility_toggled.emit)
        canvas_grid_menu.addAction(self.show_canvas_grid_action)

        self.snap_canvas_grid_action = QAction("Snap Panels to Canvas Grid", self)
        self.snap_canvas_grid_action.setCheckable(True)
        self.snap_canvas_grid_action.toggled.connect(self.canvas_grid_snap_toggled.emit)
        canvas_grid_menu.addAction(self.snap_canvas_grid_action)

        canvas_size_menu = QMenu("Canvas Grid Size", self)
        self.canvas_grid_size_group = QActionGroup(self)
        self.canvas_grid_size_group.setExclusive(True)
        for size in (5, 10, 20, 25):
            action = QAction(f"{size} px", self)
            action.setCheckable(True)
            action.setChecked(size == 10)
            action.toggled.connect(
                lambda checked, value=size: self.canvas_grid_size_changed.emit(value) if checked else None
            )
            self.canvas_grid_size_group.addAction(action)
            canvas_size_menu.addAction(action)
        canvas_grid_menu.addMenu(canvas_size_menu)
        panel_arrangement_menu.addMenu(canvas_grid_menu)

        align_menu = QMenu("Auto-align", self)
        for label, canvas_id in (
            ("All Canvases", "all"),
            ("Tools", "tools"),
            ("Keys", "keys"),
            ("Characters", "characters"),
            ("Maidens", "maidens"),
        ):
            align_menu.addAction(label, lambda checked=False, value=canvas_id: self.auto_align_requested.emit(value))
        icon_placement_menu.addMenu(align_menu)
        icon_placement_menu.addSeparator()
        icon_placement_menu.addAction("Save Icon Positions as Default", self.save_layout_default_requested.emit)
        icon_placement_menu.addAction("Reset Icon Positions", self.reset_pictures_requested.emit)
        layout_menu.addMenu(icon_placement_menu)

        panel_arrangement_menu.addSeparator()
        panel_arrangement_menu.addAction("Restore Closed Panels", self.restore_windows_requested.emit)
        panel_arrangement_menu.addAction("Snap Back Detached Panels", self.dock_all_requested.emit)
        panel_arrangement_menu.addAction("Reset Panel Arrangement", self.reset_window_layout_requested.emit)
        layout_menu.addMenu(panel_arrangement_menu)

        # --- View (Middle) ---
        view_menu = self.menu_bar.addMenu("View")
        panel_controls_menu = QMenu("Panel Controls", self)
        self.font_adj_action = QAction("Show Font Controls", self)
        self.font_adj_action.setCheckable(True)
        self.font_adj_action.toggled.connect(self.font_adj_toggled.emit)
        panel_controls_menu.addAction(self.font_adj_action)
        
        self.icon_adj_action = QAction("Show Icon Size Controls", self)
        self.icon_adj_action.setCheckable(True)
        self.icon_adj_action.toggled.connect(self.icon_adj_toggled.emit)
        panel_controls_menu.addAction(self.icon_adj_action)
        view_menu.addMenu(panel_controls_menu)

        character_display_menu = QMenu("Character Display", self)
        self.loc_text_action = QAction("Show Location Notes", self)
        self.loc_text_action.setCheckable(True)
        self.loc_text_action.setChecked(True)
        self.loc_text_action.toggled.connect(self.locations_text_toggled.emit)
        character_display_menu.addAction(self.loc_text_action)

        self.active_party_action = QAction("Show Active Party Members", self)
        self.active_party_action.setCheckable(True)
        self.active_party_action.setChecked(True)
        self.active_party_action.toggled.connect(self.active_party_visibility_toggled.emit)
        character_display_menu.addAction(self.active_party_action)
        view_menu.addMenu(character_display_menu)
        
        sprite_menu = QMenu("Map Sprites", self)
        self.sprite_actions = {}
        for cat in ["All", "Chars", "Capsules", "Maidens"]:
            action = QAction(cat, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(lambda checked, c=cat.lower(): self.sprite_visibility_toggled.emit(c, checked))
            if cat == "All":
                 action.toggled.connect(self._on_all_sprites_toggled)
            self.sprite_actions[cat] = action
            sprite_menu.addAction(action)
            
        view_menu.addMenu(sprite_menu)
        
        # --- Style (Middle) ---
        style_menu = self.menu_bar.addMenu("Style")

        panel_appearance_menu = QMenu("Panel Appearance", self)
        panel_appearance_menu.addAction("Header Color", self.header_color_requested.emit)
        style_menu.addMenu(panel_appearance_menu)

        player_marker_menu = QMenu("Player Marker", self)
        player_marker_menu.addAction("Color", self.player_color_requested.emit)
        shape_menu = QMenu("Shape", self)
        shape_menu.addAction("Triangle", lambda: self.player_shape_requested.emit("triangle"))
        shape_menu.addAction("Rhombus", lambda: self.player_shape_requested.emit("rhombus"))
        shape_menu.addAction("Square", lambda: self.player_shape_requested.emit("square"))
        shape_menu.addAction("Active Sprite", lambda: self.player_shape_requested.emit("sprite"))
        player_marker_menu.addMenu(shape_menu)
        
        size_menu = QMenu("Size", self)
        size_menu.addAction("Normal (1x)", lambda: self.player_size_requested.emit(1.0))
        size_menu.addAction("2x", lambda: self.player_size_requested.emit(2.0))
        size_menu.addAction("3x", lambda: self.player_size_requested.emit(3.0))
        size_menu.addAction("4x", lambda: self.player_size_requested.emit(4.0))
        player_marker_menu.addMenu(size_menu)
        style_menu.addMenu(player_marker_menu)

        map_locations_menu = QMenu("Map Locations", self)
        map_locations_menu.addAction("City Color", self.city_color_requested.emit)
        city_shape_menu = QMenu("City Shape", self)
        city_shape_menu.addAction("Circle", lambda: self.city_shape_requested.emit("circle"))
        city_shape_menu.addAction("Square", lambda: self.city_shape_requested.emit("square"))
        city_shape_menu.addAction("Rhombus", lambda: self.city_shape_requested.emit("rhombus"))
        city_shape_menu.addAction("Triangle", lambda: self.city_shape_requested.emit("triangle"))
        map_locations_menu.addMenu(city_shape_menu)
        
        dungeon_shape_menu = QMenu("Dungeon Shape", self)
        dungeon_shape_menu.addAction("Circle", lambda: self.dungeon_shape_requested.emit("circle"))
        dungeon_shape_menu.addAction("Square", lambda: self.dungeon_shape_requested.emit("square"))
        dungeon_shape_menu.addAction("Rhombus", lambda: self.dungeon_shape_requested.emit("rhombus"))
        dungeon_shape_menu.addAction("Triangle", lambda: self.dungeon_shape_requested.emit("triangle"))
        map_locations_menu.addMenu(dungeon_shape_menu)
        style_menu.addMenu(map_locations_menu)
        
        # --- Help / About ---
        help_menu = self.menu_bar.addMenu("Help")
        help_menu.addAction("User Guide", self._show_help)
        help_menu.addAction("Open Log Folder", self.open_log_folder_requested.emit)
        help_menu.addSeparator()
        help_menu.addAction("About", self._show_about)
        
        # --- Auto Checkboxes Panel ---
        self.checkbox_frame = QWidget()
        self.cb_layout = QHBoxLayout()
        self.cb_layout.setContentsMargins(10, 0, 0, 0)
        self.cb_layout.setSpacing(10)
        self.checkbox_frame.setLayout(self.cb_layout)
        
        self.lbl_auto = QLabel("Auto Tracking (Active)")
        self.lbl_auto.setStyleSheet("color: lightgreen; font-weight: bold;")
        self.cb_layout.addWidget(self.lbl_auto)
        
        self.lbl_scanning = QLabel("Scanning in progress...")
        self.lbl_scanning.setStyleSheet("color: yellow; font-weight: bold;")
        self.lbl_scanning.hide()
        self.cb_layout.addWidget(self.lbl_scanning)

        self.checkbox_frame.hide() 
        layout.addWidget(self.checkbox_frame)
        layout.addStretch()
        
        # Overall Styling
        self.setStyleSheet("background-color: #2b2b2b;")

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()
        
    def _show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def set_scanning_status(self, is_scanning: bool):
        if is_scanning:
            self.lbl_auto.hide()
            self.lbl_scanning.show()
            self.checkbox_frame.show()
        else:
            self.lbl_scanning.hide()
            if self.auto_active:
                self.lbl_auto.show()
                self.checkbox_frame.show()
            else:
                self.checkbox_frame.hide()

    def set_tracker_status(self, state: str, message: str):
        if state == "attached":
            self.lbl_auto.setText(message)
            self.lbl_auto.setStyleSheet("color: lightgreen; font-weight: bold;")
            self.set_scanning_status(False)
            return

        color = "#ff6b6b" if state in {"error", "lost"} else "yellow"
        self.lbl_scanning.setText(message)
        self.lbl_scanning.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.set_scanning_status(True)

    def _toggle_auto(self, checked=None):
        if checked is not None:
            self.auto_active = checked
        else:
            self.auto_active = not self.auto_active
            self.auto_tracking_action.setChecked(self.auto_active)
            
        self.auto_toggled.emit(self.auto_active)
        
        if self.auto_active:
            self.auto_menu.setTitle("Auto (Active)")
            self.checkbox_frame.show()
            if not self.checkboxes["All"].isChecked():
                 self.checkboxes["All"].setChecked(True)
        else:
            self.auto_menu.setTitle("Auto")
            self.checkbox_frame.hide()

    def _on_all_toggled(self, checked):
        # Toggle all others
        for k, cb in self.checkboxes.items():
            if k != "All":
                cb.setChecked(checked)

    def _on_all_sprites_toggled(self, checked):
        for k, action in self.sprite_actions.items():
            if k != "All":
                action.setChecked(checked)

    def _on_checkbox_change(self):
        # Gather state
        state = {k.lower(): cb.isChecked() for k, cb in self.checkboxes.items()}
        self.auto_options_changed.emit(state)

