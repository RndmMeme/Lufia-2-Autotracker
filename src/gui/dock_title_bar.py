from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QStyle
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

class DockTitleBar(QWidget):
    def __init__(self, title, dock_widget):
        super().__init__(dock_widget)
        self.dock_widget = dock_widget
        
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(5, 2, 5, 2)
        self.layout.setSpacing(2)
        self.setLayout(self.layout)
        
        # Style
        self.setStyleSheet("background-color: #3A2B50; color: white; border-bottom: 1px solid #555;")
        # Purple-ish dark background
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; padding-left: 5px;")
        self.layout.addWidget(self.title_label)
        
        self.layout.addStretch()
        
        # Font Controls (Hidden by default)
        self.font_down_btn = QPushButton("-")
        self.font_down_btn.setFixedSize(20, 20)
        self.font_down_btn.setToolTip("Decrease Font Size")
        self.font_down_btn.clicked.connect(lambda: self.dock_widget.adjust_font_size(-1))
        self.layout.addWidget(self.font_down_btn)
        
        self.font_up_btn = QPushButton("+")
        self.font_up_btn.setFixedSize(20, 20)
        self.font_up_btn.setToolTip("Increase Font Size")
        self.font_up_btn.clicked.connect(lambda: self.dock_widget.adjust_font_size(1))
        self.layout.addWidget(self.font_up_btn)
        
        self.set_font_controls_visible(False)
        
        # Pin Button (Toggle Movable)
        self.pin_btn = QPushButton("📌") # Unicode Pushpin
        self.pin_btn.setCheckable(True)
        self.pin_btn.setToolTip("Pin Dock (Prevent Dragging)")
        self.pin_btn.setFixedSize(24, 24) # Slightly larger for text
        # Remove standard icon to show text
        self.pin_btn.clicked.connect(self._toggle_pin)
        self.layout.addWidget(self.pin_btn)
        
        # Float Buton
        self.float_btn = QPushButton("❐") # Squared (Window-like)
        self.float_btn.setToolTip("Detach / Float")
        self.float_btn.setFixedSize(24, 24)
        self.float_btn.clicked.connect(self._toggle_float)
        self.layout.addWidget(self.float_btn)

        # Close Button
        self.close_btn = QPushButton("✕")
        self.close_btn.setToolTip("Close")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.dock_widget.close)
        self.layout.addWidget(self.close_btn)
        
        # Listen for float changes to update UI
        self.dock_widget.topLevelChanged.connect(self._on_float_changed)
        
        # Initial State
        self._update_pin_icon(False)

    def set_font_controls_visible(self, visible):
        self.font_down_btn.setVisible(visible)
        self.font_up_btn.setVisible(visible)

    def _toggle_pin(self, checked):
        features = self.dock_widget.features()
        if checked:
            # Pinned = Not Movable
            features &= ~self.dock_widget.DockWidgetFeature.DockWidgetMovable
            features &= ~self.dock_widget.DockWidgetFeature.DockWidgetFloatable
        else:
            # Unpinned = Movable
            features |= self.dock_widget.DockWidgetFeature.DockWidgetMovable
            features |= self.dock_widget.DockWidgetFeature.DockWidgetFloatable
            
        self.dock_widget.setFeatures(features)
        self._update_pin_icon(checked)

    def _update_pin_icon(self, is_pinned):
        if is_pinned:
             # Visual cue for "Locked" - Simple, no red background
             self.pin_btn.setStyleSheet("font-weight: bold; border: 1px solid gray;") 
             self.pin_btn.setToolTip("Unpin to Move")
        else:
             self.pin_btn.setStyleSheet("")
             self.pin_btn.setToolTip("Pin to Lock")

    def _toggle_float(self):
        # Toggle floating state
        self.dock_widget.setFloating(not self.dock_widget.isFloating())

    def set_header_color(self, color_hex):
        from PyQt6.QtGui import QColor
        bg = QColor(color_hex)
        # Calculate perceived brightness (standard formula)
        brightness = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
        text_color = "black" if brightness > 128 else "white"
        
        self.setStyleSheet(f"background-color: {color_hex}; color: {text_color}; border-bottom: 1px solid #555;")
        
    def _on_float_changed(self, is_floating):
        if is_floating:
            self.float_btn.setText("⬇") # Arrow Down (Dock back)
            self.float_btn.setToolTip("Dock back to Window")
            # self.float_btn.setStyleSheet("background-color: #ccffcc;") # Removed Color
        else:
            self.float_btn.setText("❐")
            self.float_btn.setToolTip("Detach / Float")
            # self.float_btn.setStyleSheet("")
