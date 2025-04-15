# shared.py
import os
from helpers.file_loader import load_json, load_image
from pathlib import Path
import json
import logging

# Define the base directory as the directory of this script
BASE_DIR = Path(__file__).resolve().parent

# Define the images and data directories relative to the base directory
IMAGES_DIR = BASE_DIR / "images"
DATA_DIR = BASE_DIR / "data"
AUTO_DIR = BASE_DIR / "auto"

json_cache = {}

WIDGET_STORE = {}

config = {
    'base_address': None,
    'process': None
}

COLORS = {
    'accessible': 'lightgreen',
    'not_accessible': 'red',
    'city': 'yellow',
    'cleared': 'grey'
}

LOCATION_STATES = {
    "not_accessible": "red",
    "partly_accessible": "orange",
    "fully_accessible": "lightgreen",
    "cleared": "grey"
}

ALWAYS_ACCESSIBLE_LOCATIONS = {
    'Foomy Woods',
    'Mnt.Of No Return',
    'Shaia Lab',
    'Darbi Shrine',
    'Cave to Sundletan'
}
STATE_ORDER = ["not_accessible", "fully_accessible", "cleared"]

# Cache for loaded data
_data_cache = {}

def generate_item_to_location_mapping(locations_logic):
    """
    Generates a mapping of items to locations based on the access rules in locations logic.
    """
    item_to_location = {}
    for location, logic in locations_logic.items():
        access_rules = logic.get("access_rules", [])
        for rule in access_rules:
            items = rule.split(',')
            for item in items:
                item = item.strip()  # Ensure there are no extra spaces
                if item not in item_to_location:
                    item_to_location[item] = set()
                item_to_location[item].add(location)
    return item_to_location

def update_character_image(canvas, character_images, name, image_path, image_cache):
    """
    Updates the image of a character on the canvas.
    """
    if image_path:
        if image_path not in image_cache:
            new_image = load_image(image_path)
            image_cache[image_path] = new_image
        else:
            new_image = image_cache[image_path]
        
        if new_image:
            position = character_images[name]['position']
            canvas.itemconfig(position, image=new_image)
            character_images[name]['image'] = new_image
            # Keep a reference to the image to prevent garbage collection
            if not hasattr(canvas, 'images'):
                canvas.images = []
            canvas.images.append(new_image)

def load_json_cached(filename):
    """
    Load JSON data from a file with caching to improve performance on repeated accesses.
    
    :param filename: Path to the JSON file.
    :return: Parsed JSON data as a dictionary, or an empty dictionary if an error occurs.
    """
    if filename in json_cache:
        return json_cache[filename]
    
    try:
        with open(filename, "r") as file:
            data = json.load(file)
            json_cache[filename] = data  # Cache the loaded JSON data
            return data
    except json.JSONDecodeError as e:
        logging.error(f"Error loading JSON from {filename}: {e}")
    except FileNotFoundError:
        logging.error(f"File not found: {filename}")
    except PermissionError:
        logging.error(f"Permission denied for file: {filename}")
    except Exception as e:
        logging.error(f"Unexpected error loading JSON from {filename}: {e}")
    
    return {}



def resolve_relative_path(base_path, relative_path):
    """
    Resolve the relative path to an absolute path based on the base path.
    """
    resolved_path = os.path.abspath(os.path.join(base_path, relative_path))
    return resolved_path

def resolve_image_paths(data, base_dir):
    """
    Resolves relative image paths in the data dictionary to full paths.
    
    :param data: Dictionary containing image data with relative paths.
    :param base_dir: Base directory to resolve the relative paths.
    """
    for item_name, item_data in data.items():
        if "image_path" in item_data:
            item_data["image_path"] = base_dir / item_data["image_path"]
        if "image_path_bw" in item_data:
            item_data["image_path_bw"] = base_dir / item_data["image_path_bw"]
        if "down_image_path" in item_data:
            item_data["down_image_path"] = base_dir / item_data["down_image_path"]
        if "color_image_path" in item_data:
            item_data["color_image_path"] = base_dir / item_data["color_image_path"]


# Load the locations_logic.json data and generate the mapping
locations_logic = load_json_cached(DATA_DIR / "locations_logic.json")
item_to_location = generate_item_to_location_mapping(locations_logic)

# Load configurations with caching
LOCATIONS = load_json_cached(DATA_DIR / "locations.json")
LOCATION_LOGIC = load_json_cached(DATA_DIR / "locations_logic.json")
CITIES = load_json_cached(DATA_DIR / "cities.json")
characters = load_json_cached(DATA_DIR / "characters.json")
characters_bw = load_json_cached(DATA_DIR / "characters_bw.json")
tool_items_bw = load_json_cached(DATA_DIR / "tool_items_bw.json")
scenario_items_bw = load_json_cached(DATA_DIR / "scenario_items_bw.json")
tool_items_c = load_json_cached(DATA_DIR / "tool_items.json")
scenario_items_c = load_json_cached(DATA_DIR / "scenario_items.json")
item_spells = load_json_cached(DATA_DIR / "items_spells.json")
map_address = os.path.join(IMAGES_DIR / "map", "map.jpg")
emulator_addresses = load_json_cached(DATA_DIR / "emulator_addresses.json")
boss_locations = load_json_cached(DATA_DIR / "boss_locations.json")
current_config = load_json_cached(DATA_DIR / "current_emulator_config.json")
dungeon_flags_snes = load_json_cached(DATA_DIR / "dungeon_flags_snes9x.json")
dungeon_flags_nwa = load_json_cached(DATA_DIR / "dungeon_flags_snes9x-nwa.json")
spoiler_temp = load_json_cached(DATA_DIR / 'spoiler_temp.json')
location_mapping = load_json_cached(DATA_DIR / "location_name_mapping.json")


# Resolve paths for character images
resolve_image_paths(characters, IMAGES_DIR )
resolve_image_paths(characters_bw, IMAGES_DIR )

# Resolve paths for tool items (black and white and colored)
resolve_image_paths(tool_items_bw ,IMAGES_DIR)
resolve_image_paths(tool_items_c , IMAGES_DIR)

# Resolve paths for scenario items (black and white and colored)
resolve_image_paths(scenario_items_bw , IMAGES_DIR)
resolve_image_paths(scenario_items_c , IMAGES_DIR)


    

