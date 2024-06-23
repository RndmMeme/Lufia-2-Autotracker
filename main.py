# main.py

import threading
import tkinter as tk
from tkinter import ttk
import os
import sys
import pymem
import time
from pathlib import Path

# Import necessary functions and modules
from helpers.file_loader import load_image
from helpers.memory_utils import read_memory_with_retry, check_game_running, is_process_running, read_memory
from gui_setup import setup_interface, setup_canvases, setup_scanners
from shared import LOCATIONS, LOCATION_LOGIC, CITIES, tool_items_bw, scenario_items_bw, item_to_location, characters_bw, ALWAYS_ACCESSIBLE_LOCATIONS, load_json_cached, generate_item_to_location_mapping, resolve_relative_path, BASE_DIR, IMAGES_DIR, DATA_DIR
from canvas_config import update_character_image, map_address, setup_tools_canvas, setup_scenario_canvas, setup_characters_canvas, create_tabbed_interface, setup_maidens_canvas
from event_handlers import handle_tool_click, handle_scenario_click, handle_dot_click
from game_tracking import track_game
from logic import LocationLogic

# Constants
INVENTORY_START = 0xA32DA1
INVENTORY_END = 0xA32E60
SCENARIO_START = 0xA32C32
SCENARIO_END = 0xA32C37


class Lufia2TrackerApp:
    GOLD_ADDRESS = 0xA32D9E

    def __init__(self, root):
        print("Initializing Lufia2TrackerApp...")
        self.root = root
        self.root.title("Lufia 2 Auto Tracker")

        # Use constants from config
        self.base_dir = BASE_DIR
        self.images_dir = IMAGES_DIR
        self.data_dir = DATA_DIR

        self.script_dir = Path(__file__).parent
        
        self.entries = {
            "Shop Item": [],
            "Spells": [],
            "Thief": []
        }

        # Set initial window size and layout configuration
        self.root.geometry("728x978")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, minsize=1500)

        # Initialize essential attributes
        self.map_address = os.path.join(IMAGES_DIR / "map", "map.jpg")
        self.LOCATIONS = LOCATIONS


        # Create the tabbed interface and store tab references
        self.tabbed_interface, self.tabs = create_tabbed_interface(self.root)

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
        self.process = None
        self.base_address = None
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

        # Retrieve the base address
        self.retrieve_base_address()

        if self.base_address is None:
            print("Error: base_address is None. The tracker cannot proceed without a valid base address.")
            return  # Exit the initialization if base address is not valid

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

        # Setup tools and scenario canvases
        tools_keys = list(tool_items_bw.keys())
        self.tools_canvas, self.tool_images = setup_tools_canvas(root, tools_keys, self.on_tool_click, self.image_cache)

        scenario_keys = list(scenario_items_bw.keys())
        self.scenario_canvas, self.scenario_images = setup_scenario_canvas(root, scenario_keys, item_to_location, self.on_scenario_click, self.image_cache)

        self.characters_canvas, self.character_images = setup_characters_canvas(self.root, self.characters, self.image_cache, self)

        # Populate initial canvases with black and white images
        self.populate_initial_canvases()

        # Setup scanners
        self.setup_scanners()

        # Setup maidens canvas with the check function
        self.maidens_canvas, self.maidens_images = setup_maidens_canvas(
            root, self.characters, characters_bw, self.image_cache, self.check_all_maidens_colored
        )

        # Initialize location logic
        self.logic = LocationLogic(self.script_dir, self.location_labels, self.canvas, self.maidens_images)

        # Create tabbed interface
        self.tabbed_interface = create_tabbed_interface(self.root)

        # Start tracker thread
        self.start_tracker_thread()

    def retrieve_base_address(self):
        """
        Retrieve the base address of the game process.
        """
        try:
            if is_process_running("snes9x-x64.exe"):
                self.process = pymem.Pymem("snes9x-x64.exe")
                self.base_address = self.process.process_base.lpBaseOfDll
                print(f"Attached to snes9x-x64.exe at base address 0x{self.base_address:X}")
            else:
                print("snes9x-x64.exe is not running.")
        except pymem.exception.ProcessNotFound:
            print("Process not found. Make sure the game is running.")
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
            print("All maidens are colored. Updating 'Daos' Shrine' to accessible.")
            self.logic.mark_location("Daos' Shrine", True)  # Directly mark as accessible
        else:
            print("Not all maidens are colored yet.")

    def setup_interface(self):
        setup_interface(self)

    def load_data(self):
        print(f"Loading locations_logic.json from: {self.data_dir / 'locations_logic.json'}")
        print(f"Loading characters.json from: {self.data_dir / 'characters.json'}")

        self.locations_logic = load_json_cached(self.data_dir / "locations_logic.json")
        self.characters = load_json_cached(self.data_dir / "characters.json")
        self.characters_bw = load_json_cached(self.data_dir / "characters_bw.json")  # Add this line
        self.item_to_location = generate_item_to_location_mapping(self.locations_logic)
        print("Data loaded successfully.")

    def setup_canvases(self):
        setup_canvases(self)

    def setup_scanners(self):
        if self.base_address is None:
            print("Error: base_address is None during scanner setup.")
            return

        setup_scanners(self)

    def start_tracker_thread(self):
        self.stop_event = threading.Event()
        self.tracker_thread = threading.Thread(target=track_game, args=(self,))
        self.tracker_thread.start()

    def on_tool_click(self, tool_name):
        self.handle_manual_input()
        handle_tool_click(self, tool_name)

    def on_scenario_click(self, scenario_name):
        self.handle_manual_input()
        handle_scenario_click(self, scenario_name)

    def on_dot_click(self, location):
        print(f"Location dot clicked: {location}")

        dot, label = self.location_labels.get(location, (None, None))
        if dot and label:
            current_color = self.canvas.itemcget(dot, "fill")
            next_color = self.get_next_state_color(current_color)
            self.canvas.itemconfig(dot, fill=next_color)
            self.canvas.itemconfig(label, fill="white")
            self.manually_updated_locations[location] = next_color

        print(f"Location {location} manually set to {next_color}.")

    def get_next_state_color(self, current_color):
        color_order = ["red", "orange", "lightgreen", "grey"]
        next_index = (color_order.index(current_color) + 1) % len(color_order)
        return color_order[next_index]

    def sync_game_state(self):
        print("Sync button pressed. Syncing game state and resuming automatic updates.")
        self.resume_automatic_updates()

    def handle_manual_input(self):
        self.manual_input_active = True
        print("Manual input detected. Pausing automatic updates.")

    def populate_initial_canvases(self):
        print("Populating tools canvas with black and white images...")
        for tool_name, tool_info in self.tool_images.items():
            image_path = tool_items_bw[tool_name]["image_path"]
            new_image = self.load_image_cached(image_path)
            if new_image:
                position = tool_info['position']
                self.tools_canvas.itemconfig(position, image=new_image)
                tool_info['image'] = new_image

        print("Populating scenario canvas with black and white images...")
        for scenario_name, scenario_info in self.scenario_images.items():
            image_path = scenario_items_bw[scenario_name]["image_path"]
            new_image = self.load_image_cached(image_path)
            if new_image:
                position = scenario_info['position']
                self.scenario_canvas.itemconfig(position, image=new_image)
                scenario_info['image'] = new_image

        print("Canvases populated with initial black and white images.")

    def load_image_cached(self, image_path):
        if image_path not in self.image_cache:
            new_image = load_image(image_path)
            self.image_cache[image_path] = new_image
        return self.image_cache[image_path]

    def update_character(self, name, hp):
        print(f"Updating character: {name}, HP: {hp}")

        if name in self.manual_toggles:
            print(f"Skipping update for manually toggled character: {name}")
            return  # Skip updates for manually toggled characters

        is_active = hp > 0  # Consider a character active if their HP is greater than 0

        # Special case for specific characters that have a colored path
        if name in ["Claire", "Lisa", "Marie"] and 'color_image_path' in self.characters[name]:
            is_active = True  # Ensure maidens are always shown in color

        # Update the character image based on activity status
        update_character_image(self.characters_canvas, self.character_images, name, is_active)

    
    def update_map_based_on_tools(self):
        print("Updating map based on current tool states...")
        obtained_items = self.obtained_items

        for location, logic in LOCATION_LOGIC.items():
            if location in self.manually_updated_locations:
                print(f"Skipping update for manually updated location: {location}")
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
                self.canvas.itemconfig(label, fill="white")

        print("Map update complete.")

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

    def toggle_location_labels(self):
        self.location_labels_visible = not self.location_labels_visible
        for location, label in self.location_labels.items():
            if location not in CITIES:
                dot, text = label
                self.canvas.itemconfig(text, state=tk.NORMAL if self.location_labels_visible else tk.HIDDEN)

    def toggle_city_labels(self):
        self.city_labels_visible = not self.city_labels_visible
        for location, label in self.location_labels.items():
            if location in CITIES:
                dot, text = label
                self.canvas.itemconfig(text, state=tk.NORMAL if self.city_labels_visible else tk.HIDDEN)

    def resume_automatic_updates(self):
        self.manual_input_active = False
        print("Resuming automatic updates after manual input. Syncing game state.")
        
        if self.stop_event.is_set() or not self.tracker_thread.is_alive():
            self.stop_event.clear()
            self.start_tracker_thread()        


if __name__ == "__main__":
    root = tk.Tk()
    try:
        print("Starting Lufia2TrackerApp...")
        app = Lufia2TrackerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
