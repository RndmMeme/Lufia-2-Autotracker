from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap

class DraggableLabel(QLabel):
    clicked_signal = pyqtSignal()
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(50, 50)
        self.setScaledContents(True)

    def mousePressEvent(self, event):
        if self.parent() and getattr(self.parent(), 'edit_mode', False):
            event.ignore()
        elif event.button() == Qt.MouseButton.LeftButton:
            self.clicked_signal.emit()

class MaidenCell(QWidget):
    clicked = pyqtSignal(str)
    position_changed = pyqtSignal(str, int, int)
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedWidth(80) 
        self.setMinimumHeight(100) 
        self.edit_mode = False
        self._drag_start_pos = None

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(1)
        self.setLayout(self.layout)
        
        # Icon
        self.icon_label = DraggableLabel(name, self)
        self.icon_label.clicked_signal.connect(lambda: self.clicked.emit(self.name))
        self.layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        
        # Name (We omit name block for maidens, they just want location text like in characters if obtained?)
        # Wait, user requested: "Also place names at the Maidens the same way we added names to characters."
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("font-size: 11px; font-weight: bold; color: white;")
        self.layout.addWidget(self.name_label, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        
        # Location (Found At)
        self.loc_label = QLabel("")
        self.loc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loc_label.setWordWrap(True)
        self.loc_label.setStyleSheet("font-size: 9px; color: #AAAAAA;")
        self.layout.addWidget(self.loc_label, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.loc_label.hide()
        
        self.layout.addStretch()
        self.setToolTip(name)

    def set_edit_mode(self, enabled):
        self.edit_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if self.edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.edit_mode and self._drag_start_pos:
            curr_pos = self.mapToParent(event.pos())
            start_pos_in_parent = self.mapToParent(self._drag_start_pos)
            diff = curr_pos - start_pos_in_parent
            self.move(self.pos() + diff)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.edit_mode:
            self._drag_start_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.position_changed.emit(self.name, self.x(), self.y())
        else:
            super().mouseReleaseEvent(event)
            
    def set_font_size(self, size):
        self.name_label.setStyleSheet(f"font-size: {size}px; font-weight: bold; color: white;")
        self.loc_label.setStyleSheet(f"font-size: {max(8, size-2)}px; color: #AAAAAA;")
        
    def set_icon_scale(self, scale):
        size = int(50 * scale)
        self.icon_label.setFixedSize(size, size)
        self.setFixedWidth(max(80, size + 20))
        
    def set_pixmap(self, pixmap):
        self.icon_label.setPixmap(pixmap)
        
    def set_location_text(self, text):
        if text:
            words = text.split()
            lines = []
            for word in words:
                if len(word) > 9: 
                    mid = len(word) // 2
                    lines.append(word[:mid] + "-")
                    lines.append(word[mid:])
                else:
                    lines.append(word)
            
            final_text = "\n".join(lines)
            self.loc_label.setText(final_text)
            self.loc_label.show()
        else:
            self.loc_label.hide()


class MaidenWidget(QWidget):
    """
    Displays the 3 Maidens (Claire, Lisa, Marie).
    """
    def __init__(self, data_loader, state_manager, layout_manager, parent=None):
        super().__init__(parent)
        self.data_loader = data_loader
        self.state_manager = state_manager
        self.layout_manager = layout_manager
        
        self.maidens = ["Claire", "Lisa", "Marie"]
        self.cells = {}
        
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # No Layout
        self.show_locations = True
        self.icon_scale = 1.0
        
        for name in self.maidens:
            cell = MaidenCell(name, self)
            cell.clicked.connect(self.toggle_maiden)
            cell.position_changed.connect(self._on_cell_moved)
            self.cells[name] = cell
            cell.show()

        self.update_positions()
        self.refresh_state(self.state_manager.inventory)

    def update_positions(self):
        spacing = 90
        x = 10
        y = 10
        
        for name, cell in self.cells.items():
            default_x = x
            default_y = y
            x += spacing
            
            pos = self.layout_manager.get_position("maidens", name)
            if pos:
                cell.move(pos[0], pos[1])
            else:
                cell.move(default_x, default_y)

        self.update_min_size()

    def set_edit_mode(self, enabled):
        for cell in self.cells.values():
            cell.set_edit_mode(enabled)
            
    def _on_cell_moved(self, name, x, y):
        self.layout_manager.set_position("maidens", name, x, y)
        self.update_min_size()

    def update_min_size(self):
        max_x = 0
        max_y = 0
        for cell in self.cells.values():
            max_x = max(max_x, cell.x() + cell.width())
            max_y = max(max_y, cell.y() + cell.height())
        self.setMinimumSize(max_x + 10, max_y + 10)
            
    def set_icon_scale(self, scale):
        self.icon_scale = scale
        for cell in self.cells.values():
            cell.set_icon_scale(scale)
        self.update_positions()
        
    def set_locations_visible(self, visible):
        self.show_locations = visible
        self.refresh_state(self.state_manager.inventory)
            
    def connect_signals(self, state_manager=None):
        # Allow passing state_manager or using self.state_manager
        sm = state_manager if state_manager else self.state_manager
        sm.inventory_changed.connect(self.refresh_state)
        # Also refresh when characters get optionally assigned to update location string
        sm.character_assigned.connect(lambda l, n: self.refresh_state(self.state_manager.inventory))
        
    def toggle_maiden(self, name):
        self.state_manager.toggle_manual_inventory(name)
        
    def refresh_state(self, inventory):
        # Get reverse lookup for locations: Character -> Location
        char_locations = {} 
        for loc, char in self.state_manager._character_locations.items():
            char_locations[char] = loc
            
        for name, cell in self.cells.items():
            is_active = inventory.get(name, False)
            location = char_locations.get(name)
            
            self.update_icon(cell, name, is_active)
            
            if location and is_active and getattr(self, 'show_locations', True):
                cell.set_location_text(location)
            else:
                cell.set_location_text(None)
                
            cell.adjustSize()
        self.update_min_size()
            
    def update_icon(self, cell, name, active):
        if active:
             data = self.data_loader.load_json("characters.json")
        else:
             data = self.data_loader.load_json("characters_bw.json")
        
        if name in data:
            rel_path = data[name]["image_path"]
            full_path = self.data_loader.resolve_image_path(rel_path)
            cell.set_pixmap(QPixmap(full_path))
        else:
            cell.name_label.setText(name[0])
