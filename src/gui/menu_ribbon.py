from PyQt6.QtWidgets import QMenuBar, QMenu, QWidget, QHBoxLayout, QCheckBox, QLabel, QFrame
from PyQt6.QtGui import QAction
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
    
    restore_windows_requested = pyqtSignal()
    dock_all_requested = pyqtSignal()
    icon_adj_toggled = pyqtSignal(bool)
    locations_text_toggled = pyqtSignal(bool)
    
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
        
        self.edit_layout_action = QAction("Edit Layout", self)
        self.edit_layout_action.setCheckable(True)
        self.edit_layout_action.toggled.connect(self.edit_layout_toggled.emit)
        layout_menu.addAction(self.edit_layout_action)
        
        layout_menu.addAction("Reset Picture Positions", self.reset_pictures_requested.emit)
        layout_menu.addAction("Restore Closed Windows", self.restore_windows_requested.emit)
        layout_menu.addAction("Dock All Windows", self.dock_all_requested.emit)

        # --- View (Middle) ---
        view_menu = self.menu_bar.addMenu("View")
        
        self.font_adj_action = QAction("Show Font Controls", self)
        self.font_adj_action.setCheckable(True)
        self.font_adj_action.toggled.connect(self.font_adj_toggled.emit)
        view_menu.addAction(self.font_adj_action)
        
        self.icon_adj_action = QAction("Show Icon Size Controls", self)
        self.icon_adj_action.setCheckable(True)
        self.icon_adj_action.toggled.connect(self.icon_adj_toggled.emit)
        view_menu.addAction(self.icon_adj_action)
        
        self.loc_text_action = QAction("Show Locations Text", self)
        self.loc_text_action.setCheckable(True)
        self.loc_text_action.setChecked(True)
        self.loc_text_action.toggled.connect(self.locations_text_toggled.emit)
        view_menu.addAction(self.loc_text_action)
        
        view_menu.addSeparator()
        
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
        
        style_menu.addAction("Header Color", self.header_color_requested.emit)
        style_menu.addSeparator()
        
        style_menu.addAction("Player Color", self.player_color_requested.emit)
        shape_menu = QMenu("Player Shape", self)
        shape_menu.addAction("Triangle", lambda: self.player_shape_requested.emit("triangle"))
        shape_menu.addAction("Rhombus", lambda: self.player_shape_requested.emit("rhombus"))
        shape_menu.addAction("Square", lambda: self.player_shape_requested.emit("square"))
        shape_menu.addAction("Active Sprite", lambda: self.player_shape_requested.emit("sprite"))
        style_menu.addMenu(shape_menu)
        
        size_menu = QMenu("Player Size", self)
        size_menu.addAction("Normal (1x)", lambda: self.player_size_requested.emit(1.0))
        size_menu.addAction("2x", lambda: self.player_size_requested.emit(2.0))
        size_menu.addAction("3x", lambda: self.player_size_requested.emit(3.0))
        size_menu.addAction("4x", lambda: self.player_size_requested.emit(4.0))
        style_menu.addMenu(size_menu)
        
        style_menu.addSeparator()
        
        style_menu.addAction("City Color", self.city_color_requested.emit)
        city_shape_menu = QMenu("City Shape", self)
        city_shape_menu.addAction("Circle", lambda: self.city_shape_requested.emit("circle"))
        city_shape_menu.addAction("Square", lambda: self.city_shape_requested.emit("square"))
        city_shape_menu.addAction("Rhombus", lambda: self.city_shape_requested.emit("rhombus"))
        city_shape_menu.addAction("Triangle", lambda: self.city_shape_requested.emit("triangle"))
        style_menu.addMenu(city_shape_menu)
        
        dungeon_shape_menu = QMenu("Dungeon Shape", self)
        dungeon_shape_menu.addAction("Circle", lambda: self.dungeon_shape_requested.emit("circle"))
        dungeon_shape_menu.addAction("Square", lambda: self.dungeon_shape_requested.emit("square"))
        dungeon_shape_menu.addAction("Rhombus", lambda: self.dungeon_shape_requested.emit("rhombus"))
        dungeon_shape_menu.addAction("Triangle", lambda: self.dungeon_shape_requested.emit("triangle"))
        style_menu.addMenu(dungeon_shape_menu)
        
        # --- Help / About (Right of Custom) ---
        about_action = self.menu_bar.addAction("About")
        about_action.triggered.connect(self._show_about)
        
        help_action = self.menu_bar.addAction("Help") 
        help_action.triggered.connect(self._show_help)
        
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

