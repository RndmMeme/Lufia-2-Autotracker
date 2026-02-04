from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsPolygonItem
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QBrush, QColor, QPainter, QPolygonF, QPen
import logging
from utils.constants import GAME_WORLD_SIZE, CANVAS_SIZE, COLORS

class InteractiveDot(QGraphicsEllipseItem):
    """
    A clickable dot on the map representing a location/city.
    """
    def __init__(self, location_name, x, y, size=10, initial_color="red"):
        # Center the dot on the coordinate
        rect_x = x - (size / 2)
        rect_y = y - (size / 2)
        super().__init__(rect_x, rect_y, size, size)
        
        self.location_name = location_name
        self.setAcceptHoverEvents(True)
        # User feedback: Hand cursor interacts poorly/obscures dots. Using standard Arrow.
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip(location_name)
        
        # Call set_color to apply the brush
        self.set_color(initial_color)

    def set_color(self, color_name):
        qt_color = QColor(COLORS.get(color_name, "red"))
        self.setBrush(QBrush(qt_color))
        self.setPen(QPen(Qt.PenStyle.NoPen))

    def mousePressEvent(self, event):
        """Handle interactions. Left click triggers state toggle via the Scene."""
        # Crucial: Accept event to prevent View from stealing it for Drag/Panning
        event.accept() 
        if event.button() == Qt.MouseButton.LeftButton:
            # Propagate the click to the parent view/scene to handle the logic
            # We can use the scene's method if we define it, or emit a signal from the view
            # For QGraphicsItem, direct signal emission isn't built-in without QObject inheritance.
            # Best practice: The View handles the scene interaction.
             pass
        super().mousePressEvent(event)

class InteractiveSprite(QGraphicsPixmapItem):
    """
    A draggable sprite with context menu support.
    """
    def __init__(self, pixmap, remove_callback=None, parent=None):
        super().__init__(pixmap, parent)
        self.remove_callback = remove_callback
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        
    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu()
        hide_action = QAction("Remove from Map", menu)
        hide_action.triggered.connect(self._hide_self)
        menu.addAction(hide_action)
        
        menu.exec(event.screenPos())
        
    def _hide_self(self):
        if self.remove_callback:
            self.remove_callback()
        else:
            self.setVisible(False)

class MapWidget(QGraphicsView):
    # Signals
    location_clicked = pyqtSignal(str) # name
    location_right_clicked = pyqtSignal(str) # name, for context menu
    sprite_removed = pyqtSignal(str) # location_name
    
    def __init__(self, data_loader):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        
        # ... (Config) ...
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Scale config...
        self._scale_x = CANVAS_SIZE[0] / GAME_WORLD_SIZE[0]
        self._scale_y = CANVAS_SIZE[1] / GAME_WORLD_SIZE[1]
        
        # Load Map
        map_path = data_loader.resolve_image_path("map/map.jpg")
        self._background_item = QGraphicsPixmapItem(QPixmap(map_path))
        
        orig_width = self._background_item.pixmap().width()
        orig_height = self._background_item.pixmap().height()
        bg_scale_x = CANVAS_SIZE[0] / orig_width
        bg_scale_y = CANVAS_SIZE[1] / orig_height
        self._background_item.setTransform(self._background_item.transform().scale(bg_scale_x, bg_scale_y))
        
        self._scene.addItem(self._background_item)
        
        self._dots = {}
        self._player_arrow = None
        
        self._init_locations(data_loader.get_locations())
        self._init_player_arrow()
        
        # User requested restoration of static marker behavior (no blinking).
        self._player_visible = True

    def reset(self):
        """Clears all character sprites and resets player position."""
        # Clear Sprites
        if hasattr(self, '_char_items'):
            for location, item in list(self._char_items.items()):
                self._scene.removeItem(item)
            self._char_items.clear()
            
        # Hide Player
        if self._player_arrow:
            self._player_arrow.hide()
            
        # Dots reset color is handled by update_dot_color called by logic engine

    # ... (init methods) ...

    def _init_locations(self, locations_data):
        """Creates a dot for every location in the JSON."""
        for name, coords in locations_data.items():
            # Apply scaling 4096 -> 400
            canvas_x = coords[0] * self._scale_x
            canvas_y = coords[1] * self._scale_y
            
            dot = InteractiveDot(name, canvas_x, canvas_y)
            self._scene.addItem(dot)
            self._dots[name] = dot

    def _init_player_arrow(self):
        """Creates the player position marker."""
        self.set_player_arrow_shape("triangle")

    def set_player_arrow_shape(self, shape: str):
        """Updates the shape of the player marker."""
        current_brush = QBrush(QColor("orange"))
        current_pos = QPointF(0, 0)
        is_visible = False
        
        if self._player_arrow:
            current_brush = self._player_arrow.brush()
            current_pos = self._player_arrow.pos()
            is_visible = self._player_arrow.isVisible()
            self._scene.removeItem(self._player_arrow)
            
    def set_player_arrow_shape(self, shape: str):
        """Updates the shape of the player position arrow ('triangle' or 'rhombus' or 'square' or 'sprite')."""
        self._player_shape = shape
        
        current_brush = QBrush(QColor("magenta")) # Default
        current_pos = QPointF(0, 0)
        is_visible = True

        if self._player_arrow:
            # PixmapItem (Sprite) has no brush. Preserve previous color if switching back.
            if hasattr(self._player_arrow, 'brush'):
                current_brush = self._player_arrow.brush()
            
            current_pos = self._player_arrow.pos()
            is_visible = self._player_arrow.isVisible()
            self._scene.removeItem(self._player_arrow)
            
        if shape == "rhombus":
             # Rhombus (Diamond)
             polygon = QPolygonF([
                QPointF(0, -7),   # Top
                QPointF(7, 0),    # Right
                QPointF(0, 7),    # Bottom
                QPointF(-7, 0)    # Left
             ])
             self._player_arrow = QGraphicsPolygonItem(polygon)
             self._player_arrow.setBrush(current_brush)
             
        elif shape == "square":
            # Square 10x10 (Centered)
            from PyQt6.QtWidgets import QGraphicsRectItem
            self._player_arrow = QGraphicsRectItem(-5, -5, 10, 10)
            self._player_arrow.setBrush(current_brush)
            
        elif shape == "sprite" and getattr(self, '_player_sprite_pixmap', None):
            # Sprite Mode
            # Fixed 40px size as requested
            scaled = self._player_sprite_pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._player_arrow = QGraphicsPixmapItem(scaled)
            # Center the sprite (Offset by -20, -20)
            # Note: QGraphicsPixmapItem origin is Top-Left. To center at "pos", we translate.
            self._player_arrow.setOffset(-20, -20)
            # Brush is irrelevant for Pixmap
            
        else:
            # Triangle (Default)
            # Fallback if sprite is selected but no image available -> Triangle
            polygon = QPolygonF([
                QPointF(0, 0),    # Tip at the coordinate
                QPointF(-5, -10), # Top Left
                QPointF(5, -10)   # Top Right
            ])
            self._player_arrow = QGraphicsPolygonItem(polygon)
            self._player_arrow.setBrush(current_brush)
            
        if shape != "sprite" and not isinstance(self._player_arrow, QGraphicsPixmapItem):
             self._player_arrow.setPen(QPen(Qt.PenStyle.NoPen))
             
        self._player_arrow.setZValue(100)
        self._player_arrow.setPos(current_pos)
        self._player_arrow.setScale(getattr(self, '_player_scale', 1.0))
        self._scene.addItem(self._player_arrow)
        
        if is_visible:
            self._player_arrow.show()
        else:
            self._player_arrow.hide() 

    def update_dot_color(self, name, color_name):
        if name in self._dots:
            self._dots[name].set_color(color_name)

    def update_dot_tooltip(self, name, text):
        if name in self._dots:
            self._dots[name].setToolTip(text)
            
    def set_player_arrow_color(self, hex_color: str):
        """Updates the color of the player position arrow."""
        # Only apply color if NOT a sprite
        if self._player_arrow and not isinstance(self._player_arrow, QGraphicsPixmapItem):
            self._player_arrow.setBrush(QBrush(QColor(hex_color)))

    def set_player_scale(self, scale: float):
        """Sets the scale of the player marker."""
        self._player_scale = scale
        if self._player_arrow:
            self._player_arrow.setScale(scale)

    def set_player_sprite_image(self, pixmap_path: str):
        """Sets the sprite image to be used when shape is 'sprite'."""
        if pixmap_path:
            self._player_sprite_pixmap = QPixmap(pixmap_path)
        else:
            self._player_sprite_pixmap = None
            
        # If currently in sprite mode, refresh
        if getattr(self, '_player_shape', 'triangle') == 'sprite':
            self.set_player_arrow_shape('sprite')

    def resizeEvent(self, event):
        """Ensure map scales with the widget."""
        super().resizeEvent(event)
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mousePressEvent(self, event):
        # Handle Drag Mode
        if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
             super().mousePressEvent(event)
             return
             
        # Check for item at pos
        pos = self.mapToScene(event.pos())
        item = self._scene.itemAt(pos, self.transform())
        
        if isinstance(item, InteractiveDot):
             if event.button() == Qt.MouseButton.LeftButton:
                 self.location_clicked.emit(item.location_name)
                 event.accept()
                 return # Don't propagate
             elif event.button() == Qt.MouseButton.RightButton:
                 self.location_right_clicked.emit(item.location_name)
                 event.accept()
                 return # Don't propagate
                 
        if isinstance(item, InteractiveSprite):
             # Let sprite handle its own context menu
             super().mousePressEvent(event) 
             return
             
        super().mousePressEvent(event)

    def update_player_position(self, x, y):
        safe_x = max(0, min(x, CANVAS_SIZE[0]))
        safe_y = max(0, min(y, CANVAS_SIZE[1]))
        
        self._player_arrow.setPos(safe_x, safe_y)
        self._player_arrow.show() # Ensure visible


    # ... (event methods) ...

    def add_character_sprite(self, location, char_name, pixmap_path):
        """Adds a draggable character sprite to the map."""
        if location not in self._dots:
            logging.warning(f"Map: Location {location} not found for char assignment.")
            return

        # Remove existing if any
        self.remove_character_sprite(location)

        # Create Pixmap Item
        pix = QPixmap(pixmap_path)
        pixel_size = 32
        pix = pix.scaled(pixel_size, pixel_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Use InteractiveSprite with Remove Callback
        item = InteractiveSprite(pix, remove_callback=lambda: self.sprite_removed.emit(location))
        
        # Position slightly offset from dot
        dot = self._dots[location]
        dot_x = dot.rect().x()
        dot_y = dot.rect().y()
        item.setPos(dot_x + 10, dot_y - 10)
        
        # Tooltip
        item.setToolTip(f"{char_name} at {location}")
        
        self._scene.addItem(item)
        
        # Store
        if not hasattr(self, '_char_items'):
            self._char_items = {} # loc -> item
        self._char_items[location] = item
        
        # Mark Location as Cleared visually (override)
        # Note: StateManager handles the "Logic" state update which emits location_changed,
        # so MapWidget.update_dot_color handles the dot color.

    def remove_character_sprite(self, location):
        if not hasattr(self, '_char_items'):
            return
            
        item = self._char_items.pop(location, None)
        if item:
            self._scene.removeItem(item)

    def set_sprites_visibility(self, category: str, visible: bool):
        """
        category: 'all', 'chars', 'capsules', 'maidens'
        """
        maidens = {"Claire", "Lisa", "Marie"}
        capsules = {"Jelze", "Flash", "Gusto", "Zeppy", "Darbi", "Sully", "Blaze"}
        
        if not hasattr(self, '_char_items'): return
        
        for item in self._char_items.values():
             char_name = getattr(item, 'char_name', '')
             
             is_target = False
             if category == 'all': is_target = True
             elif category == 'maidens' and char_name in maidens: is_target = True
             elif category == 'capsules' and char_name in capsules: is_target = True
             elif category == 'chars' and char_name not in maidens and char_name not in capsules: is_target = True
             
             if is_target:
                 item.setVisible(visible)


    # ... (event methods) ...

    def add_character_sprite(self, location, char_name, pixmap_path):
        """Adds a draggable character sprite to the map."""
        if location not in self._dots:
            logging.warning(f"Map: Location {location} not found for char assignment.")
            return
 
        # Remove existing if any
        self.remove_character_sprite(location)
 
        # Create Pixmap Item
        pix = QPixmap(pixmap_path)
        # Scale to 32x32
        pixel_size = 32
        pix = pix.scaled(pixel_size, pixel_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Use InteractiveSprite with Remove Callback
        item = InteractiveSprite(pix, remove_callback=lambda: self.sprite_removed.emit(location))
        item.char_name = char_name # Store text for filtering
        
        # Position slightly offset from dot
        dot = self._dots[location]
        dot_x = dot.rect().x()
        dot_y = dot.rect().y()
        item.setPos(dot_x + 10, dot_y - 10)
        
        # Tooltip
        item.setToolTip(f"{char_name} at {location}")
        
        self._scene.addItem(item)
        
        # Store
        if not hasattr(self, '_char_items'):
            self._char_items = {} # loc -> item
            self._char_items_map = {} # Unique ID/Ref -> Item? No just iterate values.
            
        self._char_items[location] = item
        
        # We need to iterate items for visibility toggle.
        if not hasattr(self, '_char_items_map'):
             self._char_items_map = {} # item -> char_name ??
             # Actually I attached char_name to item. So I can just iterate _char_items.values()
             pass
        self._char_items_map[char_name] = item # Only one sprite per char? Usually yes.
        # But wait, logic is loc -> item.
        # We use _char_items.values() in toggle.
        
        # Mark Location as Cleared visually (override)

