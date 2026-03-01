from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QVBoxLayout, QFrame, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor

class DraggableLabel(QLabel):
    clicked_signal = pyqtSignal()
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(50, 50)
        self.setScaledContents(True)

    def mousePressEvent(self, event):
        if self.parent() and getattr(self.parent(), 'edit_mode', False):
            # Pass the event up to CharacterCell to handle the Drag
            event.ignore()
        elif event.button() == Qt.MouseButton.LeftButton:
            self.clicked_signal.emit()

class CharacterCell(QWidget):
    """
    Compound widget: Icon + Name Label + Location Label
    """
    clicked = pyqtSignal(str)
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedWidth(80) # Slightly wider for long names
        self.setMinimumHeight(130) # Enforce height to reserve space for text (Fix Clipping)
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
        
        # Name
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
        
    # (Methods set_edit_mode, mousePress/Move/Release... remain same)

    def set_edit_mode(self, enabled):
        self.edit_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if self.edit_mode:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.edit_mode and self._drag_start_pos:
             # Move Logic
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
            
    # Signals
    position_changed = pyqtSignal(str, int, int)
    
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
            # Manual wrapping logic to match (roughly) v1.3 behavior
            # Split long words
            words = text.split()
            lines = []
            for word in words:
                if len(word) > 9: # v1.3 max_line_length
                    # Simple split
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


class CharactersCanvas(QWidget):
    # ... init ...
    def __init__(self, data_loader, state_manager, layout_manager, parent=None):
        super().__init__(parent)
        self.data_loader = data_loader
        self.state_manager = state_manager
        self.layout_manager = layout_manager
        
        self.cells = {} # name -> CharacterCell
        self.edit_mode = False
        self.show_locations = True
        self.icon_scale = 1.0
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        # No Layout - Absolute Positioning
        
        # Load Characters
        chars_data = self.data_loader.load_json("characters.json")
        
        excluded = ["Claire", "Lisa", "Marie"]
        heroes = ["Maxim", "Selan", "Guy", "Artea", "Tia", "Dekar", "Lexis"]
        
        items = []
        for h in heroes:
            if h in chars_data:
                items.append(h)
        
        others = [k for k in chars_data.keys() if k not in heroes and k not in excluded]
        items.extend(sorted(others))
        
        self._ordered_items = items # Store order for reflow
        
        for name in items:
            cell = CharacterCell(name, self)
            # Initial create (pos will be set in reflow)
            cell.show()
            
            cell.clicked.connect(self.toggle_character)
            cell.position_changed.connect(self._on_cell_moved)
            
            self.cells[name] = cell
            
        self.refresh_state() # Will modify content then reflow

    def _reflow_grid(self):
        """Recalculates positions for non-manually-moved cells based on content height."""
        x_start = 5
        y_start = 5
        
        current_x = x_start
        current_y = y_start
        
        col_count = 0
        max_cols = 4
        col_width = 75 # Cell width ~70 + gap
        row_max_h = 0
        
        # Row Buffer
        current_row_cells = []
        
        for name in self._ordered_items:
            if name not in self.cells: continue
            cell = self.cells[name]
            
            # Resize cell to fit content (Dynamic Height)
            if hasattr(cell, 'layout') and cell.layout:
                cell.layout.activate()
            cell.adjustSize() 
            w = cell.width()
            h = cell.height()
            
            # Default Layout Position
            default_x = current_x
            default_y = current_y
            
            # Check Manual Override
            pos = self.layout_manager.get_position("characters", name)
            if pos:
                cell.move(pos[0], pos[1])
            else:
                cell.move(default_x, default_y)
                
            # Calculate next default position
            row_max_h = max(row_max_h, h)
            current_x += col_width
            col_count += 1
            
            if col_count >= max_cols:
                # New Row
                col_count = 0
                current_x = x_start
                # Move Down by the tallest item in the previous row + EXTRA Padding (Doubled request)
                current_y += row_max_h + 50 
                row_max_h = 0
                current_row_cells = []
        
        # Update Canvas Size
        self.update_min_size()

    # ... (rest of class) ...

    def set_edit_mode(self, enabled):
        self.edit_mode = enabled
        for cell in self.cells.values():
            cell.set_edit_mode(enabled)

    def _on_cell_moved(self, name, x, y):
        self.layout_manager.set_position("characters", name, x, y)
        self.update_min_size()

    def update_min_size(self):
        max_x = 0
        max_y = 0
        for cell in self.cells.values():
            max_x = max(max_x, cell.x() + cell.width())
            max_y = max(max_y, cell.y() + cell.height())
        self.setMinimumSize(max_x + 10, max_y + 10)
            
    def connect_signals(self):
        self.state_manager.character_changed.connect(self._on_character_changed)
        self.state_manager.character_assigned.connect(self._on_assignment_changed)
        self.state_manager.character_unassigned.connect(self._on_assignment_changed)

    def _on_character_changed(self, name, obtained):
        self.refresh_state()

    def _on_assignment_changed(self, location, name):
        self.refresh_state()
        
    def set_content_font_size(self, size):
        for cell in self.cells.values():
            cell.set_font_size(size)

    def set_icon_scale(self, scale):
        self.icon_scale = scale
        for cell in self.cells.values():
            cell.set_icon_scale(scale)
        self._reflow_grid()

    def set_locations_visible(self, visible):
        self.show_locations = visible
        self.refresh_state()

    def toggle_character(self, name):
        is_obtained = self.state_manager.obtained_characters.get(name, False)
        self.state_manager.set_character_obtained(name, not is_obtained)
        
    def refresh_state(self):
        active_party = self.state_manager.active_party # Humans Only
        obtained_capsules = getattr(self.state_manager, '_obtained_capsules', set())
        obtained_chars = self.state_manager.obtained_characters
        
        # Get reverse lookup for locations: Character -> Location
        char_locations = {} 
        for loc, char in self.state_manager._character_locations.items():
            char_locations[char] = loc
            
        chars_data = self.data_loader.load_json("characters.json")
        
        for name, cell in self.cells.items():
            if name not in chars_data:
                continue
                
            is_active_human = name in active_party
            is_active_capsule = name in obtained_capsules
            is_obtained = obtained_chars.get(name, False)
            location = char_locations.get(name)
            
            # --- Visual Logic ---
            # 1. Active Human or Capsule -> Full Opacity
            # 2. Recruited Inactive Human -> Dimmed (0.5) 
            # 3. Not Obtained -> Dimmed / Grey (0.3)
            
            rel_path = chars_data[name]["image_path"]
            full_path = self.data_loader.resolve_image_path(rel_path)
            pix = QPixmap(full_path)
            
            # Reset Styling
            cell.setStyleSheet("")

            if is_active_human or is_active_capsule:
                cell.set_pixmap(pix)
            elif is_obtained:
                # Recruited but inactive -> Dimmed 
                # User said: "As long as there is a location assigned to them it signals they have been found."
                # User said: "recruited but inactive characters are still fully lit. at this point just dim them."
                # User feedback: "active state of an acquired character is too dim" -> Brighten from 0.5 to 0.85.
                
                dim_pix = QPixmap(pix.size())
                dim_pix.fill(Qt.GlobalColor.transparent)
                painter = QPainter(dim_pix)
                painter.setOpacity(0.85) # Brighter
                painter.drawPixmap(0, 0, pix)
                painter.end()
                
                cell.set_pixmap(dim_pix)
                # Maybe border to indicate "found but not party"?
                # cell.setStyleSheet("CharacterCell { border: 1px solid #444; border-radius: 4px; }") 
            else:
                # Not Obtained -> Heavy Dim + Grey
                gray_pix = QPixmap(pix.size())
                gray_pix.fill(Qt.GlobalColor.transparent)
                painter = QPainter(gray_pix)
                painter.setOpacity(0.4) # Increased from 0.2
                painter.drawPixmap(0, 0, pix)
                painter.end()
                cell.set_pixmap(gray_pix)
                
            if location and getattr(self, 'show_locations', True):
                cell.set_location_text(location)
            else:
                cell.set_location_text(None)
                
        # Recalculate positions now that text height might have changed
        self._reflow_grid()


class CharactersWidget(QWidget):
    """
    Wrapper widget adding a QScrollArea around the CharactersCanvas.
    Allows the dock to shrink smaller than the content.
    """
    def __init__(self, data_loader, state_manager, layout_manager, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        self.canvas = CharactersCanvas(data_loader, state_manager, layout_manager, self)
        self.layout.addWidget(self.canvas)
        
        # Connect signals
        self.state_manager.character_changed.connect(self.refresh_state)
        # Also need assignment changes
        self.state_manager.character_assigned.connect(lambda l, n: self.refresh_state())
        
    def set_content_font_size(self, size):
        self.canvas.set_content_font_size(size)
        
    def set_icon_scale(self, scale):
        self.canvas.set_icon_scale(scale)
        
    def set_locations_visible(self, visible):
        self.canvas.set_locations_visible(visible)
        
    def set_edit_mode(self, enabled):
        self.canvas.set_edit_mode(enabled)

    def refresh_state(self):
         # Forward directly to canvas
         self.canvas.refresh_state()
         
    def connect_signals(self):
         pass
