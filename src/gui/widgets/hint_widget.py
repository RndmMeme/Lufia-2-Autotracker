from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class HintWidget(QWidget):
    """
    Displays hints.
    Currently a simple text area, but can be expanded for specific rich text hints.
    """
    hints_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        self.label = QLabel("Looking for Hints...")
        layout.addWidget(self.label)
        
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(False)
        self.text_area.setPlaceholderText("Type your hints/notes here...")
        self.text_area.textChanged.connect(lambda: self.hints_changed.emit(self.text_area.toPlainText()))
        layout.addWidget(self.text_area)
        
    def set_content_font_size(self, size):
        # Update text area font size
        font = self.text_area.font()
        font.setPixelSize(size)
        self.text_area.setFont(font)
        
    def set_hints(self, text):
        self.text_area.setText(text)
