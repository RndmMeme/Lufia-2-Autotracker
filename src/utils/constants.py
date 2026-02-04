import os
import sys
from pathlib import Path

# Base Paths
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent

BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "src" / "data"
IMAGES_DIR = BASE_DIR / "images"

# Sacred Pixel Coordinates (Extracted from shared.py in v1.3)
# DO NOT MODIFY THESE VALUES UNDER ANY CIRCUMSTANCES
GAME_WORLD_SIZE = (4096, 4096)
CANVAS_SIZE = (400, 400)

# Color Constants
COLORS = {
    'accessible': 'lightgreen',
    'fully_accessible': 'lightgreen',
    'not_accessible': 'red',
    'city': 'yellow',
    'cleared': 'grey'
}

LOCATION_STATES = {
    "not_accessible": "red",
    "partially_accessible": "orange",
    "fully_accessible": "lightgreen",
    "cleared": "grey"
}

STATE_ORDER = ["not_accessible", "fully_accessible", "cleared"]

ALWAYS_ACCESSIBLE_LOCATIONS = {
    'Foomy Woods',
    'Mnt.Of No Return',
    'Shaia Lab',
    'Darbi Shrine',
    'Cave to Sundletan'
}
