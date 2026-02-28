from PyQt6.QtWidgets import QWidget, QScrollArea, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

from .item_icon import ItemIcon
from .flow_layout import FlowLayout

import logging
from PyQt6.QtWidgets import QWidget, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QDrag, QPixmap

from .item_icon import ItemIcon
import logging

class DraggableItemIcon(ItemIcon):
    """
    Extension of ItemIcon to support dragging when edit mode is active.
    """
    position_changed = pyqtSignal(str, int, int) # name, x, y

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.edit_mode = False
        self._drag_start_pos = None

    def set_edit_mode(self, enabled):
        self.edit_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self.edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.edit_mode and self._drag_start_pos:
            if (event.pos() - self._drag_start_pos).manhattanLength() < 5:
                return
                
            # Perform Drag (Visual only, widget moves)
            # Actually for free placement within a parent, we implement move logic here directly
            # without QDrag if we stay in same widget.
            # But "Drag" implies standard DnD.
            # For "Free Placement" inside a Widget, standard `move()` on mouseMove is smoother.
            
            delta = event.pos() - self._drag_start_pos
            new_pos = self.pos() + delta
            
            # Constraints?
            # Ensure within parent area?
            # let's allow free move for now.
            
            self.move(new_pos)
            # We don't update drag_start_pos to keep delta relative to initial click offset
            # Wait, standard move logic:
            # new_center = event.globalPos() - parent.globalPos() ...
            # Simpler:
            # self.move(self.mapToParent(event.pos()) - self._drag_start_pos)
            
            # The logic above `self.pos() + delta` works if delta is local.
            # But event.pos() changes as we move the widget!
            # So we need global diff.
            pass
        else:
            # Propagate validation? ItemIcon doesn't have drag usually.
            pass
            
    # Re-implementing simplified drag without QDrag for smooth realtime movement
    def mouseMoveEvent(self, event):
        if self.edit_mode and self._drag_start_pos:
            # Calculate movement
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
            # Save position
            self.position_changed.emit(self.name, self.x(), self.y())
        else:
            super().mouseReleaseEvent(event)


class ItemGrid(QWidget):
    """
    A grid container for ItemIcons that supports absolute positioning.
    Refactored from FlowLayout to Free Placement.
    """
    item_clicked = pyqtSignal(str, bool)

    def __init__(self, data_dict, images_dir, widget_id, layout_manager, icon_size=40, show_labels=False, parent=None):
        super().__init__(parent)
        self.widget_id = widget_id
        self.layout_manager = layout_manager
        self.icon_size = icon_size
        self.show_labels = show_labels
        
        # No Layout! Absolute positioning.
        self.icons = {} # name -> ItemIcon
        
        # Initial Grid Params
        x = 5
        y = 5
        col = 0
        cols = 6
        spacing_x = icon_size + 10 # 50
        spacing_y = icon_size + 20 if show_labels else icon_size + 5
        
        import os
        
        for name, data in data_dict.items():
            rel_path = data.get("image_path", "")
            full_path = os.path.join(images_dir, rel_path)
            
            icon = DraggableItemIcon(name, full_path, size=icon_size, show_label=show_labels, parent=self)
            icon.show() # Explicitly show since not in layout
            
            icon.toggled.connect(self._on_item_toggled)
            icon.position_changed.connect(self._on_item_moved)
            
            self.icons[name] = icon

        self.update_positions()

    def update_positions(self):
        x = 5
        y = 5
        col = 0
        cols = 6
        spacing_x = self.icon_size + 10
        spacing_y = self.icon_size + 20 if self.show_labels else self.icon_size + 5
        
        for name, icon in self.icons.items():
            default_x = x + (col * spacing_x)
            default_y = y
            
            col += 1
            if col >= cols:
                col = 0
                y += spacing_y
                
            pos = self.layout_manager.get_position(self.widget_id, name)
            if pos:
                icon.move(pos[0], pos[1])
            else:
                icon.move(default_x, default_y)
                
        self.update_min_size()

    def set_edit_mode(self, enabled):
        for icon in self.icons.values():
            icon.set_edit_mode(enabled)

    def _on_item_toggled(self, name, state):
        self.item_clicked.emit(name, state)

    def _on_item_moved(self, name, x, y):
        self.layout_manager.set_position(self.widget_id, name, x, y)
        self.update_min_size()

    def update_min_size(self):
        max_x = 0
        max_y = 0
        for icon in self.icons.values():
            max_x = max(max_x, icon.x() + icon.width())
            max_y = max(max_y, icon.y() + icon.height())
        self.setMinimumSize(max_x + 10, max_y + 10)

    def set_item_state(self, name, state):
        if name in self.icons:
            self.icons[name].set_active(state)

    def set_content_font_size(self, size):
        for icon in self.icons.values():
            icon.set_font_size(size)
