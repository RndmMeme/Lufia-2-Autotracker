import json
import pymem
import os
import logging
import shared

class ItemLookup:
    def __init__(self, json_path):
        with open(json_path, 'r') as file:
            self.items_spells = json.load(file)

    def get_item_name(self, category, value):
        category_data = self.items_spells.get(category)
        if category_data:
            item_name = category_data.get(value)
            if item_name:
                return item_name
            else:
                return None
        else:
            return None

def read_rom_start_address(process, pointer_base_address):
    process = shared.config['process']
    pointer_base_address += shared.config['base_address']
    try:
        raw_address = process.read_bytes(pointer_base_address, 4)
        if raw_address:
            reversed_bytes = raw_address[::-1]
            print(f"raw address:", {reversed_bytes})
            return reversed_bytes.hex()
        else:
            raise ValueError("Failed to read ROM start address.")
    except Exception as e:
        logging.error(f"Error reading ROM start address: {e}")
        return None

def calculate_shop_pointer(reversed_bytes, shop_offset):
    if reversed_bytes is not None:
        base_address = int(reversed_bytes, 16)
        final_address = base_address + shop_offset
        return hex(final_address)
    return None

def verify_shop_pointer(process, shop_pointer):
    try:
        address_int = int(shop_pointer, 16)
        verification_bytes = process.read_bytes(address_int, 4)
        if verification_bytes:
            valid = verification_bytes.hex() == '029c0002'
            return valid
        else:
            return False
    except Exception as e:
        logging.error(f"Error verifying shop pointer: {e}")
        return False

def process_shop_data(app):
    try:
        reversed_bytes = read_rom_start_address(app.process, shared.pointer_base_address)
        if reversed_bytes is None:
            raise ValueError("Could not read ROM start address.")

        base_address = int(reversed_bytes, 16)

        if "shops" in shared.shop_addresses:
            shops = shared.shop_addresses["shops"]
        else:
            raise ValueError("shop_addresses does not contain 'shops' key or is not a dictionary.")

        adjusted_shop_data = adjust_shop_item_ranges(shops, base_address)
        shop_items = read_shop_items(app.process, adjusted_shop_data, app)

        return adjusted_shop_data, shop_items
    except Exception as e:
        logging.error(f"Error processing shop data: {e}")
        raise

def adjust_shop_item_ranges(shops, base_address):
    adjusted_addresses = {}
    for shop in shops:
        city = shop.get("city")
        if not city:
            continue

        adjusted_addresses[city] = {}
        for category, offsets in shop.items():
            if category == "city" or offsets is None:
                continue
            try:
                start_offset, end_offset = offsets.split('-')
                start_offset = int(start_offset, 16)
                end_offset = int(end_offset, 16)
                adjusted_start = base_address + start_offset
                adjusted_end = base_address + end_offset
                adjusted_addresses[city][category] = f"{hex(adjusted_start)}-{hex(adjusted_end)}"
            except Exception as e:
                logging.error(f"Error processing offsets for {city} in category {category}: {e}")
    return adjusted_addresses

def find_item_name_in_category(category, value_hex, app):
    try:
        items_spells_path = os.path.join(app.data_dir, "items_spells.json")
        with open(items_spells_path, 'r') as f:
            items_spells = json.load(f)
        category = category.capitalize()
        if category in items_spells and value_hex in items_spells[category]:
            item_name = items_spells[category][value_hex]
            return item_name
        else:
            return None
    except Exception as e:
        logging.error(f"Error finding item name for category {category}, value {value_hex}: {e}")
        return None

def scan_weapons(process, start_addr, end_addr, app):
    category_items = []
    last_weapon_addr = None
    for address in range(start_addr, end_addr + 1, 2):
        value1 = process.read_bytes(address, 2)
        value2 = process.read_bytes(address + 1, 2)
        if value1 and len(value1) == 2:
            value1_hex = f"{value1[0]:02X}{value1[1]:02X}"
            item_name1 = find_item_name_in_category("weapon", value1_hex, app)
            if item_name1:
                category_items.append((item_name1, value1_hex))
                last_weapon_addr = address

        if value2 and len(value2) == 2:
            value2_hex = f"{value2[0]:02X}{value2[1]:02X}"
            item_name2 = find_item_name_in_category("weapon", value2_hex, app)
            if item_name2:
                category_items.append((item_name2, value2_hex))
                last_weapon_addr = address + 1

    return category_items, last_weapon_addr

def scan_armor(process, start_addr, end_addr, app):
    category_items = []
    for address in range(start_addr, end_addr + 1, 2):
        value = process.read_bytes(address, 2)
        if value:
            value1_hex = f"{value[0]:02X}{value[1]:02X}"
            value2_hex = f"{value[1]:02X}{value[0]:02X}"
            item_name1 = find_item_name_in_category("armor", value1_hex, app)
            item_name2 = find_item_name_in_category("armor", value2_hex, app)
            if item_name1:
                category_items.append((item_name1, value1_hex))
            elif item_name2:
                category_items.append((item_name2, value2_hex))
    return category_items

def scan_spells(process, start_addr, end_addr, app):
    category_items = []
    for address in range(start_addr, end_addr + 1):
        value = process.read_bytes(address, 1)
        if value and value[0] == 0xFF:
            break
        if value:
            value_hex = f"{value[0]:02X}"
            item_name = find_item_name_in_category("spell", value_hex, app)
            if item_name:
                category_items.append((item_name, value_hex))
    return category_items

def read_shop_items(process, adjusted_addresses, app):
    items = {}
    for city, categories in adjusted_addresses.items():
        items[city] = {}
        last_weapon_addr = None
        for category, address_range in categories.items():
            start_addr, end_addr = map(lambda x: int(x, 16), address_range.split('-'))
            category_items = []

            if category.lower() == "weapon":
                weapon_items, last_weapon_addr = scan_weapons(process, start_addr, end_addr, app)
                items[city][category] = weapon_items

            if category.lower() == "armor":
                if last_weapon_addr is not None:
                    armor_items = scan_armor(process, last_weapon_addr + 2, end_addr, app)
                    items[city][category] = armor_items
                else:
                    items[city][category] = []

            if category.lower() == "spell":
                spell_items = scan_spells(process, start_addr, end_addr, app)
                items[city][category] = spell_items

    return items

def get_shop_items(app, location, category, adjusted_shop_data):
    if location in adjusted_shop_data and category in adjusted_shop_data[location]:
        address_range = adjusted_shop_data[location][category]
        start_addr, end_addr = map(lambda x: int(x, 16), address_range.split('-'))
        items = []
        if category.lower() == "weapon":
            items, last_weapon_addr = scan_weapons(app.process, start_addr, end_addr, app)

        if category.lower() == "armor":
            if last_weapon_addr is not None:
                items = scan_armor(app.process, last_weapon_addr + 2, end_addr, app)
            else:
                items = []

        if category.lower() == "spell":
            items = scan_spells(app.process, start_addr, end_addr, app)

        return items
    else:
        logging.debug(f"No data for {location} in category {category}.")
        return []

def save_shop_data_to_json(shop_data, file_path):
    try:
        with open(file_path, 'w') as json_file:
            json.dump(shop_data, json_file, indent=4)
        logging.info(f"Shop data successfully saved to {file_path}")
    except Exception as e:
        logging.error(f"Error saving shop data to JSON: {e}")

def process_and_save_shop_data(app, json_path):
    adjusted_shop_data, shop_items = process_shop_data(app)
    save_shop_data_to_json(shop_items, json_path)
    return adjusted_shop_data, shop_items
