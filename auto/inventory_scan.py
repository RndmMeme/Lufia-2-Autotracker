# inventory_scan.py

import os
from sre_constants import IN
import tkinter as tk
import canvas_config
from shared import LOCATION_LOGIC, load_json_cached, DATA_DIR, COLORS, ALWAYS_ACCESSIBLE_LOCATIONS, CITIES, current_config, emulator_addresses
from helpers.file_loader import load_image
from helpers.resalo import Save, Reset
from canvas_config import load_image_cached
import gui_setup
import logging
import pymem
from logic import LocationLogic
import traceback
import logging
import re
import json
from pathlib import Path
from event_handlers import handle_tool_click, handle_scenario_click, update_tool_image, update_scenario_image


CHARACTER_SLOT_ADDRESSES = None
INVENTORY_START = None
INVENTORY_END = None
SCENARIO_START = None
SCENARIO_END = None

def initialize_shared_variables():
    global CHARACTER_SLOT_ADDRESSES, INVENTORY_START, INVENTORY_END, SCENARIO_START, SCENARIO_END
    
    emulator_addresses = load_json_cached(DATA_DIR / "emulator_addresses.json")
    default_emulator_key = "snes9x-x64.exe"

    character_slots_default = None
    inventory_range_default = ['0', '0']
    scenario_range_default = ['0', '0']

    if default_emulator_key in emulator_addresses:
        if emulator_addresses[default_emulator_key]:
            first_emulator_data = emulator_addresses[default_emulator_key][0]
            character_slots_default = first_emulator_data.get("character_slots")
            inventory_range_default = first_emulator_data.get("inventory_range", ['0', '0'])
            scenario_range_default = first_emulator_data.get("scenario_range", ['0', '0'])
        else:
            logging.warning(f"Keine Emulator-Konfigurationen für Prozess '{default_emulator_key}' in emulator_addresses.json gefunden.")
    else:
        logging.warning(f"Prozessname '{default_emulator_key}' nicht in emulator_addresses.json gefunden.")

    current_config = load_json_cached(DATA_DIR / "current_emulator_config.json")

    character_slots = current_config.get("character_slots", character_slots_default)
    inventory_range = current_config.get("inventory_range", inventory_range_default)
    scenario_range = current_config.get("scenario_range", scenario_range_default)


    CHARACTER_SLOT_ADDRESSES = character_slots
    INVENTORY_START = int(inventory_range[0], 16)
    INVENTORY_END = int(inventory_range[1], 16)
    SCENARIO_START = int(scenario_range[0], 16)
    SCENARIO_END = int(scenario_range[1], 16)

# Mapping of byte values to character names
CHARACTER_BYTE_MAPPING = {
    0x00: "Maxim",
    0x01: "Selan",
    0x02: "Guy",
    0x03: "Artea",
    0x04: "Tia",
    0x05: "Dekar",
    0x06: "Lexis",
    0xFF: "Empty"
}

def save_to_temp(app):
    '''Save scan and track data temporarily for cached comparison'''
    try:
        # Check if progress_temp.json exists; if not, create it
        progress_path = Path(DATA_DIR) / "progress_temp.json"
        
        if not progress_path.exists():
            progress_path.touch()

        # Use the Save class to retrieve all data
        save_instance = Save(app)  # Assuming `app` is available
        all_data = save_instance.get_all_canvas_data()

        # Save data to progress_temp.json
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=4)
        
        logging.info(f"Debug: Data saved to {progress_path}")

    except Exception as e:
        logging.error(f"Error in save_to_temp: {e}")

class InventoryScanner:
    def __init__(self, app, tools_canvas, tool_images, location_labels):
        self.app = app
        self.tools_canvas = tools_canvas
        self.tool_images = tool_images
        self.tool_items = load_json_cached(DATA_DIR / 'tool_items.json')
        self.location_labels = location_labels
        self.location_logic = LocationLogic(self.app.script_dir, self.location_labels, self.app.canvas, self.app.maiden_images) # LocationLogic Instanz erstellen
        
    def scan_inventory(self, process, base_address, obtained_items):
        new_obtained_items = {}
        inventory_data = process.read_bytes(base_address + INVENTORY_START, INVENTORY_END - INVENTORY_START)
        memory_value = process.read_bytes(base_address + SCENARIO_START, SCENARIO_END - SCENARIO_START + 1)
        reversed_memory_value = memory_value[::-1]
        binary_string = ''.join(f'{byte:08b}' for byte in reversed_memory_value)
        
        for tool_name, tool_info in self.tool_items.items():
            if tool_info["type"] == "normal":
                obtained_value = int(tool_info["obtained_value"], 16)
                item_bytes = obtained_value.to_bytes(2, byteorder='little')
            
                if item_bytes in inventory_data:
                    if tool_name in self.app.obtained_items and self.app.tool_images[tool_name]["is_colored"]:
                        new_obtained_items[tool_name] = True #sicherstellen, das es im neuen dict vorhanden ist.
                    else:
                        new_obtained_items[tool_name] = True
                        handle_tool_click(self.app, tool_name)
                        self.app.root.update()
                else:
                    if tool_name in self.app.obtained_items:
                        del self.app.obtained_items[tool_name]
                        update_tool_image(self.app,tool_name, obtained=False)
                       
            
        for tool_name, tool_info in self.tool_items.items():
            if tool_info["type"] == "special":
                obtained_value_bin = tool_info["obtained_value"].replace(' ', '')
                for bit_position, bit_value in enumerate(binary_string):
                    if bit_value == '1':
                        obtained_index = len(binary_string) - bit_position
                        if len(obtained_value_bin) >= obtained_index:
                            if obtained_value_bin[-obtained_index] == '1':
                                if tool_name in self.app.obtained_items and self.app.tool_images[tool_name]["is_colored"]:
                                    new_obtained_items[tool_name] = True
                                else:
                                    new_obtained_items[tool_name] = True
                                    handle_tool_click(self.app, tool_name)
                                    self.app.root.update()
                                break # Hier wird die Schleife beendet, sobald ein Match gefunden wurde
                            else:
                                if tool_name in self.app.obtained_items:
                                    del self.app.obtained_items[tool_name]
                                    update_tool_image(self.app,tool_name, obtained=False)
                        else:
                            logging.error(f"len(obtained_value_bin) < obtained_index") #Debug
            
       
        inventory_changed = not new_obtained_items.keys() == obtained_items.keys()
        obtained_items.update(new_obtained_items)
        self.update_locations(obtained_items)
        return inventory_changed   
        
    def update_locations(self, obtained_items):
        self.location_logic.update_accessible_locations(obtained_items) # LocationLogic Methode aufrufen
        

class ScenarioScanner:
    def __init__(self, app, scenario_canvas, scenario_images, location_labels):
        self.app = app
        self.scenario_canvas = scenario_canvas
        self.scenario_images = scenario_images
        self.scenario_items = load_json_cached(DATA_DIR / 'scenario_items.json')
        self.location_labels = location_labels
        self.location_logic = LocationLogic(self.app.script_dir, self.location_labels, self.app.canvas, self.app.maiden_images) # LocationLogic Instanz erstellen
        
    def scan_scenario(self, process, base_address, obtained_items):
        new_obtained_items = {}
        memory_value = process.read_bytes(base_address + SCENARIO_START, SCENARIO_END - SCENARIO_START + 1)
        reversed_memory_value = memory_value[::-1]
        binary_string = ''.join(f'{byte:08b}' for byte in reversed_memory_value)

        for scenario_name, scenario_info in self.scenario_items.items():
            for bit_position, bit_value in enumerate(binary_string):
                if bit_value == '1':
                    obtained_index = len(binary_string) - bit_position
                    if scenario_name in self.scenario_items:
                        obtained_value_bin = scenario_info["obtained_value"].replace(' ', '')
                        if len(obtained_value_bin) >= obtained_index:
                            if obtained_value_bin[-obtained_index] == '1':
                                if scenario_name in self.app.obtained_items and self.app.scenario_images[scenario_name]["is_colored"]:
                                    new_obtained_items[scenario_name] = True
                                else:
                                    new_obtained_items[scenario_name] = True
                                    handle_scenario_click(self.app, scenario_name)
                                    self.app.root.update()
                                break #Break here
                            else:
                                if scenario_name in self.app.obtained_items:
                                    del self.app.obtained_items[scenario_name]
                                    update_scenario_image(self.app, scenario_name, obtained=False)
                                    
        scenario_changed = not new_obtained_items.keys() == obtained_items.keys()
        obtained_items.update(new_obtained_items)
        self.update_locations(obtained_items)
        return scenario_changed

    def update_locations(self, obtained_items):
        self.location_logic.update_accessible_locations(obtained_items) # LocationLogic Methode aufrufen
        
        
class CharacterScanner:
    def __init__(self, app, process, base_address, canvas, character_images, image_cache, spoiler_log=None):
        self.app = app
        self.process = process
        self.base_address = base_address
        self.canvas = canvas
        self.character_images = character_images
        self.image_cache = image_cache
        self.active_characters = set()  # Track currently active characters
        self.spoiler_temp = load_json_cached(DATA_DIR / "spoiler_temp.json")  # Spoiler Log hinzufügen
        self.spoiler_log = spoiler_log
        self.name_mapping = load_json_cached(DATA_DIR / "location_name_mapping.json")
        self.capsules = load_json_cached(DATA_DIR / "characters.json")
        self.capsule_sprite_pointer = app.capsule_sprite_pointer
        
        logging.debug(f"Debug: CharacterScanner initialized with base_address: {base_address}") # Debug hinzufügn

    def scan(self):
        
        if self.base_address is None:
            logging.error("Error: base_address is None in CharacterScanner.scan")
            return

        try:
            
            self.active_characters.clear()  # Clear the active characters set
            for slot_index, offset in enumerate(CHARACTER_SLOT_ADDRESSES):
                address = self.base_address + int(offset, 16)
                
                try:
                    byte_value = self.process.read_bytes(address, 1)
                    character_id = byte_value[0]
                    character_name = CHARACTER_BYTE_MAPPING.get(character_id, "Unknown")
                    
                    if character_name != "Unknown" and character_name != "Empty":
                        self.active_characters.add(character_name)  # Add to active characters set
                        gui_setup.update_character_image(self.canvas, self.character_images, character_name, True)
                except Exception as e:
                    logging.error(f"Unexpected error reading character slot at address 0x{address:X}: {e}")

           
            for character_name in self.character_images:
                if character_name not in self.active_characters:
                    gui_setup.update_character_image(self.canvas, self.character_images, character_name, False)
                     # Überprüfung der Belohnungen im Spoiler Log
            if self.spoiler_temp and hasattr(self.app, 'cleared_dungeons'):
                
                for entry in self.spoiler_temp:
                    reward = entry.get("item")
                    spoiler_location = entry.get("location")  # Speichere den Spoiler-Namen
                    location = self.translate_location_name(spoiler_location, self.name_mapping)  # Übersetze den Spoiler-Namen
                    
                    if reward in self.character_images and location in self.app.cleared_dungeons:
                        gui_setup.assign_character_to_location(self.app, reward, location)
                    
             # Hervorhebung anpassen (nach dem Spoiler-Abgleich)
            for character_name in self.character_images:
                is_active = character_name in self.active_characters
                gui_setup.update_character_image(self.canvas, self.character_images, character_name, is_active)
                
        except Exception as e:
            logging.error(f"Error scanning character slots: {e}")
                
    def scan_capsule_monsters(self):
        try:
            config = load_json_cached(DATA_DIR / "current_emulator_config.json")
            start_address = int(config["capsule_slots_start"][0], 16) + self.base_address
            end_address = int(config["capsule_slots_end"][0], 16) + self.base_address

            monster_names = list(self.capsules.keys())[10:]  # Skipping first 10 regular characters

            expected_sprite_hex_values = {
                "Foomy S": "4600",
                "Shaggy": "A502",
                "Hard Hat": "4305",  
                "Red Fish": "AF07",  
                "Myconido": "580A",  
                "Raddisher": "0B0D",  
                "Armor Dog": "880F"   
            }

            # Step 1: Build mapping of hex sprite value → position in sprite memory
            sprite_value_to_position = {}
            for i in range(7):  # 7 capsule slots
                sprite_address = self.capsule_sprite_pointer + (i * 10)
                sprite_bytes = self.process.read_bytes(sprite_address, 2)
                sprite_hex = f"{sprite_bytes[0]:02X}{sprite_bytes[1]:02X}"
                capsule_name = monster_names[i]  # based on order
                sprite_value_to_position[sprite_hex] = i
                
                
            # Step 2: Check obtained capsules in memory range
            for address in range(start_address, end_address + 1):
                byte_value = self.process.read_bytes(address, 1)
                if byte_value[0] != 0x00:
                    offset = address - start_address
                    if offset < len(monster_names):
                        monster_name = monster_names[offset]
                        self.active_characters.add(monster_name)
                    else:
                        logging.warning(f"Offset {offset} out of range for capsule monsters.")

            # Step 3: Update character images for obtained capsules
            for monster_name in monster_names:
                is_active = monster_name in self.active_characters
                gui_setup.update_character_image(self.canvas, self.character_images, monster_name, is_active)

            # Step 4: Assign characters to locations based on spoiler info
            if self.spoiler_temp and hasattr(self.app, 'cleared_dungeons'):
                for entry in self.spoiler_temp:
                    reward = entry.get("item")
                    spoiler_location = entry.get("location")
                    location = self.translate_location_name(spoiler_location, self.name_mapping)

                    hex_value = expected_sprite_hex_values.get(reward)
                    if not hex_value:
                        continue  # Sprite not tracked

                    # Check if that hex_value is found in capsule pointer map
                    capsule_position = sprite_value_to_position.get(hex_value.upper())
                    if capsule_position is None:
                        continue  # Not currently mapped

                    # Now check if that capsule position has a non-zero value = obtained
                    capsule_memory_address = start_address + capsule_position
                    value = self.process.read_bytes(capsule_memory_address, 1)[0]
                    if value != 0x00:
                        monster_name = monster_names[capsule_position]
                        gui_setup.assign_character_to_location(self.app, monster_name, location)

        except Exception as e:
            logging.error(f"Error scanning capsule monsters: {e}")

            
    def translate_location_name(self, spoiler_name, mapping):
        for internal_name, mapped_spoiler_name in mapping.items():
            if mapped_spoiler_name == spoiler_name:
                return internal_name
        return spoiler_name  # Gibt den Spoiler-Namen zurück, wenn keine Übersetzung gefunden wird


class MaidenScanner:
    def __init__(self, app, maidens_canvas, maiden_images, spoiler_log=None):
        self.app = app
        self.maidens_canvas = maidens_canvas
        self.maiden_images = maiden_images
        self.spoiler_temp = load_json_cached(DATA_DIR / "spoiler_temp.json")
        self.name_mapping = load_json_cached(DATA_DIR / "location_name_mapping.json")
        
    def update_maidens(self):
        
        try:
            # 1. Spoiler-Log zuerst durchsuchen
            maiden_locations = {}
            maiden_mapping = {"Clare": "Claire", "Lisa": "Lisa", "Marie": "Marie"} # Mapping für Maiden-Namen
            
            for spoiler_name, internal_name in maiden_mapping.items():
                
                for entry in self.spoiler_temp:
                    if entry["item"] == spoiler_name:
                        maiden_locations[internal_name] = self.translate_location_name(entry["location"], self.name_mapping)
                        break # Beende die innere Schleife, sobald die Maiden gefunden wurde
            
            # 2. Fehlerbehandlung für Spoiler-Log-Daten
            if not maiden_locations:
                logging.error("Keine Maiden-Locations im Spoiler-Log gefunden.")
                return
            # 3. Canvas-Initialisierung überprüfen
            if not self.maiden_images:
                logging.error("Maiden-Canvas nicht initialisiert.")
                return
            # 4. Fehlerbehandlung für Canvas-Daten
            for maiden_name in ["Claire", "Lisa", "Marie"]:
                if maiden_name not in self.maiden_images:
                    logging.error(f"Maiden {maiden_name} nicht auf dem Canvas gefunden.")
                    return
            # 5. Location-Prüfung und obtained_items-Aktualisierung
            for maiden_name, location in maiden_locations.items():
                if location in self.app.cleared_dungeons:
                    if maiden_name not in self.app.obtained_items:
                        self.app.on_maiden_click(maiden_name)  
                else:
                    logging.error(f"{maiden_name} Not found")

        except Exception as e:
            logging.error(f"Fehler bei der Aktualisierung der Maidens: {e}")

    def translate_location_name(self, spoiler_name, mapping):
        for internal_name, mapped_spoiler_name in mapping.items():
            if mapped_spoiler_name == spoiler_name:
                return internal_name
        return spoiler_name
            
class SpoilerScanner:
    def __init__(self, app, process, base_address):
        self.app = app
        self.process = process
        self.base_address = base_address
        self.spoiler_log_start_address, self.spoiler_log_end_address = self.calculate_spoiler_log_addresses()
        
    def calculate_spoiler_log_addresses(self):
        """Calculates the spoiler log start and end addresses dynamically."""
        try:
            current_config = load_json_cached(DATA_DIR / "current_emulator_config.json")
            pointer_base_address = self.base_address + int(current_config["pointer_base_address"], 16)
            spoiler_log_offset_start = int(current_config["spoiler_log_offset_start"], 16)
            spoiler_log_offset_end = int(current_config["spoiler_log_offset_end"], 16)

            # Read the 4-byte array at the pointer address (little endian)
            shop_table_pointer_bytes = self.process.read_bytes(pointer_base_address, 4)
            shop_table_pointer_int = int.from_bytes(shop_table_pointer_bytes, byteorder='little')

            # Calculate the spoiler log start and end addresses
            spoiler_log_start_address = shop_table_pointer_int + spoiler_log_offset_start
            spoiler_log_end_address = shop_table_pointer_int + spoiler_log_offset_end

            return spoiler_log_start_address, spoiler_log_end_address

        except Exception as e:
            logging.error(f"Error calculating spoiler log addresses: {e}")
            return None, None

    def scan_spoiler_log(self):
        if self.spoiler_log_start_address is None or self.spoiler_log_end_address is None:
            logging.error("Error: Spoiler log addresses not calculated.")
            return None

        # Speicherbereich lesen
        try:
            memory_data = self.process.read_bytes(self.spoiler_log_start_address, self.spoiler_log_end_address - self.spoiler_log_start_address)
            
        except Exception as e:
            logging.error(f"Error: Memory read failed: {e}")
            return None
        
        # Daten als ASCII-Text dekodieren
        try:
            spoiler_text = memory_data.decode("ascii", errors="ignore") # ASCII-Dekodierung verwenden
        except UnicodeDecodeError as e:
            logging.error(f"Error decoding memory data: {e}")
            return None

        # "ITEM LOCATIONS..." suchen
        start_index = spoiler_text.find("ITEM LOCATIONS")
        if start_index == -1:
            logging.error("Debug: ITEM LOCATIONS not found.")
            return None

        # Daten nach "ITEM LOCATIONS..." extrahieren
        spoiler_text_after_item_locations = spoiler_text[start_index + len("ITEM LOCATIONS"):]
        
        # Daten extrahieren und parsen
        parsed_data = self.parse_spoiler_text(spoiler_text_after_item_locations)
        self.save_to_temp_json(parsed_data)

        return parsed_data

    def parse_spoiler_text(self, raw_text):
        
        # Assuming raw_text is already a string (decoded)
        logging.info(f"Debug: Raw decoded text:\n{raw_text[:500]}")  # Display first 500 chars for sanity check

        # Remove header like "ITEM LOCATIONS"
        text = re.sub(r"ITEM LOCATIONS", "", raw_text).strip()
        
        # Fix spacing between multi-word items/locations (e.g., "BombRuby Cave" -> "Bomb Ruby Cave")
        text = re.sub(r"([a-zA-Z])([A-Z])", r"\1 \2", text)
        
        # Split the text into potential triplets based on word boundaries
        words = re.findall(r"[A-Za-z\s]+", text)

        
        # Group the words into triplets
        triplets = []
        for i in range(0, len(words) - 2, 3):
            triplets.append((words[i].strip(), words[i + 1].strip(), words[i + 2].strip()))

        logging.info(f"Debug: Item-Location-Boss triplets: {triplets[:10]}")  # Show first 10 triplets for sanity check

        # Structured data where we will store item, location, and boss
        structured_data = []

        # Now categorize each group: item, location, boss
        for item, location, boss in triplets:
            structured_data.append({
                "item": item,
                "location": location,
                "boss": boss
            })

        logging.info(f"Debug: Parsed data: {structured_data[:5]}")  # Show first 5 entries of parsed data for inspection

        return structured_data

    def save_to_temp_json(self, data):
        try:
            # Daten in temp.json speichern
            spoiler_path = Path(DATA_DIR) / "spoiler_temp.json"
            with open(spoiler_path, "w") as f:
                json.dump(data, f, indent=4)
            
        except Exception as e:
            logging.error(f"Error in save_to_temp_json: {e}")
            
class LocationScanner:
    def __init__(self, app, canvas, location_labels):
        self.app = app
        self.canvas = canvas
        self.dungeon_flags = None
        self.location_logic = LocationLogic(self.app.script_dir, self.app.location_labels, self.app.canvas, self.app.maiden_images) # LocationLogic Instanz erstellen
        self.locations = load_json_cached(DATA_DIR / 'locations.json')
        self.locations_logic = load_json_cached(DATA_DIR / "locations_logic.json")
        self.location_labels = location_labels
        
    def scan_locations(self, process, base_address):
        """
        Scans the locations and updates the canvas based on user input, game data, and spoiler log.
        """     
        cleared_dungeons =self.get_game_cleared_locations(process, base_address)
        self.app.cleared_dungeons = cleared_dungeons
        
    def get_game_cleared_locations(self, process, base_address):
        """
        Liest die Zustände der Dungeons aus dem Spielspeicher (Byte-weise).
        """
        current_config = load_json_cached(DATA_DIR / "current_emulator_config.json")
        dungeon_flag_start = int(current_config["dungeon_flag_start"], 16)
        dungeon_flag_end = int(current_config["dungeon_flag_end"], 16)

        if current_config["name"] == "Snes9x 1.62.3":
            self.dungeon_flags = load_json_cached(DATA_DIR / "dungeon_flags_snes9x.json")
        elif current_config["name"] == "Snes9x 1.62.3-nwa":
            self.dungeon_flags = load_json_cached(DATA_DIR / "dungeon_flags_snes9x-nwa.json")

        dungeon_flags = self.dungeon_flags
        cleared_dungeons = set()

        # Speicherbereich lesen
        memory_values = process.read_bytes(base_address + dungeon_flag_start, dungeon_flag_end - dungeon_flag_start + 1)

        # Bit-Flags prüfen
        for address_str, dungeons in dungeon_flags.items():
            address = int(address_str, 16)
            # Relativen Offset berechnen
            relative_offset = address - dungeon_flag_start
            # Speicherwert aus dem gelesenen Bereich extrahieren
            memory_value = memory_values[relative_offset]
            # Speicherwert in Binär umwandeln
            binary_string = bin(memory_value)[2:].zfill(8)

            for dungeon in dungeons:
                location = dungeon["location"]
                flag = int(dungeon["flag"], 16)
                flag_binary = bin(flag)[2:].zfill(8)

                # Bit-Position bestimmen
                for i in range(8):
                    if flag_binary[7 - i] == '1':
                        bit_position = i
                        break

                # Bedingungen für den Abschluss prüfen
                accessible = self.location_logic.is_location_accessible(self.app.obtained_items, location)


                # Flag im Speicher prüfen
                if accessible and binary_string[7 - bit_position] == '1':
                    cleared_dungeons.add(location)
                    self.location_logic.mark_location(location, accessible=True, cleared=True)
                else:
                    # LocationLogic.update_accessible_locations() aufrufen
                    self.app.location_logic.update_accessible_locations(self.app.obtained_items)

                    
        return cleared_dungeons
    
class PositionScanner:
    
    def __init__(self, app, process, base_address, canvas, map_image):
        self.app = app
        self.process = process
        self.base_address = base_address
        self.canvas = canvas
        self.map_image = map_image
        self.player_position = None
        self.point_id = None
        self.x_offset = 0  # Anpassen
        self.y_offset = 0  # Anpassen
        self.x_scale = 1  # Anpassen
        self.y_scale = 1  # Anpassen
        self.player_dot_color = "orange"  # Standard
        #self.blink_state = True
        
    def scan_player_position(self):
        
        current_config = load_json_cached(DATA_DIR / "current_emulator_config.json")
        transport_flag = int(current_config["transport_flag"], 16)
        ship_x_fast_address = int(current_config["ship_x_fast_address"], 16)
        ship_x_slow_address = int(current_config["ship_x_slow_address"], 16)
        ship_y_fast_address = int(current_config["ship_y_fast_address"], 16)
        ship_y_slow_address = int(current_config["ship_y_slow_address"], 16)
        walk_x_fast_address = int(current_config["walk_x_fast_address"], 16)
        walk_x_slow_address = int(current_config["walk_x_slow_address"], 16)
        walk_y_fast_address = int(current_config["walk_y_fast_address"], 16)
        walk_y_slow_address = int(current_config["walk_y_slow_address"], 16)
        
        try:
            # Transportmodus lesen
            transport_mode_address = self.base_address + transport_flag
            transport_mode = self.process.read_bytes(transport_mode_address, 1)[0]

            # Koordinatenadressen basierend auf dem Transportmodus auswählen
            if transport_mode == 0xFF :  # Transportmodus (Schiff, U-Boot, Luftschiff)
                x_fast_address = self.base_address + ship_x_fast_address
                x_slow_address = self.base_address + ship_x_slow_address
                y_fast_address = self.base_address + ship_y_fast_address
                y_slow_address = self.base_address + ship_y_slow_address
            elif transport_mode == 0x00:  # Laufmodus
                x_fast_address = self.base_address + walk_x_fast_address
                x_slow_address = self.base_address + walk_x_slow_address
                y_fast_address = self.base_address + walk_y_fast_address
                y_slow_address = self.base_address + walk_y_slow_address
            else:
                logging.info("Unbekannter Transportmodus:", transport_mode)
                return

            # Koordinaten lesen
            x_fast = self.process.read_bytes(x_fast_address, 1)[0]
            x_slow = self.process.read_bytes(x_slow_address, 1)[0]
            y_fast = self.process.read_bytes(y_fast_address, 1)[0]
            y_slow = self.process.read_bytes(y_slow_address, 1)[0]

            # Koordinaten kombinieren
            x = (x_slow << 8) | x_fast
            y = (y_slow << 8) | y_fast

         
            # **Check the actual game world size**
            map_size_x = 4096  # Korrigiert
            map_size_y = 4096  # Korrigiert

            # **Ensure we don't go out of bounds**
            x = max(0, min(x, map_size_x))
            y = max(0, min(y, map_size_y))

            # Berechne Skalierung mit den Canvas gespeicherten Werten
            scale_factor_x = self.canvas.scale_factor_x  # Korrigiert
            scale_factor_y = self.canvas.scale_factor_y  # Korrigiert

            # Umrechnung in die Bildschirmposition
            screen_x = x * scale_factor_x
            screen_y = y * scale_factor_y

            # Berechnung des Offsets (zentrieren in der Canvas)
            canvas_x_offset = 0  # Where the map starts on the UI
            canvas_y_offset = 0  # Where the map starts on the UI

            # Final Position auf der Karte
            screen_x += canvas_x_offset
            screen_y += canvas_y_offset

            self.player_position = (screen_x, screen_y)
            self.update_point(self.player_position)

        except Exception as e:
            logging.error(f"Fehler beim Scannen der Spielerposition: {e}")

    def choose_predefined_color(self):
        """Öffnet ein Popup-Fenster mit vordefinierten Farben."""
        top = tk.Toplevel(self.app.root)
        top.title("Farbe wählen")
        top.geometry("200x75") # Fenstergröße anpassen

        colors = ["red", "green", "blue", "yellow", "purple", "orange", "magenta", "cyan"]
        for i, color in enumerate(colors):
            # Berechne die Breite basierend auf der Textlänge
            width = len(color) + 2  # Füge etwas zusätzlichen Platz hinzu

            button = tk.Button(top, text=color, bg=color, command=lambda c=color: self.set_player_color(c, top), width=width, height=1)
            button.grid(row=i // 4, column=i % 4, padx=2, pady=2)

        # Konfiguriere alle Spalten, um die gleiche Breite zu haben
        for j in range(4):  # Angenommen, du hast 4 Spalten
            top.grid_columnconfigure(j, weight=1)
            
    def set_player_color(self, color, top):
        """Setzt die Player-Farbe und schließt das Popup-Fenster."""
        self.player_dot_color = color
        self.scan_player_position()
        top.destroy()
    '''
    def blink(self):
        """Lässt den Player-Punkt blinken."""
        if hasattr(self, "player_dot"):
            if self.blink_state:
                fill_color = self.player_dot_color
            else:
                fill_color = "white"  # Oder eine andere Farbe
                
            self.canvas.itemconfig(self.player_dot, fill=fill_color)
            self.blink_state = not self.blink_state
        self.app.root.after(800, self.blink)  # Blinken alle 500 Millisekunden
    '''
    def update_point(self, point, fill=None, tag='player_dot'):
        """Plots or moves a point on the canvas as an inverted triangle."""
        if not fill:
            fill = self.player_dot_color

        triangle_width = 10  # Breite des Dreiecks (anpassen)
        triangle_height = 10 # Höhe des Dreiecks (anpassen)

        # find the location of the point on the canvas
        x, y = point

        x_screen = x
        y_screen = y

        # Koordinaten für das invertierte Dreieck (Spitze nach unten)
        x1 = x_screen
        y1 = y_screen + triangle_height  # Spitze des Dreiecks unten
        x2 = x_screen - (triangle_width / 2)
        y2 = y_screen
        x3 = x_screen + (triangle_width / 2)
        y3 = y_screen

        # if the tag exists, then move the point, else create the point
        point_ids = self.canvas.find_withtag(tag)

        if point_ids:
            point_id = point_ids[0]
            self.canvas.coords(point_id, x1, y1, x2, y2, x3, y3)
            self.canvas.itemconfig(point_id, fill=fill, outline=fill)
            self.point_id = point_id
            
        else:
            self.player_dot = self.canvas.create_polygon(x1,
                                                        y1,
                                                        x2,
                                                        y2,
                                                        x3,
                                                        y3,
                                                        outline=fill,
                                                        fill=fill,
                                                        tag=tag)
        #self.blink()
        self.point_id = self.player_dot
        
           
    def show_position(self):
        self.scan_player_position()
        