from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class PositioningCanvas(QWidget):
    """Absolute-positioning canvas with optional grid display and snapping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid_visible = False
        self._snap_to_grid = False
        self._grid_size = 10

    @property
    def grid_size(self) -> int:
        return self._grid_size

    def set_grid_visible(self, visible: bool):
        self._grid_visible = bool(visible)
        self.update()

    def set_snap_to_grid(self, enabled: bool):
        self._snap_to_grid = bool(enabled)

    def set_grid_size(self, size: int):
        self._grid_size = max(5, int(size))
        self.update()

    def snap_position(self, x: int, y: int, force: bool = False) -> QPoint:
        if not (self._snap_to_grid or force):
            return QPoint(max(0, int(x)), max(0, int(y)))
        grid = self._grid_size
        return QPoint(
            max(0, ((int(x) + grid // 2) // grid) * grid),
            max(0, ((int(y) + grid // 2) // grid) * grid),
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._grid_visible:
            return

        painter = QPainter(self)
        pen = QPen(QColor(255, 255, 255, 38))
        pen.setWidth(1)
        painter.setPen(pen)
        grid = self._grid_size
        for x in range(0, self.width(), grid):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid):
            painter.drawLine(0, y, self.width(), y)
        painter.end()
