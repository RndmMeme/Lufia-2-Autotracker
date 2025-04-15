#game_tracking.py

import pymem
import time
import logging
import auto.inventory_scan
from auto.inventory_scan import InventoryScanner, ScenarioScanner, CharacterScanner, MaidenScanner, SpoilerScanner, LocationScanner, PositionScanner, CHARACTER_SLOT_ADDRESSES, CHARACTER_BYTE_MAPPING, save_to_temp
from canvas_config import update_character_image, setup_characters_canvas, setup_tools_canvas, setup_scenario_canvas
from shared import tool_items_bw, tool_items_c, scenario_items_bw, scenario_items_c, current_config
import shared
import tkinter as tk
import threading
from tkinter import messagebox
from helpers.optics import Banner
from helpers.resalo import SoftReset




LIGHT_SCAN_INTERVAL = 5000  # Light scan every 5 seconds

def sync_with_game(menu_frame, app):
    """Syncs the game state with the tracker once."""
    try:
        emulator_found = app.auto_tracker.start_tracking(app.light_scan_queue, app)
        if emulator_found:
            
            # Stelle sicher, dass die Konfigurationsdatei vorhanden ist
            if not app.auto_tracker.get_emulator_config():
                # Erstelle die Konfigurationsdatei, falls sie nicht existiert
                emulator_data = app.auto_tracker.get_emulator_config()
                if not emulator_data:
                    emulator_data = app.auto_tracker.get_emulator_config() # get_emulator_config aufrufen
                if emulator_data:
                    app.auto_tracker.create_emulator_config(emulator_data)

            game_running = app.auto_tracker.is_game_running(app.auto_tracker.stop_event, app.auto_tracker.get_emulator_config(), app.light_scan_queue)
            if game_running:
                app.game_running = True
                process, base_address = app.auto_tracker.retrieve_base_address()
                
                SoftReset(app)
                
                
                auto.inventory_scan.initialize_shared_variables()
                
                # scanning spoiler log
                spoiler_scanner = SpoilerScanner(app, process, base_address)  # Korrekte Instanziierung
                spoiler_scanner.scan_spoiler_log()  # Korrekter Methodenaufruf
                
                # scanning inventory
                inventory_scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
                obtained_items = {}  # Leeres Set für gefundene Items
                inventory_scanner.scan_inventory(process, base_address, obtained_items)
                
                # scanning scenario
                scenario_scanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
                scenario_scanner.scan_scenario(process, base_address, obtained_items)
                
                # Gefundene Items speichern
                app.obtained_items = obtained_items
               
                # scanning map
                location_scanner = LocationScanner(app, app.canvas, app.location_labels)
                location_scanner.scan_locations(process, base_address)
             
                # scanning characters
                
                character_scanner = CharacterScanner(app, process, base_address, app.characters_canvas, app.character_images, app.image_cache)
                character_scanner.scan()
                character_scanner.scan_capsule_monsters()
            
                maiden_scanner = MaidenScanner(app, app.maidens_canvas, app.maiden_images) # MaidenScanner erstellen, wenn Maidens initialisiert sind
                maiden_scanner.update_maidens()
             
                position_scanner = PositionScanner(app, process, base_address, app.canvas, app.map_image)
                position_scanner.show_position()
                
                Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=108, y_offset=57)  # Adjusted
                save_to_temp(app)
            else:
                app.game_running = False
                Banner(app.root, message="Game not running", bg_color="#F08080", x_offset=108, y_offset=57)

        else:
            logging.error("Debug: Emulator not found, stopping sync.")
            app.game_running = False
            Banner(app.root, message="Emulator not found", bg_color="#F08080", x_offset=108, y_offset=57)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=108, y_offset=57)

def sync_tools(menu_frame, app):
    try:
        emulator_found = app.auto_tracker.start_tracking(app.light_scan_queue, app)
        if emulator_found:
           
            # Stelle sicher, dass die Konfigurationsdatei vorhanden ist
            if not app.auto_tracker.get_emulator_config():
                # Erstelle die Konfigurationsdatei, falls sie nicht existiert
                emulator_data = app.auto_tracker.get_emulator_config()
                if not emulator_data:
                    emulator_data = app.auto_tracker.get_emulator_config() # get_emulator_config aufrufen
                if emulator_data:
                    app.auto_tracker.create_emulator_config(emulator_data)

            game_running = app.auto_tracker.is_game_running(app.auto_tracker.stop_event, app.auto_tracker.get_emulator_config(), app.light_scan_queue)
            
            if game_running:
                app.game_running = True
                process, base_address = app.auto_tracker.retrieve_base_address()
                
               
                
                auto.inventory_scan.initialize_shared_variables()
                
                # scanning spoiler log
                spoiler_scanner = SpoilerScanner(app, process, base_address)  # Korrekte Instanziierung
                spoiler_scanner.scan_spoiler_log()  # Korrekter Methodenaufruf
                
                # scanning inventory
                inventory_scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
                obtained_items = {}  # Leeres Set für gefundene Items
                inventory_scanner.scan_inventory(process, base_address, obtained_items)

                # Gefundene Items speichern
                app.obtained_items = obtained_items
                
                # scanning map
                location_scanner = LocationScanner(app, app.canvas, app.location_labels)
                location_scanner.scan_locations(process, base_address)
                
                Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=50, y_offset=50)  # Adjusted
                save_to_temp(app)
                
            else:
                app.game_running = False
                Banner(app.root, message="Game not running", bg_color="#F08080", x_offset=50, y_offset=50)

        else:
            logging.error("Debug: Emulator not found, stopping sync.")
            app.game_running = False
            Banner(app.root, message="Emulator not found", bg_color="#F08080", x_offset=50, y_offset=50)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=50, y_offset=50)
        
def sync_keys(menu_frame, app):
    try:
        emulator_found = app.auto_tracker.start_tracking(app.light_scan_queue, app)
        if emulator_found:

            # Stelle sicher, dass die Konfigurationsdatei vorhanden ist
            if not app.auto_tracker.get_emulator_config():
                # Erstelle die Konfigurationsdatei, falls sie nicht existiert
                emulator_data = app.auto_tracker.get_emulator_config()
                if not emulator_data:
                    emulator_data = app.auto_tracker.get_emulator_config() # get_emulator_config aufrufen
                if emulator_data:
                    app.auto_tracker.create_emulator_config(emulator_data)

            game_running = app.auto_tracker.is_game_running(app.auto_tracker.stop_event, app.auto_tracker.get_emulator_config(), app.light_scan_queue)
            
            if game_running:
                app.game_running = True
                process, base_address = app.auto_tracker.retrieve_base_address()
               
                
               
                auto.inventory_scan.initialize_shared_variables()
                
                # scanning spoiler log
                spoiler_scanner = SpoilerScanner(app, process, base_address)  # Korrekte Instanziierung
                spoiler_scanner.scan_spoiler_log()  # Korrekter Methodenaufruf
                
                # scanning scenario
                scenario_scanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
                obtained_items = {}  # Leeres Set für gefundene Items
                scenario_scanner.scan_scenario(process, base_address, obtained_items)
                                
                # Gefundene Items speichern
                app.obtained_items = obtained_items
                
                # scanning map
                location_scanner = LocationScanner(app, app.canvas, app.location_labels)
                location_scanner.scan_locations(process, base_address)
                
                Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=50, y_offset=50)  # Adjusted
                save_to_temp(app)
                
            else:
                app.game_running = False
                Banner(app.root, message="Game not running", bg_color="#F08080", x_offset=50, y_offset=50)

        else:
            logging.error("Debug: Emulator not found, stopping sync.")
            app.game_running = False
            Banner(app.root, message="Emulator not found", bg_color="#F08080", x_offset=50, y_offset=50)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=50, y_offset=50)
             
def sync_chars(menu_frame, app):
    try:
        emulator_found = app.auto_tracker.start_tracking(app.light_scan_queue, app)
        if emulator_found:
            
            # Stelle sicher, dass die Konfigurationsdatei vorhanden ist
            if not app.auto_tracker.get_emulator_config():
                # Erstelle die Konfigurationsdatei, falls sie nicht existiert
                emulator_data = app.auto_tracker.get_emulator_config()
                if not emulator_data:
                    emulator_data = app.auto_tracker.get_emulator_config() # get_emulator_config aufrufen
                if emulator_data:
                    app.auto_tracker.create_emulator_config(emulator_data)

            game_running = app.auto_tracker.is_game_running(app.auto_tracker.stop_event, app.auto_tracker.get_emulator_config(), app.light_scan_queue)
            
            if game_running:
                app.game_running = True
                process, base_address = app.auto_tracker.retrieve_base_address()
                
               
                
                print("Debug: Starting manual sync...")
                auto.inventory_scan.initialize_shared_variables()
                
                # scanning spoiler log
                spoiler_scanner = SpoilerScanner(app, process, base_address)  # Korrekte Instanziierung
                spoiler_scanner.scan_spoiler_log()  # Korrekter Methodenaufruf
                
                # scanning map
                location_scanner = LocationScanner(app, app.canvas, app.location_labels)
                location_scanner.scan_locations(process, base_address)
                
                # scanning characters
                
                character_scanner = CharacterScanner(app, process, base_address, app.characters_canvas, app.character_images, app.image_cache)
                character_scanner.scan()
                character_scanner.scan_capsule_monsters()
                
                Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=50, y_offset=50)  # Adjusted
                save_to_temp(app)
                
            else:
                app.game_running = False
                Banner(app.root, message="Game not running", bg_color="#F08080", x_offset=50, y_offset=50)

        else:
            logging.error("Debug: Emulator not found, stopping sync.")
            app.game_running = False
            Banner(app.root, message="Emulator not found", bg_color="#F08080", x_offset=50, y_offset=50)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=50, y_offset=50)
          
def sync_maiden(menu_frame, app):
    try:
        emulator_found = app.auto_tracker.start_tracking(app.light_scan_queue, app)
        if emulator_found:
            
            # Stelle sicher, dass die Konfigurationsdatei vorhanden ist
            if not app.auto_tracker.get_emulator_config():
                # Erstelle die Konfigurationsdatei, falls sie nicht existiert
                emulator_data = app.auto_tracker.get_emulator_config()
                if not emulator_data:
                    emulator_data = app.auto_tracker.get_emulator_config() # get_emulator_config aufrufen
                if emulator_data:
                    app.auto_tracker.create_emulator_config(emulator_data)

            game_running = app.auto_tracker.is_game_running(app.auto_tracker.stop_event, app.auto_tracker.get_emulator_config(), app.light_scan_queue)
            
            if game_running:
                app.game_running = True
                process, base_address = app.auto_tracker.retrieve_base_address()
                
                
                
                auto.inventory_scan.initialize_shared_variables()
                
                # scanning spoiler log
                spoiler_scanner = SpoilerScanner(app, process, base_address)  # Korrekte Instanziierung
                spoiler_scanner.scan_spoiler_log()  # Korrekter Methodenaufruf
                
                # scanning map
                location_scanner = LocationScanner(app, app.canvas, app.location_labels)
                location_scanner.scan_locations(process, base_address)
                
                maiden_scanner = MaidenScanner(app, app.maidens_canvas, app.maiden_images) # MaidenScanner erstellen, wenn Maidens initialisiert sind
                maiden_scanner.update_maidens()
                
                Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=50, y_offset=50)  # Adjusted
                save_to_temp(app)
                
            else:
                app.game_running = False
                Banner(app.root, message="Game not running", bg_color="#F08080", x_offset=50, y_offset=50)

        else:
            logging.error("Debug: Emulator not found, stopping sync.")
            app.game_running = False
            Banner(app.root, message="Emulator not found", bg_color="#F08080", x_offset=50, y_offset=50)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=50, y_offset=50)
             
def sync_pos(menu_frame, app):
    try:
        emulator_found = app.auto_tracker.start_tracking(app.light_scan_queue, app)
        if emulator_found:
            
            # Stelle sicher, dass die Konfigurationsdatei vorhanden ist
            if not app.auto_tracker.get_emulator_config():
                # Erstelle die Konfigurationsdatei, falls sie nicht existiert
                emulator_data = app.auto_tracker.get_emulator_config()
                if not emulator_data:
                    emulator_data = app.auto_tracker.get_emulator_config() # get_emulator_config aufrufen
                if emulator_data:
                    app.auto_tracker.create_emulator_config(emulator_data)

            game_running = app.auto_tracker.is_game_running(app.auto_tracker.stop_event, app.auto_tracker.get_emulator_config(), app.light_scan_queue)
            
            if game_running:
                app.game_running = True
                process, base_address = app.auto_tracker.retrieve_base_address()
                
          
                
                auto.inventory_scan.initialize_shared_variables()
                
                # scanning spoiler log
                spoiler_scanner = SpoilerScanner(app, process, base_address)  # Korrekte Instanziierung
                spoiler_scanner.scan_spoiler_log()  # Korrekter Methodenaufruf
                
                # scanning map
                location_scanner = LocationScanner(app, app.canvas, app.location_labels)
                location_scanner.scan_locations(process, base_address)
                
                position_scanner = PositionScanner(app, process, base_address, app.canvas, app.map_image)
                position_scanner.show_position()
                
                Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=50, y_offset=50)  # Adjusted
                save_to_temp(app)
                
            else:
                app.game_running = False
                Banner(app.root, message="Game not running", bg_color="#F08080", x_offset=50, y_offset=50)

        else:
            logging.error("Debug: Emulator not found, stopping sync.")
            app.game_running = False
            Banner(app.root, message="Emulator not found", bg_color="#F08080", x_offset=50, y_offset=50)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=50, y_offset=50)
                
def perform_initial_scan(process, base_address, app):
    """Perform an initial scan to setup the GUI components."""  
    print("Debug: perform_initial_scan called")
    if not app.game_running:
        logging.debug("Initial scan skipped: Game not running.")
        return

    if process is None or base_address is None:
        logging.error("Initial scan failed: Process or base address is invalid.")
        messagebox.showinfo("Process or Base_Address failure", "A critical process is not running. Please try again.")
        raise ValueError("Process or base address is invalid.")

    try:
        print(f"Base Address Type: {type(base_address)}, Value: {base_address}")
        
        # scanning spoiler log
        spoiler_scanner = SpoilerScanner(app, process, base_address)  # Korrekte Instanziierung
        spoiler_scanner.scan_spoiler_log()  # Korrekter Methodenaufruf
        
        # scanning characters
        auto.inventory_scan.initialize_shared_variables()
        character_scanner = CharacterScanner(app, process, base_address, app.characters_canvas, app.character_images, app.image_cache)
        character_scanner.scan()
        
        # scanning inventory
        inventory_scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
        obtained_items = set() # Leeres Set für gefundene Items
        inventory_scanner.scan_inventory(process, base_address, obtained_items)
        
        # Gefundene Items speichern
        app.obtained_items = obtained_items
        
        # scanning scenario
        scenario_scanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
        obtained_items = set() # Leeres Set für gefundene Items
        scenario_scanner.scan_scenario(process, base_address, app.obtained_items)
        
        # Gefundene Items speichern
        app.obtained_items = obtained_items
        
        
        
        # ✅ READ GOLD VALUE CORRECTLY (2-byte)
        #gold_address = base_address + int(current_config['gold_address'], 16)
        #gold_value = process.read_short(gold_address)
        #print(f"Gold Value: {gold_value}")
        
        
    except Exception as e:
        logging.error(f"Error during initial scan: {e}")
        messagebox.showerror("Initial Scan Error", f"Ein unerwarteter Fehler ist aufgetreten: {e}")


def read_memory_with_retry(process, address, size, retries=3, delay=1):
    attempt = 0
    while attempt < retries:
        try:
            memory_value = pymem.memory.read_bytes(process.process_handle, address, size)
            return memory_value
        except pymem.exception.MemoryReadError as e:
            print(f"Memory read error at address 0x{address:X}: {e}, retrying...")
            time.sleep(delay)
            attempt += 1
    raise pymem.exception.MemoryReadError(f"Failed to read memory at address 0x{address:X} after {retries} attempts")


def perform_light_scan(process, base_address, app):
    """Perform a light scan to check critical state changes without updating all components."""
    print(f"Game was detected. Starting scans...")
    if not app.game_running:
        logging.debug("Light scan skipped: Game not running.")
        return  # Skip the scan if the game is not running

    if process is None or base_address is None:
        logging.error("Light scan failed: Process or base address is invalid.")
        messagebox.showinfo("Process or Base_Address failure", "A critical process is not running. Please try again.")
        raise ValueError("Process or base address is invalid.")
    '''
    try:
        print(f"Base Address Type: {type(base_address)}, Value: {base_address}")
        logging.debug("Debug: Creating and calling CharacterScanner...")
        auto.inventory_scan.initialize_shared_variables()
        character_scanner = CharacterScanner(app, process, base_address, app.characters_canvas, app.character_images, app.image_cache)
        character_scanner.scan()
        logging.debug("Debug: CharacterScanner scan completed.")
        
        # ✅ READ GOLD VALUE CORRECTLY (2-byte)
        gold_address = base_address + int(current_config['gold_address'], 16)
        gold_value = process.read_short(gold_address)
        print(f"Gold Value: {gold_value}")
        
        # Update character images based on active characters (limited to first row)
        for name, info in app.characters_canvas.character_images.items():
            if name in CHARACTER_BYTE_MAPPING.values():
                is_active = name in active_characters
                update_character_image(app.characters_canvas, app.character_images, name, is_active)
        
        # Perform light inventory scan
        inventory_scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
        inventory_changed = inventory_scanner.scan_inventory(app.process, app.base_address, app.obtained_items)

        # Perform light scenario scan
        scenario_scanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
        scenario_changed = scenario_scanner.scan_scenario(app.process, app.base_address, app.obtained_items)

        # Only update tool and scenario images if there were changes
        if inventory_changed:
            # Update tool images
            for tool_name, tool_info in app.tool_images.items():
                image_path = (tool_items_c[tool_name]["image_path"]
                              if tool_name in app.obtained_items else tool_items_bw[tool_name]["image_path"])
                new_image = app.load_image_cached(image_path)
                if new_image:
                    app.tools_canvas.itemconfig(tool_info['position'], image=new_image)
                    tool_info['image'] = new_image

        if scenario_changed:
            # Update scenario images
            for scenario_name, scenario_info in app.scenario_images.items():
                image_path = (scenario_items_c[scenario_name]["image_path"]
                              if scenario_name in app.obtained_items else scenario_items_bw[scenario_name]["image_path"])
                new_image = app.load_image_cached(image_path)
                if new_image:
                    app.scenario_canvas.itemconfig(scenario_info['position'], image=new_image)
                    scenario_info['image'] = new_image
        
    except Exception as e:
        logging.error(f"Error during light scan: {e}")
    '''
    # Schedule the next light scan if not stopped
    app.root.after(LIGHT_SCAN_INTERVAL, lambda: perform_light_scan(process, base_address, app))
        
def check_game_running(app, process, base_address):
    try:
        for offset in shared.character_slots:
            address = base_address + offset
            try:
                byte_value = read_memory_with_retry(process, address, 1)
                if byte_value[0] != 0xFF:
                    return True
            except Exception as e:
                logging.error(f"Failed reading memory at {hex(address)}: {e}")
        return False
    except Exception as e:
        logging.error(f"Error checking if game is running: {e}")
        return False
    
