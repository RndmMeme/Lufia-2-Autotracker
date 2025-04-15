#sync_game.py

import logging
import auto.inventory_scan
from auto.inventory_scan import InventoryScanner, ScenarioScanner, CharacterScanner, MaidenScanner, SpoilerScanner, LocationScanner, PositionScanner, save_to_temp
from helpers.optics import Banner
from helpers.resalo import SoftReset
from auto.start_auto import startTracker

def check_emulator_and_game(app):
    """Überprüft den Emulator-Status und die Spielausführung."""
    if not hasattr(app, 'auto_tracker') or app.auto_tracker is None:
        app.auto_tracker = startTracker() # Create an instance if it doesn't exist

    # Attempt to retrieve base address again
    app.auto_tracker.retrieve_base_address()
    process, base_address = app.auto_tracker.process, app.auto_tracker.base_address

    if process is None or base_address is None:
        logging.error("Debug: Emulator process or base address not found during sync.")
        app.game_running = False
        Banner(app.root, message="Emulator not found", bg_color="#F08080", x_offset=116, y_offset=31)
        return False, None, None  # Emulator nicht gefunden, beenden

    # Ensure the configuration file is loaded (this might be redundant if done in startTracker init)
    if app.auto_tracker.emulator_config is None:
        app.auto_tracker.emulator_config = app.auto_tracker.create_emulator_config()
        if app.auto_tracker.emulator_config is None:
            logging.error("Debug: Emulator configuration could not be loaded during sync.")
            Banner(app.root, message="Emulator config error", bg_color="#F08080", x_offset=116, y_offset=31)
            return False, None, None

    # Check if the game is running (this part might need adjustment based on your exact needs)
    # The is_game_running method in start_auto seems designed for continuous checking
    # For a single sync, we might just rely on the process and base address being found
    # game_running = app.auto_tracker.is_game_running(app.auto_tracker.stop_event, app.auto_tracker.get_emulator_config())
    # if not game_running:
    #     app.game_running = False
    #     Banner(app.root, message="Game not running", bg_color="#F08080", x_offset=116, y_offset=31)
    #     return False, None, None  # Spiel läuft nicht, beenden

    app.game_running = True
    return True, process, base_address

def sync_with_game(menu_frame, app):
    """Syncs the game state with the tracker once."""
    try:
        success, process, base_address = check_emulator_and_game(app)
        if not success:
            return

        SoftReset(app)  # SoftReset vor den Scans aufrufen

        auto.inventory_scan.initialize_shared_variables()

        spoiler_scanner = SpoilerScanner(app, process, base_address)
        spoiler_scanner.scan_spoiler_log()

        inventory_scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
        obtained_items = {}
        inventory_scanner.scan_inventory(process, base_address, obtained_items)

        scenario_scanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
        scenario_scanner.scan_scenario(process, base_address, obtained_items)

        app.obtained_items = obtained_items

        location_scanner = LocationScanner(app, app.canvas, app.location_labels)
        location_scanner.scan_locations(process, base_address)

        character_scanner = CharacterScanner(app, process, base_address, app.characters_canvas, app.character_images, app.image_cache)
        character_scanner.scan()
        character_scanner.scan_capsule_monsters()

        maiden_scanner = MaidenScanner(app, app.maidens_canvas, app.maiden_images)
        maiden_scanner.update_maidens()

        position_scanner = PositionScanner(app, process, base_address, app.canvas, app.map_image)
        position_scanner.show_position()

        Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=116, y_offset=31)
        save_to_temp(app)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=116, y_offset=31)

def sync_tools(menu_frame, app, silent=False):
    try:
        success, process, base_address = check_emulator_and_game(app)
        if not success:
            return

        auto.inventory_scan.initialize_shared_variables()
        spoiler_scanner = SpoilerScanner(app, process, base_address)
        spoiler_scanner.scan_spoiler_log()
        inventory_scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
        obtained_items = {}
        inventory_scanner.scan_inventory(process, base_address, obtained_items)
        
        # Überprüfen, ob app.obtained_items bereits befüllt ist und entsprechend updaten
        if app.obtained_items is None:
            app.obtained_items = obtained_items
        else:
            app.obtained_items.update(obtained_items)
        
        
        location_scanner = LocationScanner(app, app.canvas, app.location_labels)
        location_scanner.scan_locations(process, base_address)
        if not silent:
            Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=116, y_offset=31)
        save_to_temp(app)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=116, y_offset=31)
        
def sync_keys(menu_frame, app, silent=False):
    try:
        success, process, base_address = check_emulator_and_game(app)
        if not success:
            return
        auto.inventory_scan.initialize_shared_variables()
        spoiler_scanner = SpoilerScanner(app, process, base_address)
        spoiler_scanner.scan_spoiler_log()
        scenario_scanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
        obtained_items = {}
        scenario_scanner.scan_scenario(process, base_address, obtained_items)
        
        # Überprüfen, ob app.obtained_items bereits befüllt ist und entsprechend updaten
        if app.obtained_items is None:
            app.obtained_items = obtained_items
        else:
            app.obtained_items.update(obtained_items)
            
        location_scanner = LocationScanner(app, app.canvas, app.location_labels)
        location_scanner.scan_locations(process, base_address)
        if not silent:
            Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=116, y_offset=31)
        save_to_temp(app)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=116, y_offset=31)
             
def sync_chars(menu_frame, app, silent=False):
    try:
        success, process, base_address = check_emulator_and_game(app)
        if not success:
            return
        auto.inventory_scan.initialize_shared_variables()
        spoiler_scanner = SpoilerScanner(app, process, base_address)
        spoiler_scanner.scan_spoiler_log()
        location_scanner = LocationScanner(app, app.canvas, app.location_labels)
        location_scanner.scan_locations(process, base_address)
        character_scanner = CharacterScanner(app, process, base_address, app.characters_canvas, app.character_images, app.image_cache)
        character_scanner.scan()
        character_scanner.scan_capsule_monsters()
        if not silent:
            Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=116, y_offset=31)
        save_to_temp(app)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=116, y_offset=31)
          
def sync_maiden(menu_frame, app, silent=False):
    try:
        success, process, base_address = check_emulator_and_game(app)
        if not success:
            return
        spoiler_scanner = SpoilerScanner(app, process, base_address)
        spoiler_scanner.scan_spoiler_log()
        location_scanner = LocationScanner(app, app.canvas, app.location_labels)
        location_scanner.scan_locations(process, base_address)
        maiden_scanner = MaidenScanner(app, app.maidens_canvas, app.maiden_images)
        maiden_scanner.update_maidens()
        if not silent:
            Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=116, y_offset=31)
        save_to_temp(app)
        
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=116, y_offset=31)
             
def sync_pos(menu_frame, app, silent=False):
    try:
        success, process, base_address = check_emulator_and_game(app)
        if not success:
            return
        position_scanner = PositionScanner(app, process, base_address, app.canvas, app.map_image)
        position_scanner.show_position()
        if not silent:
            Banner(app.root, message="Sync Successful", bg_color="#90EE90", x_offset=116, y_offset=31)
        save_to_temp(app)
    except Exception as e:
        logging.error(f"Error during manual sync: {e}")
        Banner(app.root, message="Sync Failed", bg_color="#F08080", x_offset=116, y_offset=31)

                
