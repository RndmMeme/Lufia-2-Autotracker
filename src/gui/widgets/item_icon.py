from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon

class ItemIcon(QWidget):
    """
    A clickable icon representing a tracker item (Tool/Scenario/Spell).
    - Toggles between Dimmed (Inactive) and Full Color (Active).
    - Supports optional text label.
    """
    toggled = pyqtSignal(str, bool) # name, new_state

    def __init__(self, name, image_path, size=48, show_label=False, parent=None):
        super().__init__(parent)
        self.name = name
        self.base_size = size
        self._is_active = False
        
        # Layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        self.setLayout(self.layout)
        
        # Icon Label
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(size, size)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_lbl.setProperty("class", "item-icon")
        self.layout.addWidget(self.icon_lbl)
        
        # Text Label (Optional)
        if show_label:
            self.text_lbl = QLabel(name)
            self.text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.text_lbl.setWordWrap(True)
            self.text_lbl.setStyleSheet("font-size: 10px; color: #ddd;")
            self.layout.addWidget(self.text_lbl)
        
        # Load Pixmap (Original)
        self._original_pixmap = QPixmap(image_path)
        if self._original_pixmap.isNull():
            self.icon_lbl.setText(name[:2])
            self.icon_lbl.setStyleSheet("border: 1px solid red;")
        
        # Scaling Configuration
        self.icon_lbl.setScaledContents(False) # We handle scaling manually for AspectRatio
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.icon_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.setMinimumSize(size, size) # Minimum reasonable size

        self._update_display()

    def resizeEvent(self, event):
        """Handle dynamic scaling of the icon."""
        self._update_display()
        super().resizeEvent(event)

    def set_active(self, active: bool):
        if self._is_active != active:
            self._is_active = active
            self._update_display()

    def is_active(self):
        return self._is_active

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_active(not self._is_active)
            self.toggled.emit(self.name, self._is_active)
        else:
            super().mousePressEvent(event)

    def _update_display(self):
        # Apply Opacity & Styling
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        opacity_effect = QGraphicsOpacityEffect(self.icon_lbl)
        
        # Determine which pixmap to show
        pixmap_to_show = None
        
        if hasattr(self, '_original_pixmap') and not self._original_pixmap.isNull():
             # Scale if needed
             target_size = self.icon_lbl.size()
             if target_size.width() >= 10 and target_size.height() >= 10:
                 # Standard scaling
                 pixmap_to_show = self._original_pixmap.scaled(
                    target_size, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                 )
        
        if pixmap_to_show:
            self.icon_lbl.setPixmap(pixmap_to_show)
            
            if self._is_active:
                # Active: Color, Full Opacity, Green Border
                opacity_effect.setOpacity(1.0)
                self.icon_lbl.setStyleSheet("border: 2px solid lime; border-radius: 4px; background-color: rgba(255, 255, 255, 0.1);")
            else:
                # Inactive: Original Color + Low Opacity (0.3 -> 0.15)
                # User requested: "opacity still a bit too high"
                opacity_effect.setOpacity(0.15) 
                self.icon_lbl.setStyleSheet("border: 1px solid #333; border-radius: 4px;")
        
        self.icon_lbl.setGraphicsEffect(opacity_effect)

    def set_font_size(self, size):
        if hasattr(self, 'text_lbl'):
            self.text_lbl.setStyleSheet(f"font-size: {size}px; color: #ddd;")

    def set_icon_scale(self, scale):
        size = int(self.base_size * scale)
        self.icon_lbl.setFixedSize(size, size)
        self.setMinimumSize(size, size)
        self._update_display()
