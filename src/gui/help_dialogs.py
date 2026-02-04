from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QListWidget, QStackedWidget, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class BaseInfoDialog(QDialog):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 500)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Text Area
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setHtml(content)
        layout.addWidget(self.text_edit)
        
        # Close Button
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class AboutDialog(BaseInfoDialog):
    def __init__(self, parent=None):
        content = """
        <h3>Lufia 2 Auto Tracker v1.4</h3>
        <p><b>My Discord:</b><br>Rndmmeme#5100</p>
        
        <p><b>Lufia 2 Community on Discord:</b><br>Ancient Cave</p>
        
        <p><b>Many thanks to:</b></p>
        <ul>
            <li><b>abyssonym</b> (Creator of Lufia 2 Randomizer "terrorwave"):<br>
            <a href="https://github.com/abyssonym/terrorwave">https://github.com/abyssonym/terrorwave</a><br>
            who patiently explained a lot of the secrets to me :)</li>
            
            <li><b>The3X</b> (Testing and Feedback):<br>
            <a href="https://www.twitch.tv/the3rdx">https://www.twitch.tv/the3rdx</a></li>
            
            <li>The Lufia 2 Community</li>
            
            <li>And of course, you, who decided to use my tracker!</li>
        </ul>
        
        <p><b>Disclaimer:</b><br>
        If you want to use this tracker for competitive plays please make sure it is accepted for tracking. 
        Also make sure to either not use the auto tracking function or to ask whether it is allowed to be used.</p>
        
        <p><b>RndmMeme</b><br>
        Lufia 2 Auto Tracker v1.3 @2024-2025<br>
        Ported to v1.4 (PyQt6) @2026</p>
        """
        super().__init__("About", content, parent)

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help & Documentation")
        self.resize(700, 500) # Wider for pages
        
        # Main Layout
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Navigation List (Left)
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(180)
        self.nav_list.currentRowChanged.connect(self._change_page)
        self.nav_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
                color: #81d4fa;
            }
        """)
        layout.addWidget(self.nav_list)
        
        # Content Stack (Right)
        self.pages = QStackedWidget()
        layout.addWidget(self.pages)
        
        # --- Add Pages ---
        
        # 1. Introduction
        self.add_page("Introduction", """
            <h3>Welcome to RndmMeme's Lufia 2 Auto Tracker v1.4!</h3>
            <p>This tracker helps you keep track of your randomizer run with advanced features like auto-tracking, map visualization, and inventory management.</p>
            <p><b>New in v1.4.2:</b></p>
            <ul>
                <li>Scalable Player Markers (1x-4x)</li>
                <li>Active Party Sprite Marker</li>
                <li>Smoother Map Scaling</li>
            </ul>
        """)
        
        # 2. Layout & UI
        self.add_page("Layout & UI", """
            <h3>Customizing the Interface</h3>
            <h4>Dock System</h4>
            <ul>
                <li><b>Rearrange:</b> Drag 'n drop dock titles to rearrange panels.</li>
                <li><b>Float:</b> Drag a panel out to make it a separate window.</li>
                <li><b>Font Size:</b> Enable 'Show Font Adj' in Options. Use (+/-) on dock headers to scale text size.</li>
                <li><b>Header Color:</b> Use 'Header Color' in Options to customize dock appearance.</li>
            </ul>
            <h4>Free Placement (Edit Layout)</h4>
            <ul>
                <li>Toggle 'Edit Layout' in Options.</li>
                <li>Drag and drop ANY icon in Characters, Tools, or Keys widgets to your preferred order.</li>
                <li>Your layout is saved automatically.</li>
            </ul>
        """)
        
        # 3. Tracker & Auto
        self.add_page("Tracker & Auto", """
            <h3>Tracking Controls</h3>
            <h4>Auto Tracker</h4>
            <ul>
                <li><b>Auto Toggle:</b> Starts the background listener for game data (USB2SNES/QUsb2Snes).</li>
                <li><b>Sync Menu:</b> Perform a one-time snapshot of specific data (Inventory, Characters, etc.) without keeping the connection open.</li>
                <li><b>Status:</b> The 'Auto' text turns Green when active.</li>
            </ul>
            <h4>Granular Filters</h4>
            <p>In the 'Tracker' menu, you can toggle which data types to update (e.g. disable 'Pos' if you want manual map control).</p>
        """)

        # 4. Player Marker
        self.add_page("Player Marker", """
            <h3>Player Position Marker</h3>
            <p>Customize how you appear on the map:</p>
            <ul>
                <li><b>Shape:</b> Choose Triangle, Rhombus, Square, or <b>Active Sprite</b>.</li>
                <li><b>Active Sprite:</b> Displays the sprite of your current Party Leader (Slot 1). Updates automatically!</li>
                <li><b>Size:</b> Adjust the marker size (1x, 2x, 3x, 4x) via 'Tracker > Player Size'.</li>
                <li><b>Color:</b> Pick a custom color via 'Tracker > Player Color' (applies to shapes only).</li>
            </ul>
        """)
        
        # 5. Map & Item Management
        self.add_page("Map & Items", """
            <h3>Map Interaction</h3>
            <ul>
                <li><b>Left-Click Dungeon Dot:</b> Cycle state (Red -> Green -> Grey -> Red).</li>
                <li><b>Right-Click City (Yellow):</b> Open Item Search to register shop contents.</li>
                <li><b>Right-Click Location:</b> Open Character Assignment menu.</li>
            </ul>
            <h3>Color Codes</h3>
            <ul>
                <li><span style="color:red">Red</span>: Not accessible</li>
                <li><span style="color:orange">Orange</span>: Partially accessible / Glitched</li>
                <li><span style="color:green">Green</span>: Fully accessible</li>
                <li><span style="color:grey">Grey</span>: Cleared / Looted</li>
                <li><span style="color:#CCCC00">Yellow</span>: City / Shop check</li>
            </ul>
        """)

        # 6. Characters
        self.add_page("Character & Sprites", """
            <h3>Managing Characters</h3>
            <ul>
                <li><b>Auto:</b> Characters are marked obtained when they join your party.</li>
                <li><b>Manual Assign:</b> Right-click a location on the map and select a character (e.g. 'Found Guy at Alunze').</li>
                <li><b>Sprites:</b> A sprite will appear on the map at the assigned location.</li>
                <li><b>Drag & Drop:</b> You can drag character sprites on the map if they obscure a location dot!</li>
                <li><b>Toggle:</b> Use 'Show Sprites' menu to hide/show specific categories (Maidens, Capsules, etc).</li>
            </ul>
        """)

        # 7. Persistence
        self.add_page("Persistence", """
            <h3>Auto-Saving Preferences</h3>
            <p>The tracker automatically saves your settings when you close the window:</p>
            <ul>
                <li><b>Window State:</b> Size, Position, and Dock Layout.</li>
                <li><b>Custom Layouts:</b> Positions from 'Edit Layout' mode.</li>
                <li><b>Visuals:</b> Header Color, Player Marker (Color, Shape, Scale).</li>
            </ul>
            <p>These settings are restored automatically when you launch the tracker next time.</p>
        """)
        # 8. Emulator Support & Disclaimer
        self.add_page("Emulator Support", """
            <h3>Emulator Support & Disclaimer</h3>
            <p>This tracker has been successfully tested with:</p>
            <ul>
                <li><b>Snes9x-x64</b> (Standard)</li>
                <li><b>Snes9x-nwa</b> (Split Memory Banks)</li>
                <li><b>bsnes</b></li>
            </ul>
            <p><b>Note:</b> We believe it should work with most other emulators that follow standard Snes9x/bsnes memory mapping.</p>
            <p>However, there is always the possibility that a specific emulator version is an edge case (e.g., different memory base pointers or offsets).</p>
            <p>If you encounter issues (e.g., "Auto" stays red or data doesn't update), please contact me via the means listed in the <b>About</b> dialog.</p>
            <p>Please provide the exact **Emulator Name and Version** you are using.</p>
        """)
        
        # Select first
        self.nav_list.setCurrentRow(0)

    def add_page(self, title, content):
        page = QWidget()
        vbox = QVBoxLayout()
        page.setLayout(vbox)
        
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #81d4fa; margin-bottom: 10px;")
        vbox.addWidget(lbl)
        
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(content)
        text.setStyleSheet("border: none; background-color: transparent; font-size: 14px;")
        vbox.addWidget(text)
        
        self.pages.addWidget(page)
        self.nav_list.addItem(title)
        
    def _change_page(self, row):
        self.pages.setCurrentIndex(row)
