# inventory_scan.py

import os
from shared import LOCATION_LOGIC, load_json_cached, DATA_DIR
from helpers.file_loader import load_image
from helpers.memory_utils import read_memory
from canvas_config import load_image_cached, update_character_image

# Memory addresses for character slots
CHARACTER_SLOT_ADDRESSES = [
    0xA32D8F,
    0xA32D90,
    0xA32D91,
    0xA32D92
]

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

class InventoryScanner:
    def __init__(self, app, tools_canvas, tool_images, location_labels):
        self.app = app
        self.tools_canvas = tools_canvas
        self.tool_images = tool_images
        self.tool_items = load_json_cached(DATA_DIR / 'tool_items.json')
        self.location_labels = location_labels

    def scan_inventory(self, process, base_address, obtained_items):
        INVENTORY_START = 0xA32DA1
        INVENTORY_END = 0xA32E60

        new_obtained_items = set()
        for tool_name, tool_info in self.tool_items.items():
            obtained_value = int(tool_info["obtained_value"], 16)
            tool_obtained = self.scan_for_item(process, base_address, INVENTORY_START, INVENTORY_END, obtained_value)
            if tool_obtained and tool_name not in obtained_items:
                new_obtained_items.add(tool_name)
                self.app.root.after(0, self.replace_tool_image, tool_name)

        obtained_items.update(new_obtained_items)
        self.update_accessible_locations(obtained_items)

    def scan_for_item(self, process, base_address, start_address, end_address, item_value):
        item_bytes = item_value.to_bytes(2, byteorder='little')
        for address in range(start_address, end_address, 2):
            memory_value = read_memory(process, base_address + address, 2)
            if memory_value == item_bytes:
                return True
        return False

    def replace_tool_image(self, tool_name):
        tool_image_path = self.tool_items[tool_name]["image_path"]
        colored_tool_image = load_image(tool_image_path)
        if colored_tool_image:
            tool_image_info = self.tool_images.get(tool_name)
            if tool_image_info:
                position = tool_image_info['position']
                self.tools_canvas.itemconfig(position, image=colored_tool_image)
                if not hasattr(self.tools_canvas, 'images'):
                    self.tools_canvas.images = []
                self.tools_canvas.images.append(colored_tool_image)

    def update_accessible_locations(self, obtained_items):
        new_accessible_locations = set()
        for location, logic in LOCATION_LOGIC.items():
            access_rules = logic.get("access_rules", [])
            if any(all(item in obtained_items for item in rule.split(',')) for rule in access_rules):
                new_accessible_locations.add(location)

        for location in new_accessible_locations:
            self.app.root.after(0, self.mark_location_accessible, location)

    def mark_location_accessible(self, location):
        dot, label = self.location_labels.get(location, (None, None))
        if dot and label:
            self.app.canvas.itemconfig(dot, fill="lightgreen")
            self.app.canvas.itemconfig(label, fill="lightgreen")

class ScenarioScanner:
    def __init__(self, app, scenario_canvas, scenario_images, location_labels):
        self.app = app
        self.scenario_canvas = scenario_canvas
        self.scenario_images = scenario_images
        self.scenario_items = load_json_cached(DATA_DIR / 'scenario_items.json')
        self.location_labels = location_labels

    def scan_scenario(self, process, base_address, obtained_items):
        SCENARIO_START = 0xA32C32
        SCENARIO_END = 0xA32C37

        memory_value = read_memory(process, base_address + SCENARIO_START, SCENARIO_END - SCENARIO_START + 1)
        reversed_memory_value = memory_value[::-1]
        binary_string = ''.join(f'{byte:08b}' for byte in reversed_memory_value)

        new_obtained_items = set()
        for bit_position, bit_value in enumerate(binary_string):
            if bit_value == '1':
                obtained_index = len(binary_string) - bit_position
                obtained_index_hex = hex(obtained_index)[2:].zfill(2).upper()

                for scenario_name, scenario_info in self.scenario_items.items():
                    obtained_value_bin = scenario_info["obtained_value"].replace(' ', '')
                    if len(obtained_value_bin) >= obtained_index:
                        if obtained_value_bin[-obtained_index] == '1' and scenario_name not in obtained_items:
                            new_obtained_items.add(scenario_name)
                            print(f"{scenario_name} item obtained")
                            self.app.root.after(0, self.replace_scenario_image, scenario_name)

        obtained_items.update(new_obtained_items)
        self.update_accessible_locations(obtained_items)

    def replace_scenario_image(self, scenario_name):
        scenario_image_path = self.scenario_items[scenario_name].get("image_path")
        if scenario_image_path:
            colored_scenario_image = load_image(scenario_image_path)
            if colored_scenario_image:
                scenario_image_info = self.scenario_images.get(scenario_name)
                if scenario_image_info:
                    position = scenario_image_info['position']
                    self.scenario_canvas.itemconfig(position, image=colored_scenario_image)
                    if not hasattr(self.scenario_canvas, 'images'):
                        self.scenario_canvas.images = []
                    self.scenario_canvas.images.append(colored_scenario_image)

    def update_accessible_locations(self, obtained_items):
        new_accessible_locations = set()
        for location, logic in LOCATION_LOGIC.items():
            access_rules = logic.get("access_rules", [])
            if any(all(item in obtained_items for item in rule.split(',')) for rule in access_rules):
                new_accessible_locations.add(location)

        for location in new_accessible_locations:
            self.app.root.after(0, self.mark_location_accessible, location)

    def mark_location_accessible(self, location):
        dot, label = self.location_labels.get(location, (None, None))
        if dot and label:
            self.app.canvas.itemconfig(dot, fill="lightgreen")
            self.app.canvas.itemconfig(label, fill="lightgreen")

class CharacterScanner:
    def __init__(self, app, process, base_address, canvas, character_images, image_cache):
        self.app = app
        self.process = process
        self.base_address = base_address
        self.canvas = canvas
        self.character_images = character_images
        self.image_cache = image_cache
        self.active_characters = set()  # Track currently active characters
        print(f"CharacterScanner initialized with base_address: 0x{self.base_address:X}")

    def scan(self):
        if self.base_address is None:
            print("Error: base_address is None in CharacterScanner.scan")
            return

        try:
            self.active_characters.clear()  # Clear the active characters set
            for slot_index, offset in enumerate(CHARACTER_SLOT_ADDRESSES):
                address = self.base_address + offset
                print(f"Attempting to read character slot at computed address 0x{address:X} (base: 0x{self.base_address:X} + offset: 0x{offset:X})")

                try:
                    byte_value = read_memory(self.process, address, 1)
                    character_id = byte_value[0]
                    character_name = CHARACTER_BYTE_MAPPING.get(character_id, "Unknown")

                    if character_name != "Unknown" and character_name != "Empty":
                        print(f"Character {character_name} is in slot {slot_index + 1}.")
                        self.active_characters.add(character_name)  # Add to active characters set
                        update_character_image(self.canvas, self.character_images, character_name, True)
                    else:
                        print(f"No character or unrecognized byte value {character_id} in slot {slot_index + 1}.")

                except Exception as e:
                    print(f"Unexpected error reading character slot at address 0x{address:X}: {e}")

            # Dim the characters not in the active party
            for character_name in self.character_images:
                if character_name not in self.active_characters:
                    update_character_image(self.canvas, self.character_images, character_name, False)

        except Exception as e:
            print(f"Error scanning character slots: {e}")
