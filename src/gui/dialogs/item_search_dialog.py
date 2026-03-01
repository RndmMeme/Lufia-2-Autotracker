from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
    QListWidget, QListWidgetItem, QWidget, QLabel, QComboBox, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

class ItemSearchDialog(QDialog):
    """
    Dialog for searching and adding items/spells to a specific location.
    Non-modal: Stays open until closed.
    """
    item_added = pyqtSignal(str, str) # location, item_name
    duplicate_found = pyqtSignal(str, str) # location, item_name (for highlighting)
    location_changed = pyqtSignal(str)

    def __init__(self, location, data_loader, parent=None):
        super().__init__(parent)
        self.location = location
        self.data_loader = data_loader
        self.item_spells = data_loader.get_items_spells()
        self.all_categories = list(self.item_spells.keys())
        self.current_category = self.all_categories[0] if self.all_categories else ""
        
        self.setWindowTitle(f"Search {location}")
        self.setWindowIcon(QIcon("Lufia_2_Auto_Tracker.ico"))
        self.resize(400, 500) # Increased size
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        self.init_ui()
        self.load_list()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Location Selector (City Picker)
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel("Searching:"))
        
        self.loc_combo = QComboBox()
        # Populate with cities (requires access to DataLoader or just pass list)
        cities = self.data_loader.get_cities()
        excluded_locations = {"Agurio", "Pico Woods", "Gordovan"}
        filtered_cities = [c for c in cities if c not in excluded_locations]
        
        self.loc_combo.addItems(sorted(filtered_cities))
        
        self.loc_combo.setEditable(True)
        completer = QCompleter(sorted(filtered_cities))
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.loc_combo.setCompleter(completer)
        
        # Set current selection
        index = self.loc_combo.findText(self.location)
        if index >= 0:
            self.loc_combo.setCurrentIndex(index)
            
        self.loc_combo.currentTextChanged.connect(self._on_location_changed)
        location_layout.addWidget(self.loc_combo)
        
        layout.addLayout(location_layout)
        
        # Categories
        cat_layout = QHBoxLayout()
        self.cat_buttons = []
        for cat in self.all_categories:
            label = cat
            if cat == "is Treasure":
                label = "Iris Items"
            
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=cat: self.change_category(c))
            cat_layout.addWidget(btn)
            self.cat_buttons.append(btn)
        layout.addLayout(cat_layout)
        
        self.update_cat_buttons()
        
        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.filter_list)
        self.search_bar.returnPressed.connect(self.add_selected)
        layout.addWidget(self.search_bar)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.add_selected)
        layout.addWidget(self.list_widget)
        
        # Auto-focus input
        self.search_bar.setFocus()

    def update_cat_buttons(self):
        for btn in self.cat_buttons:
            btn.setEnabled(True)
            if btn.text() == self.current_category:
                btn.setChecked(True)
                btn.setStyleSheet("background-color: #555; color: white;")
            else:
                btn.setChecked(False)
                btn.setStyleSheet("")

    def change_category(self, category):
        self.current_category = category
        self.update_cat_buttons()
        self.load_list()

    def load_list(self):
        self.list_widget.clear()
        query = self.search_bar.text().lower()
        
        items = self.item_spells.get(self.current_category, {})
        
        # Flatten dict {id: name} to list of names
        source_list = []
        if isinstance(items, dict):
            source_list = list(items.values())
        elif isinstance(items, list):
            source_list = items
        
        # Filter and sort
        filtered_items = []
        for item_name in source_list:
            # Handle potential dicts if data structure changes
            if isinstance(item_name, dict):
                item_name = item_name.get('name', '')
            
            if query in str(item_name).lower():
                filtered_items.append(str(item_name))
                
        filtered_items.sort()
        
        for name in filtered_items:
            self.list_widget.addItem(name)
        
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def filter_list(self):
        self.load_list()

    def add_selected(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            name = item.text()
            self.item_added.emit(self.location, name)
            
        # Select next item for rapid entry
        nrow = self.list_widget.currentRow()
        if nrow < self.list_widget.count() - 1:
            self.list_widget.setCurrentRow(nrow + 1)

    def _on_location_changed(self, new_location):
        if new_location not in [self.loc_combo.itemText(i) for i in range(self.loc_combo.count())]:
            return # Ignore intermediate typing
        self.location = new_location
        self.setWindowTitle(f"Search {self.location}")
            
        self.update_cat_buttons()
        self.load_list()
        self.location_changed.emit(self.location)
