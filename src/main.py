import sys
import logging
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from core.data_loader import DataLoader
from core.logic_engine import LogicEngine
from core.state_manager import StateManager

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Lufia 2 Auto Tracker")
    app.setStyle("Fusion")
    
    # Global Dark Theme to fix light-mode system contrast issues
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #2b2b2b;
            color: #eeeeee;
        }
        QLineEdit, QTextEdit, QListWidget, QScrollArea {
            background-color: #2b2b2b;
            color: #eeeeee;
            border: 1px solid #444;
        }
        QDockWidget {
            color: #eeeeee;
            titlebar-close-icon: url(none);
            titlebar-normal-icon: url(none);
        }
        QMenuBar {
            background-color: #2b2b2b;
            color: #eeeeee;
        }
        QMenuBar::item:selected {
            background-color: #3d3d3d;
        }
        QMenu {
            background-color: #2b2b2b;
            color: #eeeeee;
            border: 1px solid #444;
        }
        QMenu::item:selected {
            background-color: #3d3d3d;
        }
        QToolTip {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #555;
        }
        /* Scrollbars (Vertical) */
        QScrollBar:vertical {
            border: none;
            background: #2b2b2b;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #555;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        /* Scrollbars (Horizontal) */
        QScrollBar:horizontal {
            border: none;
            background: #2b2b2b;
            height: 12px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #555;
            min-width: 20px;
            border-radius: 4px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
        QLabel {
            color: #eeeeee;
        }
    """)
    
    # Core Components
    # root_dir is handled internally by utils.constants
    data_loader = DataLoader()
    logic_engine = LogicEngine(data_loader)
    state_manager = StateManager(logic_engine)
    
    # GUI
    window = MainWindow(state_manager, data_loader, logic_engine)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
