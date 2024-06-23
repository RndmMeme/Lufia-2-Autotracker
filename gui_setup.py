# gui_setup.py

from canvas_config import (
    setup_canvas,
    setup_tools_canvas,
    setup_scenario_canvas,
    setup_maidens_canvas,
    setup_characters_canvas,
    create_tabbed_interface,
    update_character_image
)
from button_functions import sync_game_state, clear_game_state, save_game_state, load_game_state
from inventory_scan import InventoryScanner, ScenarioScanner, CharacterScanner
import tkinter as tk
from tkinter import ttk, filedialog
import datetime
import time
import os
from shared import characters, characters_bw, CITIES, shop_addresses, item_spells, WIDGET_STORE
from helpers.memory_utils import read_memory_with_retry


def setup_interface(app):
    """
    Set up the main interface of the application.
    """
    
    app.root.geometry("978x728")
    app.root.bind("<Configure>", app.on_resize)
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.tabs = {}
    create_menu(app)

def setup_canvases(app):
    """
    Set up the various canvases in the application.
    """
    print("Setting up main canvas...")
    app.canvas, app.map_image, app.map_photo, app.location_labels = setup_canvas(
        app.root, app.map_address, app.LOCATIONS, app.locations_logic, app.inventory, app.scenario_items,
        dot_click_callback=app.on_dot_click, 
        right_click_callback=lambda event, loc: right_click_handler(app, event, loc)
    )

    print("Setting up tools canvas...")
    app.tools_canvas, app.tool_images = setup_tools_canvas(
        app.root, list(app.tool_items_bw.keys()), app.on_tool_click, app.image_cache
    )

    print("Setting up scenario canvas...")
    app.scenario_canvas, app.scenario_images = setup_scenario_canvas(
        app.root, list(app.scenario_items_bw.keys()), app.item_to_location, app.on_scenario_click, app.image_cache
    )

    print("Setting up characters canvas...")
    app.characters_canvas, app.character_images = setup_characters_canvas(app.root, app.characters, app.image_cache, app)

    print("Setting up maidens canvas...")
    app.maidens_canvas, app.maidens_images = setup_maidens_canvas(app.root, app.characters, app.characters_bw, app.image_cache, app.check_all_maidens_colored)

    print("Setting up tabbed interface...")
    app.tabbed_interface, app.tabs = create_tabbed_interface(app.root)

def setup_scanners(app):
    """
    Set up the scanners for inventory and scenarios.
    """
    if app.base_address is None:
        print("Error: base_address is None during scanner setup.")
        return  # Early return if base_address is not valid
    
    app.scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
    app.sscanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
    app.cscanner = CharacterScanner(app, app.process, app.base_address, app.characters_canvas, app.character_images, app.image_cache)

def create_menu(app):
    """
    Create the application menu.
    """
    menubar = tk.Menu(app.root)
    app.root.config(menu=menubar)
    
    options_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Options", menu=options_menu)
    
    options_menu.add_command(label="Clear", command=lambda: clear_game_state(app))
    options_menu.add_command(label="Sync", command=lambda: sync_game_state(app))
    options_menu.add_command(label="Save", command=lambda: save_game_state(app))  # Added save option
    options_menu.add_command(label="Load", command=lambda: load_game_state(app))
    options_menu.add_command(label="Location Names", command=app.toggle_location_labels)
    options_menu.add_command(label="Toggle City Names", command=app.toggle_city_labels)

    print("Menu created successfully.")
  
def right_click_handler(app, event, location):
    if location in CITIES:
        # Show city-specific context menu
        show_city_context_menu(app, event, location)
    else:
        # Show regular location context menu (e.g., for characters)
        show_context_menu(app, event, location) 
    

def show_context_menu(app, event, location):
    context_menu = tk.Menu(app.root, tearoff=0)
    
    if location in shop_addresses:
        # Location is a city with shops
        context_menu.add_command(label="Weapon", command=lambda: show_shop_menu(app, location, "Weapon"))
        context_menu.add_command(label="Armor", command=lambda: show_shop_menu(app, location, "Armor"))
        context_menu.add_command(label="Spell", command=lambda: show_shop_menu(app, location, "Spell"))
        context_menu.add_command(label="Thief", command=lambda: store_thief_location(app, location))
        context_menu.add_command(label="Iris", command=lambda: show_iris_menu(app, location))
    else:
        # For other locations, provide the character menu
        context_menu.add_command(label="Character", command=lambda: show_character_menu(app, location))
    
    context_menu.post(event.x_root, event.y_root)
    
def show_city_context_menu(app, event, location):
    context_menu = tk.Menu(app.root, tearoff=0)
    context_menu.add_command(label="Weapon", command=lambda: show_shop_menu(app, location, "Weapon"))
    context_menu.add_command(label="Armor", command=lambda: show_shop_menu(app, location, "Armor"))
    context_menu.add_command(label="Spell", command=lambda: show_shop_menu(app, location, "Spell"))
    context_menu.add_command(label="Thief", command=lambda: store_thief_location(app, location))
    context_menu.add_command(label="Iris", command=lambda: show_iris_menu(app, location))
    context_menu.post(event.x_root, event.y_root)


def get_shop_items(app, location, category):
    # Retrieve the appropriate address range for the category
    shop_data = next((shop for shop in shop_addresses['shops'] if shop['city'].lower() == location.lower()), None)
    print(f"Shop data for location '{location}': {shop_data}")

    if not shop_data:
        print(f"No shop data found for location {location}.")
        return []

    category_range = shop_data.get(category.lower())
    print(f"Category range for '{category}' in location '{location}': {category_range}")

    if not category_range:
        print(f"No range specified for {category} in {location}.")
        return []

    # Read the memory within the specified range
    start_addr, end_addr = map(lambda x: int(x, 16), category_range.split('-'))
    print(f"Reading memory range for {category} in {location}: {hex(start_addr)} to {hex(end_addr)}")

    items = []
    for address in range(start_addr, end_addr + 1, 2):  # Assuming 2-byte values
        print(f"Attempting to read memory at address {hex(address)}")
        try:
            # Use appropriate Pymem method for reading memory
            value = app.process.read_short(address)  # Assuming reading 2 bytes (short) values
            if value is not None:
                # Reverse the bytes (e.g., 0x3700 -> 0x0037)
                reversed_value = reverse_bytes(value)
                print(f"Read value {hex(value)} at address {hex(address)}, reversed to {hex(reversed_value)}")

                # Convert to match the JSON structure
                value_hex = f"{reversed_value:02X}"  # Format as 2-digit hex value
                print(f"Formatted hex value: {value_hex}")

                # Lookup the item name in the specified category
                item_name = find_item_name_in_category(app, category, value_hex)

                if item_name:
                    items.append((item_name, value_hex))  # Append tuple (item_name, hex_value)
            else:
                print(f"Error reading memory at {hex(address)}: No data")
        except Exception as e:
            print(f"Error reading memory at {hex(address)}: {e}")

    return items


def reverse_bytes(value):
    """
    Reverse the bytes of a 2-byte value (short).
    E.g., 0x3700 -> 0x0037
    """
    # Convert value to 2 bytes in little-endian order and then reverse them
    byte1 = value & 0xFF
    byte2 = (value >> 8) & 0xFF
    reversed_value = (byte1 << 8) | byte2
    return reversed_value

def find_item_name_in_category(app, category, hex_value):
    # Mapping from context menu option to JSON category
    category_mapping = {
        'Weapon': 'Weapons',
        'Armor': 'Armor',
        'Spell': 'Spells',
        'Iris': 'Iris Treasures'
    }
    
    # Get the correct category to search within
    json_category = category_mapping.get(category, None)
    
    if not json_category:
        print(f"Unknown category '{category}'. Available categories: {list(category_mapping.keys())}")
        return None
    
    category_items = item_spells.get(json_category, {})

    print(f"Searching for value {hex_value} in category {json_category}")

    item_name = category_items.get(hex_value.upper())
    if item_name:
        print(f"Found {item_name} for value {hex_value}")
        return item_name
    else:
        print(f"No match found for value {hex_value} in category {json_category}")

    return None


def show_shop_menu(app, location, category):
    shop_items = get_shop_items(app, location, category)
    print(f"Shop items for {category} in {location}: {shop_items}")

    # Create a submenu for the shop items
    submenu = tk.Menu(app.root, tearoff=0)

    for item_name, hex_value in shop_items:
        # Add the items to the submenu, binding the command to store the item
        submenu.add_command(
            label=item_name,
            command=lambda item=item_name: store_shop_item(app, location, item, hex_value, category)
        )

    # Display the submenu
    submenu.post(app.root.winfo_pointerx(), app.root.winfo_pointery())


def store_shop_item(app, location, item_name, hex_value, category):
    print(f"Storing item {item_name} from {location} in category {category}")
    
    if category in ["Weapon", "Armor", "Iris"]:
        tab_name = "Shop Item"
    elif category == "Spell":
        tab_name = "Spell"
    elif category == "Thief":
        tab_name = "Thief"
    else:
        tab_name = None
    
    if tab_name:
        tab = app.tabs.get(tab_name)
        
        if tab_name == "Hints":
            # Handle Hints tab separately if needed
            pass
        else:
            # For other tabs, assume they are scrollable frames
            # Create a label with the item name and add it to the tab's frame
            label = ttk.Label(tab, text=f"{location}: {item_name} ({hex_value})")
            label.pack(pady=2, padx=2, anchor='w')
            
            # Create a button to remove the entry
            remove_button = ttk.Button(tab, text="-", command=lambda: label.pack_forget())
            remove_button.pack(pady=2, padx=2, anchor='w')
    else:
        print(f"No tab found for category {category}")


def get_item_price(hex_value):
    # Placeholder for the actual function to get the item's price based on hex value
    # You might need to implement reading the price from memory or some other source
    return "N/A"

def store_thief_location(app, location):
    add_item_to_tab(app, "Thief", f"Thief spotted in {location}")

def show_iris_menu(app, location):
    iris_items = get_shop_items(app, location, "Iris")
    if not iris_items:
        print(f"No Iris treasures found in {location}.")
        return

    iris_menu = tk.Menu(app.root, tearoff=0)
    for item in iris_items:
        iris_menu.add_command(label=item, command=lambda item=item: store_shop_item(app, location, item, "Iris"))
    
    iris_menu.post(app.root.winfo_pointerx(), app.root.winfo_pointery())

# Modify the add_item_to_tab function to use Text widget if available
def add_item_to_tab(tab_frame, city, item_name):
    """
    Adds a new item entry to the specified tab.
    """
    if isinstance(tab_frame, ttk.Treeview):
        print(f"Adding {city}: {item_name} to the Treeview in the tab")
        # Insert the item into the Treeview
        tab_frame.insert("", "end", values=(city, item_name))
        
        # Debugging: Print all current items in the Treeview
        for child in tab_frame.get_children():
            print("Treeview child:", tab_frame.item(child)["values"])
    else:
        print("Tab frame is not a Treeview. Attempting to add to a frame.")
        # Fallback to the old method if the tab_frame is not a Treeview (for other tabs)
        item_frame = ttk.Frame(tab_frame)
        current_row = len(tab_frame.winfo_children())

        item_label = ttk.Label(item_frame, text=f"{city}: {item_name}", foreground='black')
        item_label.grid(row=0, column=0, sticky='w', padx=5)

        remove_button = ttk.Button(item_frame, text="–", width=2, command=item_frame.destroy)
        remove_button.grid(row=0, column=1, sticky='e', padx=5)

        item_frame.grid(row=current_row, column=0, sticky='ew', pady=2)

        tab_frame.grid_rowconfigure(current_row, weight=1)
        tab_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Debug.TFrame", background="yellow")
        item_frame.configure(style="Debug.TFrame")

        tab_frame.update_idletasks()
        
        if hasattr(tab_frame, 'canvas'):
            tab_frame.canvas.configure(scrollregion=tab_frame.canvas.bbox("all"))

        for i, child in enumerate(tab_frame.winfo_children()):
            if isinstance(child, ttk.Frame):
                child_text = child.winfo_children()[0].cget("text") if child.winfo_children() else "Non-label widget"
                child_position = child.grid_info()
                print(f"Child {i} in tab: {child_text} at row {child_position['row']}, column {child_position['column']}")


def remove_entry(entry_frame):
    entry_frame.destroy()


def remove_entry_from_listbox(listbox):
    selected_index = listbox.curselection()
    if selected_index:
        listbox.delete(selected_index)
        



def show_character_menu(app, location):
    """
    Show character selection menu for assigning a character to the specified location.
    """
    character_menu = tk.Menu(app.root, tearoff=0)

    # Get characters that are not active and not colored
    available_characters = [name for name in app.character_images if name not in app.active_characters and not app.character_images[name]['is_colored']]
    for name in available_characters:
        character_menu.add_command(label=name, command=lambda name=name: assign_character_to_location(app, name, location))
    
    character_menu.post(app.root.winfo_pointerx(), app.root.winfo_pointery())

def assign_character_to_location(app, character_name, location):
    """
    Assign the selected character to the specified location and update the display.
    """
    app.manual_toggles[character_name] = True
    update_character_image(app.characters_canvas, app.character_images, character_name, True)
    # Add the location label above the character image
    char_info = app.character_images[character_name]
    char_position = app.characters_canvas.coords(char_info['position'])
    app.characters_canvas.create_text(char_position[0] + 20, char_position[1] - 15, text=location, fill="white", anchor="n")
    print(f"Assigned {character_name} to {location}")

def assign_capsule_to_location(app, capsule_name, location):
    """
    Assign the selected capsule to the specified location and update the display.
    """
    app.manual_toggles[capsule_name] = True
    update_character_image(app.characters_canvas, app.character_images, capsule_name, True)
    # Add the location label above the capsule image
    cap_info = app.character_images[capsule_name]
    cap_position = app.characters_canvas.coords(cap_info['position'])
    app.characters_canvas.create_text(cap_position[0] + 20, cap_position[1] - 15, text=location, fill="white", anchor="n")
    print(f"Assigned {capsule_name} to {location}")




