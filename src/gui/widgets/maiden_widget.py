from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap

class DraggableMaidenLabel(QLabel):
    position_changed = pyqtSignal(str, int, int)
    clicked = pyqtSignal(str)

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(50, 50)
        self.setScaledContents(True)
        self.setToolTip(name)
        self.edit_mode = False
        self._drag_start_pos = None

    def set_edit_mode(self, enabled):
        self.edit_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor) # Or Arrow

    def mousePressEvent(self, event):
        if self.edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            # Normal Click
             self.clicked.emit(self.name)
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
        if self.edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.position_changed.emit(self.name, self.x(), self.y())
        super().mouseReleaseEvent(event)


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
        self.labels = {}
        
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # No Layout
        
        spacing = 60
        x = 10
        y = 10
        
        for name in self.maidens:
            # Check position
            pos = self.layout_manager.get_position("maidens", name)
            if pos:
                final_x, final_y = pos
            else:
                final_x = x
                final_y = y
                x += spacing
                
            lbl = DraggableMaidenLabel(name, self)
            lbl.move(final_x, final_y)
            lbl.show()
            
            lbl.clicked.connect(self.toggle_maiden)
            lbl.position_changed.connect(self._on_label_moved)
            
            self.labels[name] = lbl
            
            # Initial update
            self.update_icon(lbl, name, False)

        self.update_min_size()

    def set_edit_mode(self, enabled):
        for lbl in self.labels.values():
            lbl.set_edit_mode(enabled)
            
    def _on_label_moved(self, name, x, y):
        self.layout_manager.set_position("maidens", name, x, y)
        self.update_min_size()

    def update_min_size(self):
        max_x = 0
        max_y = 0
        for lbl in self.labels.values():
            max_x = max(max_x, lbl.x() + lbl.width())
            max_y = max(max_y, lbl.y() + lbl.height())
        self.setMinimumSize(max_x + 10, max_y + 10)
            
    def connect_signals(self, state_manager=None):
        # Allow passing state_manager or using self.state_manager
        sm = state_manager if state_manager else self.state_manager
        sm.inventory_changed.connect(self.refresh_state)
        
    def toggle_maiden(self, name):
        self.state_manager.toggle_manual_inventory(name)
        
    def refresh_state(self, inventory):
        for name, lbl in self.labels.items():
            is_active = inventory.get(name, False)
            self.update_icon(lbl, name, is_active)
            
    def update_icon(self, label, name, active):
        # Reuse character images
        # Logic same as before...
        json_file = "characters.json" # Always use colored path base
        # Logic in previous code: used active/bw json separately.
        
        if active:
             data = self.data_loader.load_json("characters.json")
        else:
             data = self.data_loader.load_json("characters_bw.json")
        
        if name in data:
            rel_path = data[name]["image_path"]
            full_path = self.data_loader.resolve_image_path(rel_path)
            label.setPixmap(QPixmap(full_path))
        else:
            label.setText(name[0])
