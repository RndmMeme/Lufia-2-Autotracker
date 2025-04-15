#start_auto.py

import psutil
import tkinter as tk
from tkinter import messagebox
import time
from multiprocessing import Process, Event, Queue
from shared import DATA_DIR, emulator_addresses, BASE_DIR, config
import pygetwindow as gw
from rapidfuzz import process, fuzz
import logging
from pathlib import Path
import json
import pymem
import os
from auto.inventory_scan import SpoilerScanner, PositionScanner

# Load emulator addresses
EMULATOR_CONFIG_PATH = os.path.join(DATA_DIR, 'emulator_addresses.json')

class startTracker():
    def __init__(self):
        self.tracking_process = None  # Store the process instance
        self.stop_event = Event()
        self.emulator_process_name = None  # Store the emulator process name
        self.failed_game_detection = None
        self.retrieve_base_address()
        self.emulator_config = self.create_emulator_config()
        self.initialize_spoiler()
    
    def retrieve_base_address(self):
        self.process = None
        self.base_address = None
       
        try:
            if self.is_process_running("snes9x-x64.exe"):
                
                try:
                    self.process = pymem.Pymem("snes9x-x64.exe")
                    self.base_address = self.process.process_base.lpBaseOfDll
                    config['base_address'] = self.base_address
                    config['process'] = self.process
                   
                except pymem.exception.ProcessNotFound:
                    logging.error("Prozess nicht gefunden während pymem.Pymem()") # Hinzugefügt
                except Exception as e:
                    logging.error(f"Fehler beim Zugriff auf den Prozess: {e}") # Hinzugefügt
            else:
                logging.error("snes9x-x64.exe wird nicht als laufend erkannt") # Hinzugefügt
        except pymem.exception.ProcessNotFound:
            logging.error("Prozess nicht gefunden während is_process_running") # Hinzugefügt
        logging.debug(f"retrieve_base_address gibt zurück: Prozess={self.process}, Basisadresse={self.base_address}") # Hinzugefügt
        return self.process, self.base_address

    def read_rom_start_address(self, process, pointer_base_address):
       
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

    def verify_shop_pointer(self, process, shop_pointer):
        
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
        
    def compute_capsule_sprite_pointer(self, process, config, rom_start_address):
        
        try:
            capsule_sprite_pointer_offset = int(config['capsule_sprite_offset'], 16)
            capsule_sprite_pointer = int(rom_start_address, 16) + capsule_sprite_pointer_offset
            

            # Debug: Wert an der berechneten Adresse auslesen
            
            return capsule_sprite_pointer
        except Exception as e:
            logging.error(f"Error verifying capsule sprite table base address: {e}")
            return None
    
    def create_emulator_config(self):
        
        emulator_configs = None
        try:
            with open(EMULATOR_CONFIG_PATH, 'r') as file:
                emulator_configs_data = json.load(file)
                emulator_configs = emulator_configs_data.get("snes9x-x64.exe",)
        except FileNotFoundError:
            logging.warning(f"Emulator configuration file not found at: {EMULATOR_CONFIG_PATH}")
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from emulator configuration file at: {EMULATOR_CONFIG_PATH}")

        if self.is_process_running("snes9x-x64.exe") and emulator_configs:
            try:
                process = pymem.Pymem("snes9x-x64.exe")
                base_address = process.process_base.lpBaseOfDll

                for config in emulator_configs:
                    pointer_base_address_offset = int(config['pointer_base_address'], 16)
                    pointer_base_address = pointer_base_address_offset + base_address
                    rom_start_address = self.read_rom_start_address(process, pointer_base_address)
                    if rom_start_address:
                        shop_pointer_offset = int(config['shop_offset'], 16)
                        shop_pointer = int(rom_start_address, 16) + shop_pointer_offset
                        if self.verify_shop_pointer(process, hex(shop_pointer)):
                            
                            self.compute_capsule_sprite_pointer(process, config, rom_start_address)
                            
                            with open(os.path.join(DATA_DIR, 'current_emulator_config.json'), 'w') as f:
                                json.dump(config, f)
                            return config
                logging.warning("No matching emulator configuration found for the current process state.")
            except pymem.exception.ProcessNotFound:
                logging.warning("SNES9x process found running, but could not be accessed by Pymem.")
            except Exception as e:
                logging.error(f"Error during process-based configuration loading: {e}")
        elif not self.is_process_running("snes9x-x64.exe"):
            logging.info("SNES9x process not found. Starting without emulator configuration.")
            return None

        return None   
     
    def is_process_running(self, process_name_substring):
        """
        Check if any process containing the specified substring in its name is running.
        
        Args:
            process_name_substring (str): Substring to search for in process names.

        Returns:
            str or None: The name of the first matching process, or None if no matching process is found.
        """
        
        for proc in psutil.process_iter(['name']):
            try:
                if process_name_substring.lower() in proc.info['name'].lower():
                    return proc.info['name']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None
    

    def get_emulator_config(self):
        """Reads the current_emulator_config.json file."""
        config_path = Path(DATA_DIR) / "current_emulator_config.json"
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning("Emulator config not found.")
            return None
 
    def start_tracking(self, queue):
        """Detects emulator by process first, then refines with window title."""
        #logging.debug(f"Loaded emulator names from JSON: {list(emulator_addresses.keys())}")
        
        if self.emulator_config:
           
            self.stop_event.clear()
            logging.info("Auto tracking started")
            
            logging.info(f"Using emulator config: {self.emulator_config}")
            return True
        else:
            logging.debug("No emulator configuration loaded.")
            return False


    def is_game_running(self, stop_event, queue):
        failure_count = 0
        game_running = False

        process, base_address = self.retrieve_base_address()

        if process is None or base_address is None:
            logging.error("Game detection failed: Emulator process or base address not found.")
            self.failed_game_detection = True
            stop_event.set()
            return

        if self.emulator_config is None:
            logging.error("Emulator configuration not loaded. Cannot start game tracking.")
            stop_event.set()
            
            return

        logging.info(f"Game tracking started. Base Address: {hex(base_address)}")

        while not stop_event.is_set() and not game_running:
            logging.debug("Checking if game is running...")

            try:
                pointer_base_address = base_address + int(self.emulator_config['pointer_base_address'], 16)
                rom_start_address = self.read_rom_start_address(process, pointer_base_address)

                if rom_start_address:
                    shop_pointer = int(rom_start_address, 16) + int(self.emulator_config['shop_offset'], 16)

                    failure_count = 0
                    game_running = True
                    return game_running
                else:
                    failure_count += 1
                    logging.warning("Game not detected. ROM start address not found.")

                if failure_count >= 5:
                    logging.error("Game detection failed 5 times. Stopping tracking process.")
                    self.failed_game_detection = True
                    stop_event.set()
                    
                    return

                stop_event.wait(2)
            except Exception as e:
                logging.error(f"An error occurred during tracking: {e}")
                self.failed_game_detection = True
                stop_event.set()
                
                return

    def initialize_spoiler(self):
        # Initialize SpoilerScanner if process is valid
        if self.process and self.base_address:
            self.spoiler_scanner = SpoilerScanner(self, self.process, self.base_address)
            self.spoiler_scanner.scan_spoiler_log()
        else:
            self.spoiler_scanner = None
            logging.error(f"SpoilerScanner not initialized due to process issues.")
                       
    
        
    