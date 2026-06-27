import json
import logging
from PyQt6.QtCore import QObject
from utils.constants import DATA_DIR, USER_DATA_DIR

class LayoutManager(QObject):
    """
    Manages the saving and loading of widget positions within their containers.
    """
    def __init__(self):
        super().__init__()
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.config_path = USER_DATA_DIR / "layout_config.json"
        self.user_default_path = USER_DATA_DIR / "default_layout_config.json"
        self.factory_default_path = DATA_DIR / "default_layout_config.json"
        self.legacy_config_path = DATA_DIR / "layout_config.json"
        self._layouts = {}
        self.load_layout()

    def load_layout(self):
        load_path = self.config_path
        if not load_path.exists() and self.legacy_config_path.exists():
            load_path = self.legacy_config_path

        if load_path.exists():
            try:
                with open(load_path, 'r', encoding='utf-8') as f:
                    self._layouts = json.load(f)
                logging.info("Layout config loaded | path=%s", load_path)
                if load_path == self.legacy_config_path:
                    self.save_layout()
            except Exception:
                logging.exception("Failed to load layout config | path=%s", load_path)
                self._layouts = {}
        else:
            self._layouts = {}

    def save_layout(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._layouts, f, indent=4)
            logging.info("Layout config saved | path=%s", self.config_path)
        except Exception:
            logging.exception("Failed to save layout config | path=%s", self.config_path)

    def get_position(self, widget_id: str, item_name: str, scale: float = 1.0) -> tuple:
        """Return a logical saved position projected into the current icon scale."""
        container = self._layouts.get(widget_id, {})
        pos = container.get(item_name)
        if pos:
            return (round(pos['x'] * scale), round(pos['y'] * scale))
        return None

    def set_position(self, widget_id: str, item_name: str, x: int, y: int, scale: float = 1.0):
        """Store scale-independent logical coordinates for stable proportional resizing."""
        if widget_id not in self._layouts:
            self._layouts[widget_id] = {}

        safe_scale = max(0.01, float(scale))
        self._layouts[widget_id][item_name] = {
            'x': round(x / safe_scale, 3),
            'y': round(y / safe_scale, 3),
        }
        self.save_layout() # Auto-save on change? Or explicit save? Auto-save is easier for user.

    def clear_positions(self, widget_id: str):
        """Remove manual positions for one canvas so its deterministic layout can reflow."""
        self._layouts.pop(widget_id, None)
        self.save_layout()

    def replace_positions(self, widget_id: str, positions: dict, scale: float = 1.0):
        """Replace one canvas layout in a single durable write."""
        safe_scale = max(0.01, float(scale))
        self._layouts[widget_id] = {
            name: {
                'x': round(position[0] / safe_scale, 3),
                'y': round(position[1] / safe_scale, 3),
            }
            for name, position in positions.items()
        }
        self.save_layout()

    def save_custom_as_default(self):
        """Saves current layout as the fallback 'Default' layout."""
        try:
            with open(self.user_default_path, 'w', encoding='utf-8') as f:
                json.dump(self._layouts, f, indent=4)
            logging.info("Custom Default layout saved.")
        except Exception:
            logging.exception("Failed to save custom default layout | path=%s", self.user_default_path)

    def load_custom_default(self):
        """Load the user's default layout, falling back to the packaged factory layout."""
        default_path = self.user_default_path if self.user_default_path.exists() else self.factory_default_path
        if default_path.exists():
            try:
                with open(default_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                logging.exception("Failed to load default layout | path=%s", default_path)
        return {}

    def reset_layout(self):
        """Restores to the custom default, or empty if none exists."""
        self._layouts = self.load_custom_default()
        self.save_layout()
