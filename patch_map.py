import os
import re

path = r"d:\Projects\Python\lufia2_manualtracker_v1.4\src\gui\map_widget.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

new_interactive_dot = '''class InteractiveDot(QGraphicsItem):
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
        event.accept() 
        if event.button() == Qt.MouseButton.LeftButton:
             pass
        super().mousePressEvent(event)
'''

content = re.sub(r'class InteractiveDot\(.*?\):.*?(?=class InteractiveSprite)', new_interactive_dot + "\n", content, flags=re.DOTALL)

old_init = '''    def _init_locations(self, locations_data):
        """Creates a dot for every location in the JSON."""
        for name, coords in locations_data.items():
            # Apply scaling 4096 -> 400
            canvas_x = coords[0] * self._scale_x
            canvas_y = coords[1] * self._scale_y
            
            dot = InteractiveDot(name, canvas_x, canvas_y)
            self._scene.addItem(dot)
            self._dots[name] = dot'''

new_init = '''    def _init_locations(self, locations_data):
        """Creates a dot for every location in the JSON."""
        import json
        cities = []
        try:
            with open(r"d:\\Projects\\Python\\lufia2_manualtracker_v1.4\\src\\data\\cities.json", "r") as f:
                cities = json.load(f)
        except:
            pass

        for name, coords in locations_data.items():
            # Apply scaling 4096 -> 400
            canvas_x = coords[0] * self._scale_x
            canvas_y = coords[1] * self._scale_y
            
            dot = InteractiveDot(name, canvas_x, canvas_y)
            
            if getattr(self, '_city_color_hex', None):
                 dot.set_custom_color(self._city_color_hex)
            
            if name in cities:
                dot._is_city = True
                dot.set_shape(getattr(self, '_city_shape', 'square'), is_city=True)
            else:
                dot.set_shape(getattr(self, '_dungeon_shape', 'circle'), is_city=False)
                
            self._scene.addItem(dot)
            self._dots[name] = dot'''

if old_init in content:
    content = content.replace(old_init, new_init)

additions = '''
    def set_city_color_override(self, hex_color: str):
        self._city_color_hex = hex_color
        for dot in self._dots.values():
             if getattr(dot, '_is_city', False):
                 dot.set_custom_color(hex_color)

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
            self._highlighted_dot = self._dots[name]
            self._highlighted_dot._is_highlighted = True
            self._highlighted_dot.update()

    def clear_highlight(self):
        if hasattr(self, '_highlighted_dot') and self._highlighted_dot:
            self._highlighted_dot._is_highlighted = False
            self._highlighted_dot.update()
            self._highlighted_dot = None
'''

if "def set_city_shape" not in content:
    content += additions

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patch successfully applied.")
