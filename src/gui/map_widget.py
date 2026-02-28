from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsPolygonItem
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QBrush, QColor, QPainter, QPolygonF, QPen
import logging
from utils.constants import GAME_WORLD_SIZE, CANVAS_SIZE, COLORS

class InteractiveDot(QGraphicsItem):
    """
    A clickable dot on the map representing a location/city.
    """
    def __init__(self, location_name, x, y, size=10, initial_color="red"):
        super().__init__()
        
        self.location_name = location_name
        self.setPos(x, y)
        self._size = size
        self._shape = "circle"
        self._color_name = initial_color
        self._custom_hex_color = None
        self._is_city = False
        self._is_highlighted = False

        self.setAcceptHoverEvents(True)
        # User feedback: Hand cursor interacts poorly/obscures dots. Using standard Arrow.
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._tooltip_text = location_name

    def hoverEnterEvent(self, event):
        from PyQt6.QtWidgets import QToolTip
        QToolTip.showText(event.screenPos(), self._tooltip_text)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        from PyQt6.QtWidgets import QToolTip
        QToolTip.hideText()
        super().hoverLeaveEvent(event)

    def setToolTip(self, text):
        self._tooltip_text = text

    def boundingRect(self):
        from PyQt6.QtCore import QRectF
        s = self._size / 2.0
        # Expand boundingRect by 5 pixels to safely enclose the highlight cyan ring (r = s + 3 with 3.0 pen width)
        padding = 5.0
        return QRectF(-s - padding, -s - padding, self._size + padding*2, self._size + padding*2)

    def shape(self):
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        s = self._size / 2.0
        if self._shape == "square":
            path.addRect(-s, -s, self._size, self._size)
        elif self._shape == "rhombus":
            poly = QPolygonF([QPointF(0, -s), QPointF(s, 0), QPointF(0, s), QPointF(-s, 0)])
            path.addPolygon(poly)
        elif self._shape == "triangle":
            poly = QPolygonF([QPointF(0, -s), QPointF(s, s), QPointF(-s, s)])
            path.addPolygon(poly)
        else: # circle
            path.addEllipse(-s, -s, self._size, self._size)
        return path

    def paint(self, painter, option, widget=None):
        qt_color = None
        # Only use custom color if the dot is a city and hasn't been completely cleared
        if self._is_city and self._color_name == "city" and getattr(self, '_custom_hex_color', None):
            qt_color = QColor(self._custom_hex_color)
        else:
            qt_color = QColor(COLORS.get(self._color_name, "red"))
            
        painter.setBrush(QBrush(qt_color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        
        s = self._size / 2.0
        if self._shape == "square":
            # Using QRectF
            from PyQt6.QtCore import QRectF
            painter.drawRect(QRectF(-s, -s, self._size, self._size))
        elif self._shape == "rhombus":
            poly = QPolygonF([QPointF(0, -s), QPointF(s, 0), QPointF(0, s), QPointF(-s, 0)])
            painter.drawPolygon(poly)
        elif self._shape == "triangle":
            poly = QPolygonF([QPointF(0, -s), QPointF(s, s), QPointF(-s, s)])
            painter.drawPolygon(poly)
        else: # circle
            from PyQt6.QtCore import QRectF
            painter.drawEllipse(QRectF(-s, -s, self._size, self._size))

        if getattr(self, '_is_highlighted', False):
            hl_pen = QPen(QColor("cyan"))
            hl_pen.setWidthF(3.0)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(hl_pen)
            r = s + 3
            from PyQt6.QtCore import QRectF
            painter.drawEllipse(QRectF(-r, -r, r*2, r*2))

    def set_shape(self, shape_name, is_city=False):
        self._shape = shape_name
        self._is_city = is_city
        self.update()

    def set_custom_color(self, hex_color):
        self._custom_hex_color = hex_color
        self.update()

    def set_color(self, color_name):
        self._color_name = color_name
        self.update()

    def mousePressEvent(self, event):
        """Handle interactions. Left click triggers state toggle via the Scene."""
        # Crucial: Accept event to prevent View from stealing it for Drag/Panning
        event.accept() 
        if event.button() == Qt.MouseButton.LeftButton:
            # Propagate the click to the parent view/scene to handle the logic
            # We can use the scene's method if we define it, or emit a signal from the view
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
        self.data_loader = data_loader
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
        # Find cities to mark them appropriately
        cities = {}
        if hasattr(self, 'data_loader'):
             cities = set(self.data_loader.get_cities())
             
        for name, coords in locations_data.items():
            # Apply scaling 4096 -> 400
            canvas_x = coords[0] * self._scale_x
            canvas_y = coords[1] * self._scale_y
            
            dot = InteractiveDot(name, canvas_x, canvas_y)
            if name in cities:
                dot._is_city = True
                dot.set_shape(getattr(self, '_city_shape', 'square'), is_city=True) 
            else:
                dot.set_shape(getattr(self, '_dungeon_shape', 'circle'), is_city=False)
            
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
            dot = self._dots[name]
            dot.set_color(color_name)
            
            if dot._is_city:
                # Custom City Color
                custom_color = getattr(self, '_city_color', None)
                if custom_color:
                    dot.set_custom_color(custom_color)

    def set_city_color_override(self, hex_color: str):
        self._city_color = hex_color
        self._refresh_dots()

    def set_city_shape(self, shape: str):
        self._city_shape = shape
        for dot in self._dots.values():
            if getattr(dot, '_is_city', False):
                dot.set_shape(shape, is_city=True)

    def set_dungeon_shape(self, shape: str):
        self._dungeon_shape = shape
        for dot in self._dots.values():
            if not getattr(dot, '_is_city', False):
                dot.set_shape(shape, is_city=False)

    def highlight_location(self, name: str):
        self.clear_highlight()
        if name in self._dots:
             self._dots[name]._is_highlighted = True
             self._dots[name].update()
             self._highlighted_dot = name

    def clear_highlight(self):
        if hasattr(self, '_highlighted_dot') and self._highlighted_dot:
             if self._highlighted_dot in self._dots:
                 self._dots[self._highlighted_dot]._is_highlighted = False
                 self._dots[self._highlighted_dot].update()
             self._highlighted_dot = None

    def _refresh_dots(self):
        # We need to re-trigger dot coloring to apply new overrides
        # Or just manually update them if we store the base `color_name`
        for name, dot in self._dots.items():
            self.update_dot_color(name, dot._color_name)

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

