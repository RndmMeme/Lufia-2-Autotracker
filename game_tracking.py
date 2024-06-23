import pymem
import time
from helpers.memory_utils import is_process_running
from inventory_scan import CHARACTER_SLOT_ADDRESSES, CHARACTER_BYTE_MAPPING
from canvas_config import update_character_image

GOLD_ADDRESS = 0xA32D9E
FULL_SCAN_INTERVAL = 30000  # Full scan every 30 seconds
LIGHT_SCAN_INTERVAL = 10000   # Light scan every 5 seconds
TRACKER_SCAN_INTERVAL = 10000


# game_tracking.py

def track_game(app):
    """Tracks the game state and updates the app accordingly."""

    # Check if automatic updates are paused
    if not app.auto_update_active:
        print("Auto updates are paused. Skipping this cycle.")
        return

    # Attach to the game process if not already attached
    if app.process is None or app.base_address is None:
        process_name = is_process_running("snes9x")
        if not process_name:
            print("Waiting for snes9x to start...")
            app.root.after(5000, lambda: track_game(app))
            return

        try:
            app.process = pymem.Pymem(process_name)
            app.base_address = app.process.process_base.lpBaseOfDll
            print(f"Attached to {process_name} at base address 0x{app.base_address:X}")
            
            # Check if the game is running by reading the character slot
            if not app.is_game_running(app.process, app.base_address):
                print("Waiting for game to load...")
                app.process = None  # Reset process to reattempt attachment
                app.base_address = None
                app.root.after(5000, lambda: track_game(app))
                return
            else:
                print("Game is running. Proceeding with the scan.")
                app.initial_scan_done = False  # Reset to allow the initial scan

        except pymem.exception.ProcessNotFound:
            print("Process not found. Make sure the game is running.")
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
                print("Performing periodic full scan...")
                perform_game_tracking(app)
                app.full_scan_due = False  # Reset full scan flag

            # Schedule the next full scan
            app.root.after(FULL_SCAN_INTERVAL, lambda: set_full_scan_due(app))

            # Perform a light scan more frequently
            perform_light_scan(app)

    except Exception as e:
        print(f"Error during game tracking: {e}")
        app.root.after(5000, lambda: track_game(app))

def set_full_scan_due(app):
    """Sets the flag indicating a full scan is due."""
    app.full_scan_due = True



def perform_game_tracking(app):
    try:
        if app.base_address is None:
            print("Error: base_address is None at the start of perform_game_tracking.")
            return  # Early exit to prevent further issues.

        print(f"Scanning game state with base_address: 0x{app.base_address:X}")

        # Read current gold to determine if detailed scan is needed
        current_gold_bytes = read_memory_with_retry(app.process, app.base_address + app.GOLD_ADDRESS, 2)
        current_gold = int.from_bytes(current_gold_bytes, byteorder='little')
        print(f"Current gold: {current_gold}")

        if app.previous_gold is None or app.previous_gold != current_gold:
            print(f"Gold changed from {app.previous_gold} to {current_gold}. Performing detailed scan.")
            app.previous_gold = current_gold

            # Perform detailed scans when significant changes are detected
            app.scanner.scan_inventory(app.process, app.base_address, app.obtained_items)
            app.sscanner.scan_scenario(app.process, app.base_address, app.obtained_items)

            # Scan character slots to determine which characters are active
            active_characters = set()
            for offset in CHARACTER_SLOT_ADDRESSES:
                address = app.base_address + offset
                try:
                    byte_value = read_memory_with_retry(app.process, address, 1)
                    character_id = byte_value[0]
                    character_name = CHARACTER_BYTE_MAPPING.get(character_id, "Unknown")
                    if character_name != "Unknown":
                        active_characters.add(character_name)
                except Exception as e:
                    print(f"Error reading character slot at address 0x{address:X}: {e}")

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
            print("No significant changes detected, skipping detailed scan.")
            # Perform a lighter scan if no significant changes are detected
            perform_light_scan(app)

    except Exception as e:
        print(f"Error during game tracking: {e}")

    # Schedule the next scan after the interval
    app.root.after(TRACKER_SCAN_INTERVAL, lambda: track_game(app))


def perform_light_scan(app):
    """
    Perform a light scan to check critical state changes without updating all components.
    This scan focuses on ensuring the game is running and checks a critical value like in-game gold.
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
                gold_value = read_memory_with_retry(app.process, app.base_address + GOLD_ADDRESS, 2)
                gold = int.from_bytes(gold_value, 'little')
                if gold != app.previous_gold:
                    app.previous_gold = gold
                    print(f"In-game gold: {gold}")
            except Exception as e:
                print(f"Error reading gold value: {e}")

        # Quick check of active character slots to verify active characters haven't changed
        active_characters = set()
        for offset in CHARACTER_SLOT_ADDRESSES:
            address = app.base_address + offset
            try:
                byte_value = read_memory_with_retry(app.process, address, 1)
                character_id = byte_value[0]
                character_name = CHARACTER_BYTE_MAPPING.get(character_id, "Unknown")
                if character_name != "Unknown":
                    active_characters.add(character_name)
            except Exception as e:
                print(f"Error reading character slot at address 0x{address:X}: {e}")

        if active_characters != app.active_characters:
            app.active_characters = active_characters
            print(f"Active characters have changed: {active_characters}")

        # Optionally, refresh only specific components if a change is detected
        for name in active_characters:
            update_character_image(app.characters_canvas, app.character_images, name, is_active=True)

    except Exception as e:
        print(f"Error during light scan: {e}")

    # Schedule the next light scan
    app.root.after(LIGHT_SCAN_INTERVAL, lambda: perform_light_scan(app))

def check_game_running(app, process, base_address):
    try:
        # Check if any character slot is occupied (not Empty)
        for offset in CHARACTER_SLOT_ADDRESSES:
            address = base_address + offset
            byte_value = read_memory_with_retry(process, address, 1)
            if byte_value[0] != 0xFF:  # Assuming 0xFF means the slot is empty
                print(f"Character slot at 0x{address:X} is occupied.")
                return True
        print("No character slots are occupied. Game might not be running.")
        return False
    except Exception as e:
        print(f"Error checking if game is running: {e}")
        return False

def read_memory_with_retry(process, address, size, retries=3, delay=1):
    attempt = 0
    while attempt < retries:
        try:
            print(f"Reading memory from address 0x{address:X}, size: {size}")
            memory_value = pymem.memory.read_bytes(process.process_handle, address, size)
            print(f"Memory value read (raw): {memory_value.hex()}")
            return memory_value
        except pymem.exception.MemoryReadError as e:
            print(f"Memory read error at address 0x{address:X}: {e}")
            if e.error_code == 299:
                print("Partial copy error, retrying...")
                attempt += 1
                time.sleep(delay)
            else:
                raise
    raise pymem.exception.MemoryReadError(f"Failed to read memory at address 0x{address:X} after {retries} attempts")

