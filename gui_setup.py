# gui_setup.py

from canvas_config import (
    setup_item_canvas,
    setup_tools_canvas,
    setup_scenario_canvas,
    setup_maidens_canvas,
    setup_characters_canvas,
    setup_hints_canvas,
    setup_canvas,
    update_character_image
)
from button_functions import sync_game_state, save_game_state, load_game_state
from inventory_scan import InventoryScanner, ScenarioScanner, CharacterScanner
import tkinter as tk
from tkinter import ttk, filedialog, Label
import datetime
import time
import os
import json
import logging
import tkinter.font as tkFont
from shop_calc import read_shop_items, process_shop_data
from shared import characters, characters_bw, CITIES, shop_addresses, item_spells, WIDGET_STORE
from helpers.memory_utils import read_memory_with_retry

def setup_interface(app):
    """
    Set up the main interface of the application.
    """
    app.root.geometry("870x802")  # Adjusted to a larger view for better visibility
    app.root.bind("<Configure>", app.on_resize)
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    style = ttk.Style()
    style.configure('Custom.TFrame', background='black')
    style.configure('Custom.TLabel', foreground='white', background='black')
    style.configure('Custom.TButton', width=2)
    
    create_menu(app)
    
    app.root.update()  # Force update
    
def setup_canvases(app):
    """
    Set up the various canvases in the application.
    """
    app.canvas, app.map_image, app.map_photo, app.location_labels, app.autoscan_label = setup_canvas(
        app.root, app.map_address, app.LOCATIONS, app.locations_logic, app.inventory, app.scenario_items,
        dot_click_callback=app.on_dot_click, 
        right_click_callback=lambda event, loc: right_click_handler(app, event, loc),
        
    )
    
    app.item_canvas = setup_item_canvas(app.root)
    
    app.hints_canvas = setup_hints_canvas(app.root)
     
    app.tools_canvas, app.tool_images = setup_tools_canvas(
        app.root, list(app.tool_items_bw.keys()), app.on_tool_click, app.image_cache)    
    app.root.update_idletasks()  # Force update
    
    app.scenario_canvas, app.scenario_images = setup_scenario_canvas(
        app.root, list(app.scenario_items_bw.keys()), app.item_to_location, app.on_scenario_click, app.image_cache)
    app.root.update_idletasks()  # Force update

    app.characters_canvas, app.character_images = setup_characters_canvas(app.root, app.characters, app.image_cache, app)
    
    app.maidens_canvas, app.maidens_images = setup_maidens_canvas(app.root, app.characters, app.characters_bw, app.image_cache, app.check_all_maidens_colored)

def setup_scanners(app):
    """
    Set up the scanners for inventory and scenarios.
    """
    if app.base_address is None:
        logging.error("Error: base_address is None during scanner setup.")
        return  # Early return if base_address is not valid
    
    app.scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
    app.sscanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
    app.cscanner = CharacterScanner(app, app.process, app.base_address, app.characters_canvas, app.character_images, app.image_cache)

def show_about_window():
    """Show the 'About' window."""
    about_window = tk.Toplevel()
    about_window.title("About")
    about_text = (
        "Thank you for using Lufia 2 Auto Tracker!\n"
        "This was my first project and took me quite some time.\n"
        "Feel free to report any bugs or suggestions to\n\n"
        "my git repository:\n"
        "https://github.com/RndmMeme/Lufia-2-Autotracker\n\n"
        "my discord:\n"
        "Rndmmeme#5100\n\n"
        "or the Lufia2 community on discord:\n"
        "Ancient Cave\n\n"
        "Many thanks to\n\n"
        "- abyssonym, the creator of the Lufia2 Randomizer \"terrorwave\"\n"
        "https://github.com/abyssonym/terrorwave\n\n"
        "who patiently explained a lot of the secrets to me :)\n\n"
        "- The3X for testing and feedback\n"
        "https://www.twitch.tv/the3rdx\n\n"
        "- the Lufia2 community\n\n"
        "- and of course you, who decided to use my tracker!\n\n"
        "RndmMeme\n"
        "Lufia 2 Auto Tracker v1 @2024"
    )
    label = tk.Label(about_window, text=about_text, padx=10, pady=10, justify=tk.LEFT)
    label.pack()
    
    close_button = tk.Button(about_window, text="Close", command=about_window.destroy)
    close_button.pack(pady=10)

def show_help_window():
    """Show the 'Help' window."""
    help_window = tk.Toplevel()
    help_window.title("Help")
    help_text = (
        "Welcome to Lufia 2 Auto Tracker!\n"
        "If you want to explore the application on your own, feel free to do so.\n"
        "Otherwise here a few tips:\n\n"
        "- \"Options\"\n"
        "   - \"Save\": Save your current session\n"
        "   - \"Load\": Load a saved session\n"
        "- Clicking the \"Autoscan\" will sync the tracker to the actual state"
        "- Manually toggling any item or character will pause synchronization, press \"Sync\" to resume auto update\n"
        "- Right click on cities (pink dots) to open the sub menu. Clicking any entry will save it to the corresponding canvas.\n"
        "- Right click on locations (other color) to open character menu. Clicking a character name will color the character \n"
        "  as \"obtained\" and display the location name where you found it\n"
        "- Right click a character you obtained will reset the character and remove the location\n"
        "- Left click any location dot will change the color\n"
        "Colors: red - not accessible\n"
        "        orange - partially accessible\n"
        "        green - fully accessible\n"
        "        grey - cleared\n"
    )
    label = tk.Label(help_window, text=help_text, padx=10, pady=10, justify=tk.LEFT)
    label.pack()

    close_button = tk.Button(help_window, text="Close", command=help_window.destroy)
    close_button.pack(pady=10)

def create_menu(app):
    """
    Create the application menu.
    """
    menubar = tk.Menu(app.root)
    app.root.config(menu=menubar)
    
    options_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Options", menu=options_menu)
    
    options_menu.add_command(label="Save", command=lambda: save_game_state(app))  # Added save option
    options_menu.add_command(label="Load", command=lambda: load_game_state(app))

    menubar.add_command(label="About", command=show_about_window)
    menubar.add_command(label="Help", command=show_help_window)

def right_click_handler(app, event, location):
    show_context_menu(app, event, location)

def show_context_menu(app, event, location):
    context_menu = tk.Menu(app.root, tearoff=0)
    
    # Set the font size for the context menu
    new_font = tkFont.Font(family="Helvetica", size=10)  # You can change the size and family as desired
    app.root.option_add("*Menu*Font", new_font)

    if location in CITIES:  # Check if the location is a city
        weapon_menu = tk.Menu(context_menu, tearoff=0, font=new_font)
        armor_menu = tk.Menu(context_menu, tearoff=0, font=new_font)
        spell_menu = tk.Menu(context_menu, tearoff=0, font=new_font)

        context_menu.add_cascade(label="Weapon", menu=weapon_menu)
        context_menu.add_cascade(label="Armor", menu=armor_menu)
        context_menu.add_cascade(label="Spell", menu=spell_menu)

        fill_shop_menu(app, location, "weapon", weapon_menu)
        fill_shop_menu(app, location, "armor", armor_menu)
        fill_shop_menu(app, location, "spell", spell_menu)

        
    else:
        # For other locations, provide the character menu
        context_menu.add_command(label="Assign Character", command=lambda: show_character_menu(app, location))
    
    context_menu.configure(font=new_font)
    context_menu.post(event.x_root, event.y_root)

def fill_shop_menu(app, location, category, menu):
    json_path = os.path.join(app.data_dir, 'shop_data.json')
    with open(json_path, 'r') as file:
        shop_items = json.load(file)
    
    if location in shop_items and category.lower() in shop_items[location]:
        items = shop_items[location][category.lower()]
        if items:
            for item in items:
                menu.add_command(label=item[0], command=lambda item=item: store_shop_item(app, location, item[0], item[1], category))
        else:
            menu.add_command(label=f"No items found for {category} in {location}")
    else:
        menu.add_command(label=f"No items found for {category} in {location}")

def store_shop_item(app, location, item_name, hex_value, category):
    canvas = app.item_canvas if category in ["weapon", "armor", "iris", "spell"] else None
    if canvas:
        # Determine the y-coordinate for the new entry
        bbox = canvas.bbox("all")
        y = bbox[3] + 20 if bbox else 30  # Start the first entry at y=30

        # Create the label and remove button directly on the canvas
        text_id = canvas.create_text(10, y, anchor='nw', text=f"{location}: {item_name}", fill="white", font=('Arial', 10))
        button_id = canvas.create_text(260, y, anchor='nw', text="x", fill="red", font=('Arial', 10, 'bold'))

        # Bind the remove button to remove the entry
        canvas.tag_bind(button_id, "<Button-1>", lambda event, tid=text_id, bid=button_id: remove_entry(canvas, tid, bid))

        # Update the scroll region to include the new entry
        canvas.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # Scroll to the new entry
        canvas.yview_moveto(1.0)

def remove_entry(canvas, text_id, button_id):
    canvas.delete(text_id)
    canvas.delete(button_id)
    canvas.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

def update_character_image(canvas, character_images, name, is_active):
    """
    Update the character image to colored if active, or dimmed (black-and-white) if inactive.
    """
    character_info = character_images.get(name)
    if character_info:
        new_image = character_info['color_image'] if is_active else character_info['bw_image']
        canvas.itemconfig(character_info['position'], image=new_image)
        character_info['current_image'] = new_image
        character_info['is_colored'] = is_active

        # Keep a reference to the image to prevent it from being garbage collected
        if not hasattr(canvas, 'images'):
            canvas.images = []
        canvas.images.append(new_image)

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
    app.manual_toggles[character_name] = True
    update_character_image(app.characters_canvas, app.character_images, character_name, True)

    # Split the location name into two lines if it has more than 10 characters
    if len(location) > 10:
        mid = len(location) // 2
        if ' ' in location:
            space_index = location.rfind(' ', 0, mid)
            if space_index != -1:
                part1 = location[:space_index]
                part2 = location[space_index + 1:]
            else:
                part1 = location[:mid]
                part2 = location[mid:]
        else:
            part1 = location[:mid]
            part2 = location[mid:]
        location_text = f"{part1}\n{part2}"
    else:
        location_text = location

    # Add the location label below the character image
    char_info = app.character_images[character_name]
    char_position = app.characters_canvas.coords(char_info['position'])

    # Always place text below the character image
    text_y_offset = 65

    # Determine the final y position for the text
    new_text_y = char_position[1] + text_y_offset

    text_id = app.characters_canvas.create_text(
        char_position[0] + 20,
        new_text_y,
        text=location_text,
        fill="white",
        anchor="n",
        tags=(f"location_text_{character_name}", "location_text")
    )

    # Bind right-click event to the character image for removing location
    app.characters_canvas.tag_bind(char_info['position'], "<Button-3>", lambda event: remove_character_location(app, character_name))

    # Force the canvas to redraw and ensure the text is on top
    app.characters_canvas.tag_raise(text_id)
    app.characters_canvas.update_idletasks()

def remove_character_location(app, character_name):
    text_tags = f"location_text_{character_name}"
    app.characters_canvas.delete(text_tags)
    app.manual_toggles[character_name] = False
    update_character_image(app.characters_canvas, app.character_images, character_name, False)
