# game_tracking.py

import pymem
import time
from helpers.memory_utils import is_process_running
from inventory_scan import CHARACTER_SLOT_ADDRESSES, CHARACTER_BYTE_MAPPING, InventoryScanner, ScenarioScanner
from canvas_config import update_character_image, update_autoscan_label
from shared import tool_items_bw, tool_items_c, scenario_items_bw, scenario_items_c
import shared
import tkinter as tk
import logging

FULL_SCAN_INTERVAL = 30000  # Full scan every 30 seconds
LIGHT_SCAN_INTERVAL = 5000  # Light scan every 10 seconds
TRACKER_SCAN_INTERVAL = 5000  # Scenario scan every 5 seconds

def show_error_window(app):
    """Show the error window if the emulator is not running."""
    error_window = tk.Toplevel(app.root)
    error_window.title("Error")
    error_text = "Please load the game first before running the tracker!"
    label = tk.Label(error_window, text=error_text, padx=10, pady=10, justify=tk.CENTER)
    label.pack()

    close_button = tk.Button(error_window, text="Close", command=lambda: close_app(app))
    close_button.pack(pady=10)

def close_app(app):
    """Terminate the tracker process."""
    app.root.destroy()

def track_game(app):
    """Tracks the game state and updates the app accordingly."""

    # Check if automatic updates are paused
    if not app.auto_update_active:
        logging.info("Auto updates are paused. Skipping this cycle.")
        update_autoscan_label(app.autoscan_label, False)
        return

    # Attach to the game process if not already attached
    if app.process is None or app.base_address is None:
        process_name = is_process_running("snes9x")
        if not process_name:
            show_error_window(app)  # Show the error window
            return

        try:
            app.process = pymem.Pymem(process_name)
            app.base_address = app.process.process_base.lpBaseOfDll
           
            # Check if the game is running by reading the character slot
            if not app.is_game_running(app.process, app.base_address):
                print("Waiting for game to load...")
                app.process = None  # Reset process to reattempt attachment
                app.base_address = None
                app.root.after(5000, lambda: track_game(app))
                return
            else:
                app.initial_scan_done = False  # Reset to allow the initial scan

        except pymem.exception.ProcessNotFound:
            logging.error("Process not found. Make sure the game is running.")
            app.root.after(5000, lambda: track_game(app))
            return

    # Perform scans if the game is confirmed to be running and the process is attached
    try:
        if app.process and app.base_address:
            # Perform the initial scan if not done yet
            if not app.initial_scan_done:
                print("Performing initial scans...")
                perform_game_tracking(app)
                app.initial_scan_done = True
                print("Initial scans complete. Game is fully loaded.")

            # Full scan at longer intervals
            if app.auto_update_active and app.full_scan_due:
                perform_game_tracking(app)
                app.full_scan_due = False  # Reset full scan flag

            # Schedule the next full scan
            app.root.after(FULL_SCAN_INTERVAL, lambda: set_full_scan_due(app))

            # Perform a light scan more frequently
            perform_light_scan(app)
            
            update_autoscan_label(app.autoscan_label, True)

    except Exception as e:
        logging.error(f"Error during game tracking: {e}")
        app.root.after(5000, lambda: track_game(app))
           

def set_full_scan_due(app):
    """Sets the flag indicating a full scan is due."""
    app.full_scan_due = True

def perform_game_tracking(app):
    try:
        if app.base_address is None:
            logging.error("Error: base_address is None at the start of perform_game_tracking.")
            return  # Early exit to prevent further issues.

        # Read current gold to determine if detailed scan is needed
        current_gold_bytes = read_memory_with_retry(app.process, app.base_address + shared.GOLD_ADDRESS, 2)
        current_gold = int.from_bytes(current_gold_bytes, byteorder='little')

        if app.previous_gold is None or app.previous_gold != current_gold:
            app.previous_gold = current_gold

            # Perform detailed scans when significant changes are detected
            app.scanner.scan_inventory(app.process, app.base_address, app.obtained_items)
            app.sscanner.scan_scenario(app.process, app.base_address, app.obtained_items)

            # Scan character slots to determine which characters are active
            active_characters = set()
            for offset in shared.character_slots:
                address = app.base_address + offset
                try:
                    byte_value = read_memory_with_retry(app.process, address, 1)
                    character_id = byte_value[0]
                    character_name = CHARACTER_BYTE_MAPPING.get(character_id, "Unknown")
                    if character_name != "Unknown":
                        active_characters.add(character_name)
                except Exception as e:
                    logging.error(f"Error reading character slot at address 0x{address:X}: {e}")

            # Determine newly active and newly inactive characters
            newly_active = active_characters - app.previous_active_characters
            newly_inactive = app.previous_active_characters - active_characters

            # Dim characters that are no longer active
            for name in newly_inactive:
                if name in app.character_images and name not in app.manual_toggles:
                    update_character_image(app.characters_canvas, app.character_images, name, False)

            # Color the newly active characters
            for name in newly_active:
                if name in app.character_images and name not in app.manual_toggles:
                    update_character_image(app.characters_canvas, app.character_images, name, True)

            # Update the tracked active characters
            app.previous_active_characters = active_characters

        else:
            # Perform a lighter scan if no significant changes are detected
            perform_light_scan(app)

    except Exception as e:
        logging.error(f"Error during game tracking: {e}")

    # Schedule the next scan after the interval
    app.root.after(TRACKER_SCAN_INTERVAL, lambda: track_game(app))

def perform_light_scan(app):
    """
    Perform a light scan to check critical state changes without updating all components.
    This scan focuses on ensuring the game is running and checks critical values like in-game gold,
    and updates character, scenario items, and tools.
    """
    try:
        # Check if the game process is still running
        process_name = is_process_running("snes9x")
        if not process_name:
            print("Game process not found. Pausing updates.")
            app.auto_update_active = False  # Pause automatic updates if the game is not running
            return

        # Quick check of in-game gold to verify game state
        if app.base_address:
            try:
                gold_value = read_memory_with_retry(app.process, app.base_address + shared.GOLD_ADDRESS, 2)
                gold = int.from_bytes(gold_value, 'little')
                if gold != app.previous_gold:
                    app.previous_gold = gold
            except Exception as e:
                logging.error(f"Error reading gold value: {e}")

         # Quick check of active character slots to verify active characters haven't changed
        active_characters = set()
        for offset in shared.character_slots:
            address = app.base_address + offset
            try:
                byte_value = read_memory_with_retry(app.process, address, 1)
                character_id = byte_value[0]
                if character_id in CHARACTER_BYTE_MAPPING:
                    character_name = CHARACTER_BYTE_MAPPING[character_id]
                    if character_name != "Unknown":
                        active_characters.add(character_name)
            except Exception as e:
                logging.error(f"Error reading character slot at address 0x{address:X}: {e}")

        # Update character images based on active characters (limited to first row)
        for name, info in app.character_images.items():
            if name in CHARACTER_BYTE_MAPPING.values():
                is_active = name in active_characters
                update_character_image(app.characters_canvas, app.character_images, name, is_active)

        # Perform light inventory scan
        inventory_scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
        inventory_scanner.scan_inventory(app.process, app.base_address, app.obtained_items)

        # Perform light scenario scan
        scenario_scanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
        scenario_scanner.scan_scenario(app.process, app.base_address, app.obtained_items)

        # Update tool images
        for tool_name, tool_info in app.tool_images.items():
            image_path = (tool_items_c[tool_name]["image_path"]
                          if tool_name in app.obtained_items else tool_items_bw[tool_name]["image_path"])
            new_image = app.load_image_cached(image_path)
            if new_image:
                app.tools_canvas.itemconfig(tool_info['position'], image=new_image)
                tool_info['image'] = new_image

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

    # Schedule the next light scan
    app.root.after(LIGHT_SCAN_INTERVAL, lambda: perform_light_scan(app))


def check_game_running(app, process, base_address):
    try:
        # Detailed logging for each slot check
        for offset in shared.character_slots:
            address = base_address + offset
            try:
                byte_value = read_memory_with_retry(process, address, 1)
                if byte_value[0] != 0xFF:  # Assuming 0xFF means the slot is empty
                    return True
            except Exception as e:
                logging.error(f"Failed reading memory at {hex(address)}: {e}")
        return False
    except Exception as e:
        logging.error(f"Error checking if game is running: {e}")
        return False

def read_memory_with_retry(process, address, size, retries=3, delay=1):
    attempt = 0
    while attempt < retries:
        try:
            memory_value = pymem.memory.read_bytes(process.process_handle, address, size)
            return memory_value
        except pymem.exception.MemoryReadError as e:
            logging.error(f"Memory read error at address 0x{address:X}: {e}")
            if e.error_code == 299:
                attempt += 1
                time.sleep(delay)
            else:
                raise
    raise pymem.exception.MemoryReadError(f"Failed to read memory at address 0x{address:X} after {retries} attempts")
