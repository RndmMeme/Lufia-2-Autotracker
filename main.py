# main.py

import re
import tkinter as tk
import os
from pathlib import Path
import logging
import ctypes, sys

from helpers.file_loader import load_image
from helpers.item_management import load_items_and_cache
from gui_setup import setup_interface, setup_canvases
from shared import LOCATIONS,tool_items_bw, scenario_items_bw, item_to_location, characters_bw, load_json_cached, generate_item_to_location_mapping, BASE_DIR, IMAGES_DIR, DATA_DIR, item_spells
from canvas_config import setup_tools_canvas, setup_scenario_canvas, setup_characters_canvas, setup_maidens_canvas
from event_handlers import handle_maiden_click, handle_tool_click, handle_scenario_click
from logic import LocationLogic
from auto.start_auto import startTracker
from auto.inventory_scan import PositionScanner, initialize_shared_variables, CharacterScanner

if sys.platform == "win32":
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)  # Minimize console

# Optional: Disable logs for EXE builds
import logging
if getattr(sys, 'frozen', False):
    logging.disable(logging.CRITICAL)

# Ensure the directory exists
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    
save_dir = "saves"
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# Configure logging
logging.basicConfig(
    filename=os.path.join(log_dir, 'app.log'),
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# Load item data (**moved to the beginning**)
item_spells = load_items_and_cache()  # This line should be at the beginning

class Lufia2TrackerApp:
    def __init__(self, root):
        
        self.root = root
        self.root.title("Lufia 2 Tracker")

        # Initialize shared variables in inventory_scan.py
        initialize_shared_variables()

        # Initialize essential attributes
        self.base_dir = BASE_DIR
        self.images_dir = IMAGES_DIR
        self.data_dir = DATA_DIR
        self.script_dir = Path(__file__).parent
        self.entries = {"Shop Item": [], "Spells": [], "Thief": []}
        self.image_cache = {}  # Image cache to avoid repeated loading
        
        
        # Initialize essential attributes
        self.map_address = os.path.join(IMAGES_DIR / "map", "map.jpg")
        self.LOCATIONS = LOCATIONS
        
        self.game_state = {}
        self.manually_updated_locations = {}
   
        
        self.location_character_images = {}
        self.item_spells = item_spells
        self.inventory = {}
        self.scenario_items = {}
        self.location_labels = {}
        self.label_visibility = {}
        self.tool_images = {}
        self.scenario_images = {}
        self.maiden_images = {}
        self.character_images = {}
        self.obtained_items = {}
        self.location_states = {location: "not_accessible" for location in LOCATIONS.keys()}
        self.location_labels_visible = True
        self.tool_items_bw = {}
        self.tool_items_c = {}
        self.scenario_items_bw = {}
        self.scenario_items_c = {}
        self.item_to_location = {}
        self.logic = None
        self.update_accessible_locations = True
        self.manual_input_active = False
        self.manually_updated_locations = {}
        self.manual_updates = {}
        self.manual_toggles = {}
        self.image_cache = {}
        self.characters = {}
        self.auto_tracker = startTracker()
        self.active_characters = set()  # To keep track of active characters
        self.previous_active_characters = set()
        self.cleared_dungeons = set()
        self.tracking_active = False
        self.game_running = False
        self.position_color_chosen = False
        self.capsule_sprite_pointer = None
        
        # Image cache to avoid repeated loading
        self.image_cache = {}

        # Load data
        self.load_data()
        
        # Setup interface
        self.setup_interface()

        # Initialize canvases here
        self.setup_canvases()
            
        self.process, self.base_address = self.auto_tracker.retrieve_base_address()
         
       # Initialize PositionScanner if process is valid
        if self.process and self.base_address:
            self.position_scanner = PositionScanner(self, self.process, self.base_address, self.canvas, self.map_image) # Stelle sicher, dass dies vorhanden ist.
            self.character_scanner = CharacterScanner(
            app=self,
            process=self.process,
            base_address=self.base_address,
            canvas=self.canvas,
            character_images=self.character_images,
            image_cache=self.image_cache,
            spoiler_log=None  # or provide one if needed
        )
        else:
            self.position_scanner = None
            self.character_scanner = None
            logging.error(f"PositionScanner not initialized due to process issues.")
       
        if self.process and self.base_address:
            rom_start_address = self.auto_tracker.read_rom_start_address(
            self.process,
            self.base_address + int(self.auto_tracker.emulator_config['pointer_base_address'], 16)
        )

            self.capsule_sprite_pointer = self.auto_tracker.compute_capsule_sprite_pointer(self.process, self.auto_tracker.emulator_config, rom_start_address)
            
        # Setup tools and scenario canvases
        tools_keys = list(tool_items_bw.keys())
        self.tools_canvas, self.tool_images = setup_tools_canvas(root, tools_keys, self.on_tool_click, self.image_cache)
        scenario_keys = list(scenario_items_bw.keys())
        self.scenario_canvas, self.scenario_images = setup_scenario_canvas(root, scenario_keys, item_to_location, self.on_scenario_click, self.image_cache)
        self.characters_canvas, self.character_images = setup_characters_canvas(self.root, self.characters, self.image_cache, self)
        self.maidens_canvas, self.maiden_images = setup_maidens_canvas(root, self.characters, characters_bw, self.image_cache, self, self.on_maiden_click)
        

        # Initialize location logic AFTER canvases are set up
        if self.canvas is not None and self.location_labels and self.maidens_images: # Check if all data is available
            self.location_logic = LocationLogic(self.script_dir, self.location_labels, self.canvas, self.maidens_images)
        else:
            if self.characters_canvas is None:
                logging.error("Characters canvas not initialized.")
            if not self.location_labels:
                logging.error("Location labels not initialized.")
            if not self.maidens_images:
                logging.error("Maidens images not initialized.")
            logging.error("Required data (canvas, location_labels, maidens_images) not initialized. Cannot create LocationLogic.")
            # Handle this error appropriately, e.g., exit the application or disable features
            return  # Exit init if data is not available

    def setup_interface(self):
        setup_interface(self)
        
    def load_data(self):
        try:
            self.locations_logic = load_json_cached(self.data_dir / "locations_logic.json")
            #logging.info("Loaded locations logic data.")
        except Exception as e:
            logging.error(f"Failed to load locations logic data: {e}")

        try:
            self.characters = load_json_cached(self.data_dir / "characters.json")
            #logging.info("Loaded characters data.")
        except Exception as e:
            logging.error(f"Failed to load characters data: {e}")

        try:
            self.characters_bw = load_json_cached(self.data_dir / "characters_bw.json")
            #logging.info("Loaded characters_bw data.")
        except Exception as e:
            logging.error(f"Failed to load characters_bw data: {e}")

        try:
            self.item_to_location = generate_item_to_location_mapping(self.locations_logic)
            #logging.info("Generated item to location mapping.")
        except Exception as e:
            logging.error(f"Failed to generate item to location mapping: {e}")

    def setup_canvases(self):
        setup_canvases(self)

    def on_tool_click(self, tool_name):
        handle_tool_click(self, tool_name)

    def on_scenario_click(self, scenario_name):
        handle_scenario_click(self, scenario_name)
        
    def on_maiden_click(self, maiden_name):
        handle_maiden_click(self, maiden_name)   

    def on_dot_click(self, location):
        dot = self.location_labels.get(location)
        if dot:
            current_color = self.canvas.itemcget(dot, "fill")
            next_color = self.get_next_state_color(current_color)
            self.canvas.itemconfig(dot, fill=next_color)
            self.manually_updated_locations[location] = next_color

    def get_next_state_color(self, current_color):
        color_order = ["red","lightgreen", "grey"]
        next_index = (color_order.index(current_color) + 1) % len(color_order)
        return color_order[next_index]

    def handle_manual_input(self):
        self.manual_input_active = True
        
    def load_image_cached(self, image_path, size=None):
        if image_path not in self.image_cache:
            new_image = load_image(image_path)
            self.image_cache[image_path] = new_image
        return self.image_cache[image_path]

    def reset(self):
        self.reset_handler.reset_game_state()

    def save(self):
        self.save_handler.save_game_state()
        
    def load(self):
        self.load_handler.load_game_state()
        

    def on_resize(self, event):
        pass

    def on_closing(self):
        spoiler_path = Path(DATA_DIR) / "spoiler_temp.json"
        if os.path.exists(spoiler_path):
            os.remove(spoiler_path)
        emulator_config_path = Path(DATA_DIR) / "current_emulator_config.json"
        if os.path.exists(emulator_config_path):
            os.remove(emulator_config_path)
        # Remove the temp file if it exists
            
        self.root.destroy()
 

if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = Lufia2TrackerApp(root)
        root.mainloop()
        app.reset()
        app.load()
        app.save()
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        try:
            with open("error_log.txt", "a", encoding="utf-8") as error_file: # Unicode Encoding
                error_file.write(f"Unhandled exception: {e}\n")
        except UnicodeEncodeError:
            with open("error_log.txt", "a", encoding="utf-8", errors="replace") as error_file: # Unicode Encoding mit Fehlerbehandlung
                error_file.write(f"Unhandled exception: {e}\n")
