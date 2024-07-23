# button_functions.py

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from shared import tool_items_bw, tool_items_c, scenario_items_bw, scenario_items_c, ALWAYS_ACCESSIBLE_LOCATIONS, STATE_ORDER, LOCATION_STATES, LOCATION_LOGIC
from helpers.file_loader import load_image
from canvas_config import CITIES, update_character_image
from inventory_scan import CHARACTER_SLOT_ADDRESSES, CHARACTER_BYTE_MAPPING
from game_tracking import read_memory_with_retry
import json
import os
import datetime
import logging
from shop_calc import process_shop_data, process_and_save_shop_data
import gui_setup

# Ensure the directory exists
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logging
logging.basicConfig(
    filename=os.path.join(log_dir, 'app.log'),
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

def sync_game_state(app):
    """
    Synchronizes the current game state with the UI, updating all tracked items and resuming automatic tracking.
    """
    try:
        
        # Delete the old shop_data.json
        shop_data_path = os.path.join(app.data_dir, 'shop_data.json')
        try:
            if os.path.exists(shop_data_path):
                print(f"Deleting existing shop_data.json at {shop_data_path}")
                os.remove(shop_data_path)
            else:
                print(f"No existing shop_data.json found at {shop_data_path}")
        except Exception as e:
            logging.error(f"Error deleting shop_data.json: {e}")
            print(f"Error deleting shop_data.json: {e}")

        # Re-run shop calculations to read the current shop table
        print("Re-running shop calculations...")
        process_shop_data(app)

        # Save the re-read shop data
        print("Saving new shop_data.json...")
        process_and_save_shop_data(app, shop_data_path)
        
        """
        Resets the game state, clearing all tracked items and resetting UI elements.
        """
        app.obtained_items.clear()

        # Clear tool images on the canvas
        for tool_name, tool_info in app.tool_images.items():
            bw_image_path = tool_items_bw[tool_name]["image_path"]
            new_image = app.load_image_cached(bw_image_path)
            if new_image:
                app.tools_canvas.itemconfig(tool_info['position'], image=new_image)
                tool_info['image'] = new_image
    
        # Clear scenario images on the canvas
        for scenario_name, scenario_info in app.scenario_images.items():
            bw_image_path = scenario_items_bw[scenario_name]["image_path"]
            new_image = app.load_image_cached(bw_image_path)
            if new_image:
                app.scenario_canvas.itemconfig(scenario_info['position'], image=new_image)
                scenario_info['image'] = new_image

        # Update map locations based on the current state
        for location, dot in app.location_labels.items():
            current_color = app.canvas.itemcget(dot, "fill")
            if current_color == "grey":
                continue  # Skip locations that are already marked as cleared

            dot_color = "red"
            if location in ALWAYS_ACCESSIBLE_LOCATIONS:
                dot_color = "lightgreen"
            elif location in CITIES:
                dot_color = "pink"
            elif location in app.obtained_items:
                dot_color = "lightgreen"
            elif any(item in app.obtained_items for item in LOCATION_LOGIC.get(location, {}).get("access_rules", [])):
                dot_color = "orange"

            app.canvas.itemconfig(dot, fill=dot_color)

    except Exception as e:
        logging.error(f"Error during game sync: {e}")
    finally:
        # Resume automatic updates after manual sync
        app.resume_automatic_updates()


def update_obtained_items(app, item_name, canvas, item_dict, color_images_dict):
    """
    Updates the state of an obtained item and its display on the canvas.
    """
    if item_name in app.obtained_items:
        app.obtained_items.remove(item_name)
        image_path = item_dict[item_name]["image_path"]
    else:
        app.obtained_items.add(item_name)
        image_path = color_images_dict[item_name]["image_path"]

    new_image = app.load_image_cached(image_path)
    if new_image:
        item_info = app.tool_images[item_name] if item_name in app.tool_images else app.scenario_images[item_name]
        canvas.itemconfig(item_info['position'], image=new_image)
        item_info['image'] = new_image

    # Update the map after changing an item's state
    app.update_map_based_on_tools()

def handle_tool_click(app, tool_name):
    app.manual_input_active = True  # Disable automatic updates during manual input
    
    if tool_name in app.obtained_items:
        app.obtained_items.remove(tool_name)
        new_image_path = tool_items_bw[tool_name]["image_path"]
    else:
        app.obtained_items.add(tool_name)
        new_image_path = tool_items_c[tool_name]["image_path"]

    update_tool_image(app, tool_name, new_image_path)
    app.update_map_based_on_tools()

def handle_scenario_click(app, scenario_name):
    app.manual_input_active = True  # Disable automatic updates during manual input

    if scenario_name in app.obtained_items:
        app.obtained_items.remove(scenario_name)
        new_image_path = scenario_items_bw[scenario_name]["image_path"]
    else:
        app.obtained_items.add(scenario_name)
        new_image_path = scenario_items_c[scenario_name]["image_path"]

    update_scenario_image(app, scenario_name, new_image_path)
    app.update_map_based_on_tools()

def handle_dot_click(app, location):
    app.manual_input_active = True  # Disable automatic updates during manual input

    current_state = app.location_states.get(location, "not_accessible")
    current_index = STATE_ORDER.index(current_state)
    next_state = STATE_ORDER[(current_index + 1) % len(STATE_ORDER)]
    app.location_states[location] = next_state

    dot, label = app.location_labels.get(location, (None, None))
    if dot:
        new_color = LOCATION_STATES[next_state]
        app.canvas.itemconfig(dot, fill=new_color)
        app.canvas.itemconfig(label, fill=new_color)

def update_tool_image(app, tool_name, image_path):
    new_image = app.load_image_cached(image_path)
    if new_image:
        tool_image_info = app.tool_images[tool_name]
        position = tool_image_info['position']
        app.tools_canvas.itemconfig(position, image=new_image)
        app.tool_images[tool_name]['image'] = new_image
        if not hasattr(app.tools_canvas, 'images'):
            app.tools_canvas.images = []
        app.tools_canvas.images.append(new_image)

def update_scenario_image(app, scenario_name, image_path):
    new_image = app.load_image_cached(image_path)
    if new_image:
        scenario_image_info = app.scenario_images[scenario_name]
        position = scenario_image_info['position']
        app.scenario_canvas.itemconfig(position, image=new_image)
        app.scenario_images[scenario_name]['image'] = new_image
        if not hasattr(app.scenario_canvas, 'images'):
            app.scenario_canvas.images = []
        app.scenario_canvas.images.append(new_image)

def save_game_state(app):
    """
    Saves the state of the application.
    """
    game_state = {
        "tools_canvas": get_canvas_content(app.tools_canvas),
        "scenario_canvas": get_canvas_content(app.scenario_canvas),
        "item_canvas": get_canvas_content(app.item_canvas),
        "hints_content": app.hints_canvas.get("1.0", tk.END),  # Save the text content
        "characters_canvas": get_canvas_content(app.characters_canvas),
        "maidens_canvas": get_canvas_content(app.maidens_canvas),
        "map_state": get_map_state(app)  # Save the map state
    }

    with open("game_state.json", "w") as f:
        json.dump(game_state, f)

def load_game_state(app):
    """
    Loads the state of the application.
    """
    try:
        with open("game_state.json", "r") as f:
            game_state = json.load(f)

        restore_canvas_content(app.tools_canvas, game_state["tools_canvas"])
        restore_canvas_content(app.scenario_canvas, game_state["scenario_canvas"])
        restore_canvas_content(app.item_canvas, game_state["item_canvas"])
        app.hints_canvas.delete("1.0", tk.END)
        app.hints_canvas.insert("1.0", game_state["hints_content"])
        restore_canvas_content(app.characters_canvas, game_state["characters_canvas"])
        restore_canvas_content(app.maidens_canvas, game_state["maidens_canvas"])
        restore_map_state(app, game_state["map_state"])  # Restore the map state

    except Exception as e:
        logging.error(f"Error loading game state: {e}")

def get_canvas_content(canvas):
    """
    Extracts the content from a canvas.
    """
    items = []
    for item_id in canvas.find_all():
        item_type = canvas.type(item_id)
        item_coords = canvas.coords(item_id)
        item_options = {k: v for k, v in canvas.itemconfig(item_id).items() if k != 'image'}  # Exclude the image itself
        items.append({"type": item_type, "coords": item_coords, "options": item_options})
    return items

def clear_canvas(canvas):
    """
    Clears all items from a canvas.
    """
    canvas.delete("all")

def restore_canvas_content(canvas, items):
    """
    Restores the content of a canvas.
    """
    for item in items:
        item_type = item["type"]
        item_coords = item["coords"]
        item_options = item["options"]

        if item_type == "text":
            canvas.create_text(*item_coords, **item_options)
        elif item_type == "rectangle":
            canvas.create_rectangle(*item_coords, **item_options)
        elif item_type == "oval":
            canvas.create_oval(*item_coords, **item_options)
        elif item_type == "image":
            # Restore image handling here
            pass
        # Add handling for other item types as needed

def get_map_state(app):
    """
    Extracts the state of the map (locations and their colors).
    """
    map_state = {}
    for location, dot in app.location_labels.items():
        color = app.canvas.itemcget(dot, "fill")
        map_state[location] = color
    return map_state

def restore_map_state(app, map_state):
    """
    Restores the state of the map (locations and their colors).
    """
    for location, color in map_state.items():
        if location in app.location_labels:
            dot = app.location_labels[location]
            app.canvas.itemconfig(dot, fill=color)

# Ensure these functions are accessible
__all__ = ["save_game_state", "load_game_state", "clear_game_state", "sync_game_state", "handle_tool_click", "handle_scenario_click", "handle_dot_click"]
