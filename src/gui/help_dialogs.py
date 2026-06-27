from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QListWidget, QStackedWidget, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from utils.version import APP_VERSION

class BaseInfoDialog(QDialog):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon("Lufia_2_Auto_Tracker.ico"))
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
        content = f"""
        <h3>Lufia 2 Auto Tracker v{APP_VERSION}</h3>
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
        Ported to v1.4 (PyQt6) @2026<br>
        Current release v{APP_VERSION}</p>
        """
        super().__init__("About", content, parent)

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help & Documentation")
        self.setWindowIcon(QIcon("Lufia_2_Auto_Tracker.ico"))
        self.resize(850, 600)
        
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
        self.add_page("Introduction", f"""
            <h3>Welcome to RndmMeme's Lufia 2 Auto Tracker v{APP_VERSION}!</h3>
            <p>This tracker helps you keep track of your randomizer run with advanced features like auto-tracking, map visualization, and inventory management.</p>
            <p><b>New in v1.4.11:</b></p>
            <ul>
                <li><b>Clear Character States:</b> Every obtained character is fully lit; location notes identify where inactive recruits were found.</li>
                <li><b>Editable One-Shot Sync:</b> Synced party members can be manually toggled after the helper disconnects.</li>
                <li><b>Focused Menus:</b> Layout, View, and Style commands are grouped by what they affect.</li>
                <li><b>Current Guide:</b> Menu paths, independent panels, grids, syncing, and persistence are documented here.</li>
            </ul>
        """)
        
        # 2. Layout & UI
        self.add_page("Layout & UI", """
            <h3>Customizing the Interface</h3>
            <h4>Independent Panel System</h4>
            <ul>
                <li><b>Rearrange:</b> Drag a panel title to place it freely in the workspace.</li>
                <li><b>Resize:</b> Drag any panel border. Other panels retain their exact geometry; overlap is allowed.</li>
                <li><b>Float:</b> Use the detach button or double-click a title to make a separate window.</li>
                <li><b>Font Size:</b> Enable <b>View &gt; Panel Controls &gt; Show Font Controls</b>, then use (+/-) in panel headers.</li>
                <li><b>Icon Sizing:</b> Enable <b>View &gt; Panel Controls &gt; Show Icon Size Controls</b>.</li>
                <li><b>Recover Panels:</b> Use <b>Layout &gt; Panel Arrangement &gt; Restore Closed Panels</b>.</li>
                <li><b>Snap Back:</b> Use <b>Layout &gt; Panel Arrangement &gt; Snap Back Detached Panels</b>.</li>
                <li><b>Factory Arrangement:</b> Use <b>Layout &gt; Panel Arrangement &gt; Reset Panel Arrangement</b>.</li>
                <li><b>Header Color:</b> Use <b>Style &gt; Panel Appearance &gt; Header Color</b>.</li>
            </ul>
            <h4>Free & Grid Placement</h4>
            <ul>
                <li>Toggle <b>Layout &gt; Icon Placement &gt; Edit Icon Positions</b> to move icons inside Characters, Maidens, Tools, and Keys.</li>
                <li>The icon-placement switch does not control panel movement or resizing.</li>
                <li>Use the other <b>Icon Placement</b> commands for the picture grid, snapping, auto-align, defaults, and reset.</li>
                <li>Use <b>Layout &gt; Panel Arrangement &gt; Canvas Grid</b> to display a workspace grid and snap whole panels while moving or resizing them.</li>
                <li>Changing either grid size changes only its ruler; existing pictures and panels stay unchanged.</li>
                <li>Your layout is saved automatically.</li>
                <li>Icon resizing scales saved coordinates and spacing; smaller panels scroll instead of shrinking text.</li>
            </ul>
        """)

        self.add_page("Menus & Display", """
            <h3>Where Commands Live</h3>
            <ul>
                <li><b>Layout &gt; Icon Placement:</b> icon editing, picture grid, picture snapping, auto-align, and icon-position defaults.</li>
                <li><b>Layout &gt; Panel Arrangement:</b> Canvas Grid, closed-panel recovery, snap-back, and panel reset.</li>
                <li><b>View &gt; Panel Controls:</b> show or hide the per-panel font and icon-size buttons.</li>
                <li><b>View &gt; Character Display:</b> location notes and active-party visibility.</li>
                <li><b>View &gt; Map Sprites:</b> character, capsule, and Maiden sprites drawn on the map.</li>
                <li><b>Style &gt; Panel Appearance:</b> panel-header color.</li>
                <li><b>Style &gt; Player Marker:</b> map marker color, shape, and size.</li>
                <li><b>Style &gt; Map Locations:</b> city color plus city/dungeon marker shapes.</li>
            </ul>
        """)
        
        # 3. Tracker & Auto
        self.add_page("Tracker & Auto", """
            <h3>Tracking Controls</h3>
            <h4>Auto Tracker</h4>
            <ul>
                <li><b>Auto:</b> Continuously reads the emulator. Live memory will reassert inventory and character states after manual clicks.</li>
                <li><b>Sync:</b> Reads one valid snapshot and disconnects. The resulting board remains manually editable, including current party members.</li>
                <li><b>Status:</b> The ribbon shows discovery progress and turns green after a validated attachment.</li>
            </ul>
            <h4>Important: Loading Saves</h4>
            <p>When changing seed or save, use <b>Options &gt; Reset</b> before Sync/Auto if you want to discard manual overrides and notes from the previous run.</p>
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
                <li><b>Size:</b> Choose 1x, 2x, 3x, or 4x via <b>Style &gt; Player Marker &gt; Size</b>.</li>
                <li><b>Color:</b> Use <b>Style &gt; Player Marker &gt; Color</b> (applies to geometric markers).</li>
                <li><b>Shape:</b> Use <b>Style &gt; Player Marker &gt; Shape</b>.</li>
            </ul>
        """)
        
        # 5. Map & Item Management
        self.add_page("Map & Items", """
            <h3>Map Interaction</h3>
            <ul>
                <li><b>Left-Click Dungeon:</b> Toggle cleared state (Red/Green &harr; Grey).</li>
                <li><b>Right-Click Dungeon:</b> Open Character Assignment menu.</li>
            </ul>
            <h3>Appearance & Shapes</h3>
            <ul>
                <li>Use <b>Style &gt; Map Locations &gt; City Color</b> to adjust city color.</li>
                <li>Use <b>Style &gt; Map Locations &gt; City Shape</b> for city markers.</li>
                <li>Use <b>Style &gt; Map Locations &gt; Dungeon Shape</b> for dungeon markers.</li>
            </ul>
            <h3>Color Codes</h3>
            <ul>
                <li><span style="color:red">Red</span>: Not accessible</li>
                <li><span style="color:green">Green</span>: Fully accessible</li>
                <li><span style="color:grey">Grey</span>: Cleared / Looted</li>
            </ul>
        """)

        # 6. Characters
        self.add_page("Character & Sprites", """
            <h3>Managing Characters</h3>
            <ul>
                <li><b>Brightness:</b> Obtained characters are fully lit whether active or inactive. Unobtained characters are dimmed.</li>
                <li><b>One-Shot Sync:</b> Current party members can be clicked off/on after Sync disconnects.</li>
                <li><b>Continuous Auto:</b> Live memory restores the real party/obtained state on later updates.</li>
                <li><b>Manual Assign:</b> Right-click a location on the map and select a character (e.g. 'Found Guy at Alunze').</li>
                <li><b>Sprites:</b> A sprite will appear on the map at the assigned location.</li>
                <li><b>Drag & Drop:</b> You can drag character sprites on the map if they obscure a location dot!</li>
                <li><b>Map Sprites:</b> Use <b>View &gt; Map Sprites</b> to hide/show categories.</li>
                <li><b>Party Filter:</b> Disable <b>View &gt; Character Display &gt; Show Active Party Members</b> to hide active human slots while retaining inactive recruits and capsule monsters.</li>
            </ul>
        """)

        # 7. Persistence
        self.add_page("Persistence", """
            <h3>Auto-Saving Preferences</h3>
            <p>The tracker automatically saves your settings when you close the window:</p>
            <ul>
                <li><b>Panels:</b> Main-window geometry plus each panel's position, size, visibility, and detached state.</li>
                <li><b>Icon Positions:</b> Custom positions created through <b>Edit Icon Positions</b>.</li>
                <li><b>Grids:</b> Picture-grid and Canvas Grid visibility, snapping, and sizes.</li>
                <li><b>Visuals:</b> Header color, character display, and player marker settings.</li>
            </ul>
            <p>These settings are restored automatically when you launch the tracker next time.</p>
        """)

        # 8. Diagnostics
        self.add_page("Diagnostics", """
            <h3>Logs & Error Reports</h3>
            <p>Use <b>Help &gt; Open Log Folder</b> to access:</p>
            <ul>
                <li><b>tracker.log:</b> session, discovery, synchronization, and recovery events.</li>
                <li><b>error.log:</b> errors and critical failures with tracebacks and helper context.</li>
            </ul>
            <p>Logs rotate automatically and are stored under <code>%LOCALAPPDATA%\\Lufia2AutoTracker\\logs</code>.</p>
            <p>For emulator problems, reproduce the issue once and provide both current files with the emulator name and version.</p>
        """)

        # 9. Emulator Support & Disclaimer
        self.add_page("Emulator Support", """
            <h3>Emulator Support & Disclaimer</h3>
            <p>This tracker has been successfully tested with:</p>
            <ul>
                <li><b>Snes9x-x64</b> (Standard)</li>
                <li><b>Snes9x-nwa</b> (Split Memory Banks)</li>
                <li><b>bsnes</b></li>
            </ul>
            <p><b>How detection works:</b> Executable names are only hints. The tracker finds and validates the Lufia II WRAM root, then resolves every game value from one canonical map.</p>
            <p>Core inventory, character, dungeon, and position tracking can operate from WRAM alone. Capsule sprite metadata additionally requires a verified ROM mapping; spoiler-log discovery is a separate signature scan.</p>
            <p>If detection fails, provide the emulator name/version and the logs available through <b>Help &gt; Open Log Folder</b>.</p>
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
