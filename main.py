# main.py

import threading
import tkinter as tk
from tkinter import ttk
import os
import sys
import pymem
import time
from pathlib import Path
import logging
import json

# Import necessary functions and modules
from helpers.file_loader import load_image
from helpers.memory_utils import read_memory_with_retry, check_game_running, is_process_running, read_memory
from gui_setup import setup_interface, setup_canvases, setup_scanners
from shared import LOCATIONS, LOCATION_LOGIC, CITIES, tool_items_bw, scenario_items_bw, item_to_location, characters_bw, ALWAYS_ACCESSIBLE_LOCATIONS, load_json_cached, generate_item_to_location_mapping, resolve_relative_path, BASE_DIR, IMAGES_DIR, DATA_DIR, shop_addresses, config, GOLD_ADDRESS, pointer_base_address, shop_offset
from canvas_config import update_autoscan_label, update_character_image, map_address, setup_tools_canvas, setup_scenario_canvas, setup_characters_canvas, setup_maidens_canvas, setup_item_canvas, setup_hints_canvas
from event_handlers import handle_tool_click, handle_scenario_click, handle_dot_click
from game_tracking import track_game, show_error_window
from logic import LocationLogic
from shop_calc import process_shop_data, process_and_save_shop_data
from inventory_scan import initialize_shared_variables
from button_functions import sync_game_state

# Ensure the directory exists
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logging
logging.basicConfig(
    filename=os.path.join(log_dir, 'app.log'),
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# Load emulator addresses
EMULATOR_CONFIG_PATH = os.path.join(DATA_DIR, 'emulator_addresses.json')

def read_rom_start_address(process, pointer_base_address):
    try:
        raw_address = process.read_bytes(pointer_base_address, 4)
        if raw_address:
            reversed_bytes = raw_address[::-1]
            
            return reversed_bytes.hex()
            
        else:
            raise ValueError("Failed to read ROM start address.")
    except Exception as e:
        logging.error(f"Error reading ROM start address: {e}")
        return None

def verify_shop_pointer(process, shop_pointer):
    try:
        address_int = int(shop_pointer, 16)
        verification_bytes = process.read_bytes(address_int, 4)
        if verification_bytes:
            valid = verification_bytes.hex() == '029c0002'
            return valid
        else:
            return False
    except Exception as e:
        logging.error(f"Error verifying shop table base address at {shop_pointer}: {e}")
        return False

def create_emulator_config():
    try:
        if is_process_running("snes9x-x64.exe"):
            process = pymem.Pymem("snes9x-x64.exe")
            base_address = process.process_base.lpBaseOfDll

            with open(EMULATOR_CONFIG_PATH, 'r') as file:
                emulator_configs = json.load(file)

            configs = emulator_configs.get("snes9x-x64.exe", [])
            for config in configs:
                pointer_base_address = int(config['pointer_base_address'], 16) + base_address
                rom_start_address = read_rom_start_address(process, pointer_base_address)
                if rom_start_address:
                    shop_pointer = int(rom_start_address, 16) + int(config['shop_offset'], 16)
                    if verify_shop_pointer(process, hex(shop_pointer)):
                        with open(os.path.join(DATA_DIR, 'current_emulator_config.json'), 'w') as f:
                            json.dump(config, f)
                        return config

        if emulator_configs:
            import shared
            shared.GOLD_ADDRESS = int(emulator_configs['gold_address'], 16)
            shared.pointer_base_address = int(emulator_configs['pointer_base_address'], 16)
            shared.shop_offset = int(emulator_configs['shop_offset'], 16)
            shared.character_slots = [int(slot, 16) for slot in emulator_configs['character_slots']]
            shared.inventory_range = [int(addr, 16) for addr in emulator_configs['inventory_range']]
            shared.scenario_range = [int(addr, 16) for addr in emulator_configs['scenario_range']]
            return emulator_configs

        logging.error("No matching emulator configuration found.")
    except Exception as e:
        logging.error(f"Error creating emulator configuration: {e}")
    return None

class Lufia2TrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lufia 2 Auto Tracker")
        self.pointer_base_address = None
        self.shop_offset = None
        self.shop_pointer_verified = False
        self.shop_addresses = None  # Initialize shop addresses

        # Initialize essential attributes
        self.base_dir = BASE_DIR
        self.images_dir = IMAGES_DIR
        self.data_dir = DATA_DIR
        self.script_dir = Path(__file__).parent
        self.entries = {"Shop Item": [], "Spells": [], "Thief": []}
        self.image_cache = {}  # Image cache to avoid repeated loading

        # Load emulator configuration
        self.emulator_config = create_emulator_config()
        if self.emulator_config is None:
            show_error_window(self)
            return

        # Now load the current emulator configuration file
        config_path = os.path.join(DATA_DIR, 'current_emulator_config.json')
        with open(config_path, 'r') as f:
            emulator_config = json.load(f)

        self.pointer_base_address = int(emulator_config['pointer_base_address'], 16)
        self.shop_offset = int(emulator_config['shop_offset'], 16)
        self.GOLD_ADDRESS = int(emulator_config['gold_address'], 16)
        self.character_slots = [int(slot, 16) for slot in emulator_config['character_slots']]
        self.inventory_range = [int(addr, 16) for addr in emulator_config['inventory_range']]
        self.scenario_range = [int(addr, 16) for addr in emulator_config['scenario_range']]

        import shared
        shared.GOLD_ADDRESS = self.GOLD_ADDRESS
        shared.pointer_base_address = self.pointer_base_address
        shared.shop_offset = self.shop_offset
        shared.character_slots = self.character_slots
        shared.inventory_range = self.inventory_range
        shared.scenario_range = self.scenario_range

        # Initialize shared variables in inventory_scan.py
        initialize_shared_variables()

        # Initialize essential attributes
        self.base_dir = BASE_DIR
        self.images_dir = IMAGES_DIR
        self.data_dir = DATA_DIR
        self.script_dir = Path(__file__).parent
        self.entries = {"Shop Item": [], "Spells": [], "Thief": []}
        self.image_cache = {}  # Image cache to avoid repeated loading
        self.retrieve_base_address()  # Ensure process is set up here before it's needed elsewhere

        if self.base_address is None:
            show_error_window(self)
            return  # Exit the initialization if base address is not valid

        # Initialize essential attributes
        self.map_address = os.path.join(IMAGES_DIR / "map", "map.jpg")
        self.LOCATIONS = LOCATIONS
        
        shop_addresses_path = os.path.join(self.data_dir, 'shop_addresses.json')

        self.shop_addresses, self.shop_items = process_shop_data(self)

        self.inventory = {}
        self.previous_gold = None
        self.scenario_items = {}
        self.location_labels = {}
        self.tool_images = {}
        self.scenario_images = {}
        self.character_images = {}
        self.maidens_images = {}
        self.obtained_items = set()
        self.location_states = {location: "not_accessible" for location in LOCATIONS.keys()}
        self.location_labels_visible = True
        self.city_labels_visible = True
        self.tool_items_bw = {}
        self.tool_items_c = {}
        self.scenario_items_bw = {}
        self.scenario_items_c = {}
        self.item_to_location = {}
        self.logic = None
        self.update_accessible_locations = True
        self.stop_event = threading.Event()
        self.tracker_thread = None 
        self.initial_scan_done = False
        self.manual_input_active = False
        self.manually_updated_locations = {}
        self.manual_updates = {}
        self.manual_toggles = {}
        self.image_cache = {}
        self.characters = {}
        self.active_characters = set()  # To keep track of active characters
        self.previous_active_characters = set()
        self.auto_update_active = True
        self.full_scan_due = True

        # Initialize auto update flag
        self.auto_update_active = True

        # Image cache to avoid repeated loading
        self.image_cache = {}

        # Load data
        self.load_data()

        # Setup interface
        self.setup_interface()

        # Initialize canvases here
        self.setup_canvases()
        
        # Bind the click event to autoscan_label to trigger the sync callback
        self.autoscan_label.bind("<Button-1>", self.sync_game_state_callback)

        # Setup tools and scenario canvases
        tools_keys = list(tool_items_bw.keys())
        self.tools_canvas, self.tool_images = setup_tools_canvas(root, tools_keys, self.on_tool_click, self.image_cache)
        scenario_keys = list(scenario_items_bw.keys())
        self.scenario_canvas, self.scenario_images = setup_scenario_canvas(root, scenario_keys, item_to_location, self.on_scenario_click, self.image_cache)
        self.characters_canvas, self.character_images = setup_characters_canvas(self.root, self.characters, self.image_cache, self)

        # Setup maidens canvas with the check function
        self.maidens_canvas, self.maidens_images = setup_maidens_canvas(
            root, self.characters, characters_bw, self.image_cache, self.check_all_maidens_colored
        )

        # Populate initial canvases with black and white images
        self.populate_initial_canvases()

        # Setup scanners
        self.setup_scanners()

        # Initialize location logic
        self.logic = LocationLogic(self.script_dir, self.location_labels, self.canvas, self.maidens_images)

        # Start tracker thread
        self.start_tracker_thread()
        
        # Process and save shop data to JSON
        self.process_and_save_shop_data_to_json()

    def retrieve_base_address(self):
        try:
            if is_process_running("snes9x-x64.exe"):
                self.process = pymem.Pymem("snes9x-x64.exe")
                self.base_address = self.process.process_base.lpBaseOfDll
                config['base_address'] = self.base_address
                config['process'] = self.process
            else:
                logging.error("snes9x-x64.exe is not running.")
        except pymem.exception.ProcessNotFound:
            logging.error("Process not found. Make sure the game is running.")
            self.base_address = None

    def check_all_maidens_colored(self):
        """
        Check if all maidens' images are colored and update the location "Daos' Shrine".
        """
        all_colored = all(
            self.maidens_images[maiden]['is_colored']
            for maiden in ["Claire", "Lisa", "Marie"]
        )

        if all_colored:
            self.logic.mark_location("Daos' Shrine", True)  # Directly mark as accessible

    def setup_interface(self):
        setup_interface(self)

    def load_data(self):
        self.locations_logic = load_json_cached(self.data_dir / "locations_logic.json")
        self.characters = load_json_cached(self.data_dir / "characters.json")
        self.characters_bw = load_json_cached(self.data_dir / "characters_bw.json")
        self.item_to_location = generate_item_to_location_mapping(self.locations_logic)

    def setup_canvases(self):
        setup_canvases(self)

    def setup_scanners(self):
        if self.base_address is None:
            logging.error("Error: base_address is None during scanner setup.")
            return

        setup_scanners(self)

    def start_tracker_thread(self):
        self.stop_event = threading.Event()
        self.tracker_thread = threading.Thread(target=track_game, args=(self,))
        self.tracker_thread.start()

    def on_tool_click(self, tool_name):
        self.handle_manual_input()
        handle_tool_click(self, tool_name)
        update_autoscan_label(self.autoscan_label, False)

    def on_scenario_click(self, scenario_name):
        self.handle_manual_input()
        handle_scenario_click(self, scenario_name)
        update_autoscan_label(self.autoscan_label, False)

    def on_dot_click(self, location):
        dot = self.location_labels.get(location)
        if dot:
            current_color = self.canvas.itemcget(dot, "fill")
            next_color = self.get_next_state_color(current_color)
            self.canvas.itemconfig(dot, fill=next_color)
            self.manually_updated_locations[location] = next_color

    def get_next_state_color(self, current_color):
        color_order = ["red", "orange", "lightgreen", "grey"]
        next_index = (color_order.index(current_color) + 1) % len(color_order)
        return color_order[next_index]
    

    def sync_game_state(self):
        self.resume_automatic_updates()

    def handle_manual_input(self):
        self.manual_input_active = True
        self.auto_update_active = False
        print("Manual input detected. Pausing automatic updates.")

    def populate_initial_canvases(self):
        for tool_name, tool_info in self.tool_images.items():
            image_path = tool_items_bw[tool_name]["image_path"]
            new_image = self.load_image_cached(image_path)
            if new_image:
                position = tool_info['position']
                self.tools_canvas.itemconfig(position, image=new_image)
                tool_info['image'] = new_image

        for scenario_name, scenario_info in self.scenario_images.items():
            image_path = scenario_items_bw[scenario_name]["image_path"]
            new_image = self.load_image_cached(image_path)
            if new_image:
                position = scenario_info['position']
                self.scenario_canvas.itemconfig(position, image=new_image)
                scenario_info['image'] = new_image

    def load_image_cached(self, image_path):
        if image_path not in self.image_cache:
            new_image = load_image(image_path)
            self.image_cache[image_path] = new_image
        return self.image_cache[image_path]

    def update_character(self, name, hp):
        if name in self.manual_toggles:
            return  # Skip updates for manually toggled characters

        is_active = hp > 0  # Consider a character active if their HP is greater than 0

        # Special case for specific characters that have a colored path
        if name in ["Claire", "Lisa", "Marie"] and 'color_image_path' in self.characters[name]:
            is_active = True  # Ensure maidens are always shown in color

        # Update the character image based on activity status
        update_character_image(self.characters_canvas, self.character_images, name, is_active)

    def update_map_based_on_tools(self):
        obtained_items = self.obtained_items

        for location, logic in LOCATION_LOGIC.items():
            if location in self.manually_updated_locations:
                continue

            access_rules = logic.get("access_rules", [])
            fully_accessible = any(set(rule.split(',')).issubset(obtained_items) for rule in access_rules)
            partially_accessible = any(set(rule.split(',')).intersection(obtained_items) for rule in access_rules)

            dot, label = self.location_labels.get(location, (None, None))
            if dot and label:
                if location in ALWAYS_ACCESSIBLE_LOCATIONS:
                    dot_color = "lightgreen"
                elif location in CITIES:
                    dot_color = "blue"
                else:
                    dot_color = "lightgreen" if fully_accessible else "orange" if partially_accessible else "red"
                self.canvas.itemconfig(dot, fill=dot_color)
                

    def is_game_running(self, process, base_address):
        return check_game_running(self, process, base_address)

    def read_memory(self, process, address, size):
        return read_memory_with_retry(process, address, size)

    def on_resize(self, event):
        pass

    def on_closing(self):
        self.stop_event.set()
        self.tracker_thread.join()
        self.root.destroy()

    def resume_automatic_updates(self):
        self.manual_input_active = False
        self.auto_update_active = True
        
        if self.stop_event.is_set() or not self.tracker_thread.is_alive():
            self.stop_event.clear()
            self.start_tracker_thread()
     
    def process_and_save_shop_data_to_json(self):
        json_path = os.path.join(self.data_dir, 'shop_data.json')
        adjusted_shop_data, shop_items = process_and_save_shop_data(self, json_path)
        
    def sync_game_state_callback(self, event=None):
        sync_game_state(self)    
            
if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = Lufia2TrackerApp(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        with open("error_log.txt", "a") as error_file:
            error_file.write(f"Unhandled exception: {e}\n")
