from PyQt6.QtCore import QObject, pyqtSignal, QPointF
import json
import logging
from typing import Dict, Any, Optional

from .helper_interface import HelperInterface

class StateManager(QObject):
    """
    Central repository for the application state.
    Handles manual overrides, data sync, and toroidal world logic.
    """
    
    # Signals for UI updates
    inventory_changed = pyqtSignal(dict)  # Emits full inventory dict
    location_changed = pyqtSignal(str, str)  # location_name, new_state (red/green/grey)
    player_position_changed = pyqtSignal(float, float)  # x, y (canvas coordinates)
    character_changed = pyqtSignal(str, bool)  # name, is_obtained
    character_assigned = pyqtSignal(str, str) # location, character_name
    character_unassigned = pyqtSignal(str, str) # location, character_name
    
    # Signal for external auto-updates (from network)
    auto_update_received = pyqtSignal(dict) # payload
    reset_occurred = pyqtSignal() # New signal for global reset
    
    shop_items_changed = pyqtSignal(list) # List of {location, name} dictionaries
    hints_changed = pyqtSignal(str)
    
    def __init__(self, logic_engine):
        super().__init__()
        self.logic_engine = logic_engine
        
        # --- Auto Tracker Helper ---
        self.helper = HelperInterface(self.on_helper_data)
        self.auto_update_received.connect(self.process_auto_update)
        
        # --- Internal State ---
        self._inventory: Dict[str, bool] = {}
        self._locations: Dict[str, str] = {}  # name -> state
        self._characters: Dict[str, bool] = {}
        self._character_locations: Dict[str, str] = {}
        self._active_party = set()
        self._active_party_list = [] # Ordered list for Sprite Display
        self._obtained_capsules = set()
        self._player_pos = QPointF(0, 0)
        self._game_world_size = (4096, 4096)  # Standard SNES Map Size
        self._canvas_size = (400, 400)        # Fixed Canvas Size
        self.shop_items = [] # List of {location, name}
        self.hints_text = ""
        
        # --- Overrides ---
        # If a user manually clicks something, it gets locked here.
        # External data updates for locked items are ignored until reset.
        self._manual_inventory_overrides: Dict[str, bool] = {}
        self._manual_location_overrides: Dict[str, str] = {}
        self._manual_character_overrides: Dict[str, bool] = {}
        
        # --- Load Location Mapping ---
        try:
             import os
             import sys
             
             if getattr(sys, 'frozen', False):
                 base_path = sys._MEIPASS
                 mapping_path = os.path.join(base_path, "src", "data", "location_name_mapping.json")
             else:
                 mapping_path = os.path.join("src", "data", "location_name_mapping.json")

             with open(mapping_path, 'r') as f:
                 self._location_mapping = json.load(f)
             logging.info(f"Loaded {len(self._location_mapping)} location mappings.")
        except Exception as e:
            logging.error(f"Failed to load location mapping: {e}")
            self._location_mapping = {}

    def _normalize_location_name(self, raw_loc):
        """
        Normalize location name from spoiler log using loaded mapping.
        Replicates v1.3 Logic: Linear search to find FIRST matching internal name.
        """
        if not raw_loc:
            return "Unknown"
            
        # Linear search for FIRST match (Value == raw_loc)
        # This is critical because multiple Internal Locations (Keys) map to the SAME Spoiler Name (Value).
        # v1.3 relies on finding the FIRST one (e.g. "Ruby Cave Capsule" before "Ruby Cave")
        for internal_name, spoiler_name in self._location_mapping.items():
            if spoiler_name == raw_loc:
                return internal_name
                
        return raw_loc
        
    # --- Public Accessors ---
    
    def get_inventory(self) -> Dict[str, bool]:
        """Explicit getter for inventory."""
        effective = self._inventory.copy()
        effective.update(self._manual_inventory_overrides)
        return effective

    @property
    def inventory(self) -> Dict[str, bool]:
        """Returns effective inventory (actual + overrides)."""
        return self.get_inventory()

    @property
    def locations(self) -> Dict[str, str]:
        """Returns effective location states."""
        effective = self._locations.copy()
        effective.update(self._manual_location_overrides)
        return effective
        
    def get_player_position(self) -> QPointF:
        """Returns current player position (canvas coordinates)."""
        return self._player_pos

    # --- Manual Interactions (High Priority) ---
    
    def set_manual_location_state(self, name: str, state: str):
        """User manually clicked a location dot."""
        self._manual_location_overrides[name] = state
        self.location_changed.emit(name, state)
        logging.info(f"Manual override: Location {name} -> {state}")

    def toggle_manual_inventory(self, item_name: str):
        """User clicked an item icon."""
        current = self.inventory.get(item_name, False)
        new_state = not current
        self._manual_inventory_overrides[item_name] = new_state
        self.inventory_changed.emit(self.inventory)
        logging.info(f"Manual override: Item {item_name} -> {new_state}")

    def reset_overrides(self):
        """Clears all manual overrides, reverting to raw external data."""
        self._manual_inventory_overrides.clear()
        self._manual_location_overrides.clear()
        self._manual_character_overrides.clear()
        
        # Re-emit everything to sync UI
        self.inventory_changed.emit(self._inventory)
        for loc, state in self._locations.items():
            self.location_changed.emit(loc, state)
        # TODO: emit characters
        
        logging.info("Manual overrides reset.")

    # --- External Data Updates (Low Priority) ---
    
    def update_from_external(self, data: Dict[str, Any]):
        """
        Ingest data from the C# helper.
        Expected keys: 'inventory', 'cleared_locations', 'player_x', 'player_y'
        """
        # 1. Update Inventory
        if 'inventory' in data:
            raw_inventory = data['inventory']
            # Only update internal state, do not overwrite overrides
            self._inventory = raw_inventory
            # Emit key-by-key or full update? Full update is safer for UI consistency
            self.inventory_changed.emit(self.inventory)

        # 2. Update Locations
        # Logic is complex here: 'cleared_locations' comes from memory (grey).
        # Accessibility (red/green) is calculated by LogicEngine (not handled here, but triggered by inv change).
        # This method mainly updates the "Cleared" status from game memory.
        if 'cleared_locations' in data:
            for loc in data['cleared_locations']:
                if loc not in self._manual_location_overrides:
                    self._locations[loc] = "cleared"
                    self.location_changed.emit(loc, "cleared")

        # 3. Update Player Position (Toroidal Wrap Logic)
        if 'player_x' in data and 'player_y' in data:
            new_game_x = data['player_x']
            new_game_y = data['player_y']
            self._update_player_position(new_game_x, new_game_y)

    def _update_player_position(self, game_x: int, game_y: int):
        """
        Calculates canvas position from game coordinates.
        Handles toroidal wrapping visuals if necessary (though straight mapping is usually fine for a 1:1 map).
        """
        # 1. Scale to Canvas
        scale_x = self._canvas_size[0] / self._game_world_size[0]
        scale_y = self._canvas_size[1] / self._game_world_size[1]
        
        canvas_x = game_x * scale_x
        canvas_y = game_y * scale_y
        
        # 2. Toroidal Check (Optional visual smoothing)
        # If the player jumps from 0 to 4096, we might want to suppress animation trails?
        # For a simple dot update, absolute positioning is fine.
        
        # 2. Toroidal Check (Optional visual smoothing)
        # If the player jumps from 0 to 4096, we might want to suppress animation trails?
        # For a simple dot update, absolute positioning is fine.
        
        self._player_pos = QPointF(canvas_x, canvas_y)

    # --- Tracking Options (Granular Filters) ---
    def update_tracking_options(self, options: dict):
        """
        Updates the filter mask for auto-tracking.
        Expected keys: 'chars', 'tools', 'keys', 'maidens', 'pos' (all bools).
        """
        self._tracking_options = options
        logging.info(f"Tracking options updated: {options}")

    def _is_tracking_enabled(self, category: str) -> bool:
        """Returns True if the category is enabled in tracking options (default True)."""
        if not hasattr(self, '_tracking_options'):
             return True # Default allow all if not set
        return self._tracking_options.get(category, True)


    @property
    def obtained_characters(self) -> Dict[str, bool]:
        """Returns all obtained characters (whether in party or not)."""
        return self._characters.copy()

    @property
    def active_party(self) -> set:
        """Returns the set of characters currently in the player's party."""
        return getattr(self, '_active_party', set())

    def get_active_party_leader(self) -> Optional[str]:
        """Returns the name of the first character in the active party (Slot 1)."""
        if hasattr(self, '_active_party_list') and self._active_party_list:
             return self._active_party_list[0]
        return None
        
    def get_character_at_location(self, location_name: str) -> Optional[str]:
        return self._character_locations.get(location_name)

    def set_character_obtained(self, name: str, obtained: bool):
        self._characters[name] = obtained
        self.character_changed.emit(name, obtained)
        
    def assign_character_to_location(self, location: str, character_name: str):
        # 0. Prevent Redundant Updates
        if self._character_locations.get(location) == character_name:
            return

        # 1. Check if character is already assigned elsewhere (Move)
        prev_loc = None
        for loc, name in self._character_locations.items():
            if name == character_name:
                prev_loc = loc
                break
        
        if prev_loc:
             # Remove from old location, but keep obtained status (moving)
             # Just emit unassign so map sprite is removed
             del self._character_locations[prev_loc]
             self.character_unassigned.emit(prev_loc, character_name)

        # 2. Check if location already has someone (Overwrite)
        old_char = self._character_locations.get(location)
        if old_char and old_char != character_name:
             # User says: "Previous character needs to be dimmed" (Reset)
             self.set_character_obtained(old_char, False)
             self.character_unassigned.emit(location, old_char)
             
        # 3. Assign
        self._character_locations[location] = character_name
        self.set_character_obtained(character_name, True)
        
        # 4. Mark Location as "Cleared"
        self.set_manual_location_state(location, "cleared")
        
        # Emit signal for MapWidget
        self.character_assigned.emit(location, character_name)
        
    def remove_character_assignment(self, location: str):
        char = self._character_locations.pop(location, None)
        if char:
            # Logic Parity v1.3: "Removes from inactive but obtained roster"
            # Since inactive roster = obtained=True but not in Active Party,
            # we set obtained=False.
            self.set_character_obtained(char, False)
            self.character_unassigned.emit(location, char)
            logging.info(f"StateManager: Removed {char} from {location} and set to Not Obtained.")

    def register_shop_item(self, location, item_name):
        # Check duplicate
        for entry in self.shop_items:
            if entry['location'] == location and entry['name'] == item_name:
                return
        self.shop_items.append({'location': location, 'name': item_name})
        self.shop_items_changed.emit(self.shop_items)
        
    def unregister_shop_item(self, location, item_name):
        self.shop_items = [e for e in self.shop_items if not (e['location'] == location and e['name'] == item_name)]
        self.shop_items_changed.emit(self.shop_items)
        
    def clear_shop_items(self):
        self.shop_items = []
        self.shop_items_changed.emit(self.shop_items)

    def update_hints(self, text):
        if self.hints_text != text:
             self.hints_text = text
             self.hints_changed.emit(text)

    def toggle_auto_tracking(self, enabled: bool):
        """Starts or stops the C# helper process."""
        if enabled:
            logging.info("Starting Auto-Tracker Helper...")
            self.helper.start()
        else:
            logging.info("Stopping Auto-Tracker Helper...")
            self.helper.stop()

    def on_helper_data(self, data: dict):
        """Callback from HelperInterface thread. Bridges to main thread via signals if needed."""
        self.auto_update_received.emit(data)

    def process_auto_update(self, payload: dict):
        """
        Slot for auto_update_received signal. 
        Process data received from external tracker.
        """
        logging.info(f"Auto-Update Payload Keys: {list(payload.keys())}")
        
        # 0. Store Capsule Mapping (if present)
        if "capsule_sprite_values" in payload:
            self.update_capsule_sprites(payload["capsule_sprite_values"])
        
        # 1. Inventory & Scenario (Keys)
        if self._is_tracking_enabled('tools'):
            new_inventory = {}
            
            # Tools
            if "inventory" in payload:
                for item in payload['inventory']:
                     new_inventory[item] = True
            
            # Keys (Scenario Items)
            if "scenario" in payload:
                for item in payload['scenario']:
                    new_inventory[item] = True
            
            # Update Inventory (Authoritative)
            self._inventory = new_inventory
            
            # Maidens & Inactive Characters (Inferred from Spoiler Log + Cleared Locations)
            if payload.get("spoiler_log"):
                 self.process_spoiler_log(
                     payload['spoiler_log'], 
                     payload.get('cleared_locations', []),
                     payload.get('capsules', []) # Pass obtained capsules for map logic
                 )
            
            # Emit Inventory Change
            self.inventory_changed.emit(self.get_inventory())

        # 2. Characters & Capsules
        if self._is_tracking_enabled('chars'):
            active_list = payload.get('characters', []) # Humans (Party)
            capsule_list = payload.get('capsules', []) # Capsules (Obtained)
            
            # v1.3 Logic Decoupled:
            self._active_party_list = active_list # Store ordered list
            self._active_party = set(active_list)      # Only Humans in Party
            self._obtained_capsules = set(capsule_list) # Only Obtained Capsules
            
            # Mark active humans as obtained
            for name in active_list:
                self.set_character_obtained(name, True)
                
            # Mark obtained capsules as obtained
            for name in capsule_list:
                self.set_character_obtained(name, True)

            # Emit changes (force update on widget to refresh Dim/Lit states)
            for name, obtained in self._characters.items():
                self.character_changed.emit(name, obtained)

        # 3. Locations (Cleared)
        if self._is_tracking_enabled('tools') and 'cleared_locations' in payload:
             payload_cleared = set(payload['cleared_locations'])
             
             # Apply new cleared
             for loc in payload_cleared:
                if loc not in self._manual_location_overrides:
                    if self._locations.get(loc) != "cleared":
                        self._locations[loc] = "cleared"
                        self.location_changed.emit(loc, "cleared")
                        
             # Un-clear locations (Reset Logic)
             # If we have a stored "cleared" state that is NOT in payload, and NOT manual, revert it.
             # We revert by deleting it from _locations (letting LogicEngine determine state)
             to_remove = []
             for loc, state in self._locations.items():
                 if state == "cleared" and loc not in self._manual_location_overrides:
                     if loc not in payload_cleared:
                         to_remove.append(loc)
             
             for loc in to_remove:
                 del self._locations[loc]
                 # We trigger location_changed with "reset" to prompt re-eval?
                 # Or just "unknown"?
                 # Actually, logic engine runs on inventory change.
                 # We should probably emit "reset" or let the next logic pass handle it.
                 # Logic Engine is triggered by `MainWindow._refresh_all` usually.
                 # `inventory_changed` triggers it.
                 # We just removed the "cleared" override.
                 
        # 4. Player Position
        if self._is_tracking_enabled('pos') and 'player_x' in payload and 'player_y' in payload:
             new_game_x = payload['player_x']
             new_game_y = payload['player_y']
             self._update_player_position(new_game_x, new_game_y)
             self.player_position_changed.emit(self._player_pos.x(), self._player_pos.y())

    def _get_capsule_base_name(self, reward_hex_val: str) -> Optional[str]:
        """Maps a Reward Hex (e.g. A502) to the Base Name of the slot (e.g. Jelze)."""
        if not hasattr(self, '_capsule_sprite_mapping') or not self._capsule_sprite_mapping:
            return None
            
        # Iterate our mapping to find index
        # Mapping is List[HexStrings] where Index -> Slot
        try:
            # hex string from JSON might be upper/lower.
            target = reward_hex_val.upper()
            if target in self._capsule_sprite_mapping:
                idx = self._capsule_sprite_mapping.index(target)
                # Slot Index -> Base Name
                base_names = ["Jelze", "Flash", "Gusto", "Zeppy", "Darbi", "Sully", "Blaze"]
                if 0 <= idx < len(base_names):
                    return base_names[idx]
        except ValueError:
            pass
        return None

    def reset_state(self):
        """Reset all tracker state to defaults (but keep options)."""
        logging.info("Resetting tracker state to defaults.")
        self._inventory = {}
        self._characters = {}
        self._active_party = set()
        self._obtained_capsules = set()
        
        self.reset_overrides()
        
        # Unassign all map sprites explicitly
        for loc, char in list(self._character_locations.items()):
            self.character_unassigned.emit(loc, char)
        self._character_locations = {}
        
        # Locations reset
        self._locations = {}
        self.location_changed.emit("Reset", "reset") 
        
        # Emit all signals to clear UI
        self.inventory_changed.emit({})
        self.clear_shop_items()
        
        self.hints_text = ""
        # hints UI cleared by MainWindow._on_reset_occurred
        
        # Characters:
        for name in ["Maxim", "Selan", "Guy", "Artea", "Tia", "Dekar", "Lexis", "Jelze", "Flash", "Gusto", "Zeppy", "Darbi", "Sully", "Blaze"]:
            self.character_changed.emit(name, False)
        
        self.player_position_changed.emit(0, 0)
        
        self.reset_occurred.emit()



    def register_spoiler_location(self, location: str, character_name: str):
        """
        Registers a potential character location from the spoiler log.
        Does NOT mark as obtained or cleared.
        """
        # Update internal map
        self._character_locations[location] = character_name
        # Emit signal so MapWidget can place the sprite (if location not cleared)
        self.character_assigned.emit(location, character_name)

    def process_spoiler_log(self, spoiler_log: list, cleared_lines: list, obtained_capsules: list):
        """
        Maps spoiler log to map sprites and character states.
        Strict v1.3 Logic: Only assign to Map if Obtained/Cleared.
        """
        # Cache for re-processing when C# data arrives
        self._last_spoiler_args = (spoiler_log, cleared_lines, obtained_capsules)
        
        cleared_set = set(cleared_lines)
        obtained_capsules_set = set(obtained_capsules)
        
        maiden_map = {"Clare": "Claire", "Lisa": "Lisa", "Marie": "Marie"}
        possible_chars = {
             "Maxim", "Selan", "Guy", "Artea", "Tia", "Dekar", "Lexis",
             "Jelze", "Flash", "Gusto", "Zeppy", "Darbi", "Sully", "Blaze" 
        }
        
        # Hex Mapping Table for Rewards -> Hex
        reward_hex_map = {
             "Foomy S": "4600",
             "Shaggy": "A502",
             "Hard Hat": "4305",  
             "Red Fish": "AF07",  
             "Myconido": "580A",  
             "Raddisher": "0B0D",  
             "Armor Dog": "880F",
        }

        capsule_count = 0
        
        for entry in spoiler_log:
            item = entry.get('item')
            raw_loc = entry.get('location')
            loc = self._normalize_location_name(raw_loc)
            
            entity_name = item
            is_maiden = False
            is_capsule = False
            is_char = False
            
            # 1. Maiden Check
            if item in maiden_map:
                entity_name = maiden_map[item]
                is_maiden = True
            elif item in reward_hex_map:
                 # 2. Capsule Mapping Logic (Order Based)
                 # "The first listed capsule reward... corresponds to Slot 0"
                 if hasattr(self, 'capsule_sprites') and self.capsule_sprites and capsule_count < len(self.capsule_sprites):
                      hex_val = self.capsule_sprites[capsule_count]
                      
                      base_name = self._get_capsule_base_name(hex_val)
                      
                      if base_name:
                          entity_name = base_name
                          is_capsule = True
                      
                      capsule_count += 1
                 else:
                      # Fallback: Don't map?
                      pass
            else:
                pass # Normal processing
                
                # Check if it resolved to a known character/capsule
                if entity_name in possible_chars:
                    if entity_name in ["Jelze", "Flash", "Gusto", "Zeppy", "Darbi", "Sully", "Blaze"]:
                         is_capsule = True
                    else:
                         is_char = True
            
            if not (is_maiden or is_char or is_capsule):
                continue
                
            # v1.3 Logic Implementation:
            
            if is_maiden:
                if loc in cleared_set:
                    self._inventory[entity_name] = True
                    # Maidens don't go on specific map location in v1.3? 
                    # They are just "Obtained".
                    # But we can show "Found At" text if we want.
                    self.register_spoiler_location(loc, entity_name) 

            elif is_char:
                # Humans: Only on Map if Location is Cleared
                if loc in cleared_set:
                    self.set_character_obtained(entity_name, True)
                    self.register_spoiler_location(loc, entity_name)
                    
            elif is_capsule:
                # Capsules: Only on Map if Capsule is Obtained (Value != 0)
                # Note: v1.3 checks if *that specific capsule slot* is valid.
                # Here we check if `entity_name` (Base Name) is in obtained_capsules list.
                if entity_name in obtained_capsules_set:
                     self.set_character_obtained(entity_name, True)
                     self.register_spoiler_location(loc, entity_name)
        
        # Note: inventory_changed emitted by caller

    def save_state(self, filepath: str):
        """Serialize current overrides AND progress to JSON."""
        data = {
            "inventory_overrides": self._manual_inventory_overrides,
            "location_overrides": self._manual_location_overrides,
            "character_locations": self._character_locations,
            # "character_obtained": self._characters, # We want full state? 
            # If we save _characters, we save the auto-tracked state.
            
            # Full State
            "inventory": self._inventory,
            "locations": self._locations,
            "characters": self._characters,
            "active_party": list(self._active_party),
            "obtained_capsules": list(self._obtained_capsules),
            "capsule_mapping": self._capsule_sprite_mapping,
            "shop_items": self.shop_items,
            "hints": self.hints_text
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logging.info(f"State saved to {filepath}")

    def load_state(self, filepath: str):
        """Load state from JSON and apply."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self._manual_inventory_overrides = data.get("inventory_overrides", {})
        self._manual_location_overrides = data.get("location_overrides", {})
        
        # Restore State
        self._inventory = data.get("inventory", {})
        self._locations = data.get("locations", {})
        self._characters = data.get("characters", {})
        self._character_locations = data.get("character_locations", {})
        
        self.shop_items = data.get("shop_items", [])
        self.shop_items_changed.emit(self.shop_items)
        
        self.hints_text = data.get("hints", "")
        self.hints_changed.emit(self.hints_text)
        
        self._active_party = set(data.get("active_party", []))
        self._obtained_capsules = set(data.get("obtained_capsules", []))
        self._capsule_sprite_mapping = data.get("capsule_mapping", {})
        
        # Re-emit changes
        self.inventory_changed.emit(self.inventory)
        for loc, state in self._locations.items():
            self.location_changed.emit(loc, state)
        
        # We need to re-emit character assignments essentially to place sprites
        # Clear existing sprites? MainWindow doesn't have "clear all sprites" method exposed easily
        # inside `load_state`. 
        # But we can iterate known locations and emit.
        
        for loc, char in self._character_locations.items():
             self.character_assigned.emit(loc, char)
            
        # Also emit character toggles
        for char, obtained in self._characters.items():
            self.character_changed.emit(char, obtained)
            
        logging.info(f"State loaded from {filepath}")

    def update_capsule_sprites(self, sprites: list):
        """Called by Logic/TrackerClient when C# sends new sprite data."""
        self.capsule_sprites = sprites
        self._capsule_sprite_mapping = sprites 
        
        logging.info(f"StateManager: Received {len(sprites)} capsule sprites.")
        
        # Trigger re-mapping if we have potential spoiler data waiting
        if hasattr(self, '_last_spoiler_args') and self._last_spoiler_args:
            logging.info("StateManager: Re-processing spoiler log with new capsule data.")
            self.process_spoiler_log(*self._last_spoiler_args)

