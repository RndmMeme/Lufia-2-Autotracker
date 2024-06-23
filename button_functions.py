# button_functions.py
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from shared import tool_items_bw, tool_items_c, scenario_items_bw, scenario_items_c, ALWAYS_ACCESSIBLE_LOCATIONS, STATE_ORDER, LOCATION_STATES
from helpers.file_loader import load_image
from canvas_config import CITIES, update_character_image
from inventory_scan import CHARACTER_SLOT_ADDRESSES, CHARACTER_BYTE_MAPPING
from game_tracking import read_memory_with_retry
from tkinter import filedialog
import json
import os
import datetime

# button_functions.py

def clear_game_state(app):
    """
    Resets the game state, clearing all tracked items and resetting UI elements.
    """
    print("Clearing game state...")
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

    # Reset map locations to default inaccessible state
    for location, (dot, label) in app.location_labels.items():
        dot_color = "red"
        if location in ALWAYS_ACCESSIBLE_LOCATIONS:
            dot_color = "lightgreen"
        elif location in CITIES:
            dot_color = "blue"
        app.canvas.itemconfig(dot, fill=dot_color)
        app.canvas.itemconfig(label, fill="white")

    # Pause automatic updates after clearing the game state
    app.auto_update_active = False
    print("Game state cleared and auto updates paused.")

def sync_game_state(app):
    """
    Synchronizes the current game state with the UI, updating all tracked items and resuming automatic tracking.
    """
    try:
        print("Synchronizing game state...")

        # Ensure the process is attached and the game is loaded
        if app.process and app.base_address:
            # Perform a manual inventory scan
            app.scanner.scan_inventory(app.process, app.base_address, app.obtained_items)
            app.sscanner.scan_scenario(app.process, app.base_address, app.obtained_items)

        # Update tool images based on the current obtained items
        for tool_name, tool_info in app.tool_images.items():
            if tool_name in app.obtained_items:
                color_image_path = tool_items_c[tool_name]["image_path"]
            else:
                color_image_path = tool_items_bw[tool_name]["image_path"]
            new_image = app.load_image_cached(color_image_path)
            if new_image:
                app.tools_canvas.itemconfig(tool_info['position'], image=new_image)
                tool_info['image'] = new_image

        # Update scenario images based on the current obtained items
        for scenario_name, scenario_info in app.scenario_images.items():
            if scenario_name in app.obtained_items:
                color_image_path = scenario_items_c[scenario_name]["image_path"]
            else:
                color_image_path = scenario_items_bw[scenario_name]["image_path"]
            new_image = app.load_image_cached(color_image_path)
            if new_image:
                app.scenario_canvas.itemconfig(scenario_info['position'], image=new_image)
                scenario_info['image'] = new_image


        # Optionally, update the map based on the obtained tools
        app.update_map_based_on_tools()

        print("Game state synchronized.")
    except Exception as e:
        print(f"Error during game sync: {e}")
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
        print(f"Item removed: {item_name}")
    else:
        app.obtained_items.add(item_name)
        image_path = color_images_dict[item_name]["image_path"]
        print(f"Item added: {item_name}")

    new_image = app.load_image_cached(image_path)
    if new_image:
        item_info = app.tool_images[item_name] if item_name in app.tool_images else app.scenario_images[item_name]
        canvas.itemconfig(item_info['position'], image=new_image)
        item_info['image'] = new_image

    # Update the map after changing an item's state
    app.update_map_based_on_tools()
    print(f"Updated state for {item_name}.")

def handle_tool_click(app, tool_name):
    print(f"Tool clicked: {tool_name}")
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
    print(f"Scenario item clicked: {scenario_name}")
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
    print(f"Location dot clicked: {location}")
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

    print(f"Location {location} updated to {next_state} (color: {new_color}).")

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
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                      initialfile=f"Lufia2Tracker_Save_{now}.json",
                                                      filetypes=[("JSON files", "*.json")])
        if not save_file_path:
            return  # User cancelled the save dialog

        save_data = {
            "obtained_items": list(app.obtained_items),
            "manual_toggles": app.manual_toggles,
            "tabbed_interface_content": get_tabbed_interface_content(app),
            "hints": app.tabbed_interface.nametowidget(app.tabbed_interface.tabs()[-1]).hints_text.get("1.0", tk.END)  # Save the hints text
        }

        with open(save_file_path, 'w') as save_file:
            json.dump(save_data, save_file, indent=2)

        print(f"Game state saved to {save_file_path}")
    except Exception as e:
        print(f"Error saving game state: {e}")


def load_game_state(app):
    try:
        load_file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not load_file_path:
            return  # User cancelled the load dialog

        with open(load_file_path, 'r') as load_file:
            load_data = json.load(load_file)

        # Restore the obtained items and manual toggles
        app.obtained_items = set(load_data.get("obtained_items", []))
        app.manual_toggles = load_data.get("manual_toggles", {})

        # Restore the tabbed interface content
        set_tabbed_interface_content(app, load_data.get("tabbed_interface_content", {}))

        # Restore the hints text
        hints_text_widget = app.tabbed_interface.nametowidget(app.tabbed_interface.tabs()[-1]).hints_text
        hints_text_widget.delete("1.0", tk.END)
        hints_text_widget.insert(tk.END, load_data.get("hints", ""))

        # Sync the game state to update UI based on the loaded data
        sync_game_state(app)

        print(f"Game state loaded from {load_file_path}.")
    except Exception as e:
        print(f"Error loading game state: {e}")



def get_tabbed_interface_content(app):
    """
    Collects the content of the tabbed interface for saving.
    """
    tab_content = {}

    # Access the notebook from the left_frame
    notebook = app.tabbed_interface.winfo_children()[0]  # The notebook should be the first child of the frame

    if isinstance(notebook, ttk.Notebook):
        for tab_id in notebook.tabs():
            tab_title = notebook.tab(tab_id, "text")
            tab_frame = notebook.nametowidget(tab_id)
            tab_data = get_tab_data(tab_frame)
            tab_content[tab_title] = tab_data
    else:
        print(f"Unexpected type for tabbed interface content: {type(notebook)}")

    return tab_content

def get_tab_data(tab_frame):
    """
    Extracts the content from a given tab frame.
    """
    content = []
    for widget in tab_frame.winfo_children():
        if isinstance(widget, tk.Canvas):
            canvas_content = get_canvas_content(widget)
            content.append({"type": "canvas", "content": canvas_content})
        # Add more types of widgets if needed
    return content

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



def set_tabbed_interface_content(app, content):
    """
    Restores the content of the tabbed interface from the saved state.
    """
    notebook = app.tabbed_interface.nametowidget(app.tabbed_interface.winfo_children()[0])
    print("Restoring tabbed interface content...")
    for tab_title, items in content.items():
        try:
            tab_id = notebook.index(tab_title)
            tab_frame = notebook.nametowidget(notebook.tabs()[tab_id])
            scrollable_frame = tab_frame.winfo_children()[0].winfo_children()[0]  # Access the inner scrollable frame
            clear_frame(scrollable_frame)

            for i, item in enumerate(items):
                tk.Label(scrollable_frame, text=item, background="black", foreground="white").grid(row=i, column=0, padx=5, pady=5)
        except Exception as e:
            print(f"Error restoring tab '{tab_title}': {e}")

def clear_frame(frame):
    """
    Clears all widgets from a frame.
    """
    for widget in frame.winfo_children():
        widget.destroy()

def restore_tab_data(tab_frame, content):
    """
    Restores the content of a given tab frame.
    """
    for widget_data in content:
        if widget_data["type"] == "canvas":
            restore_canvas_content(tab_frame, widget_data["content"])
        # Add more types of widgets if needed

def restore_canvas_content(canvas, items):
    """
    Restores the content of a canvas.
    """
    for item in items:
        item_type = item["type"]
        item_coords = item["coords"]
        item_options = item["options"]

        if item_type == "text":
            canvas.create_text(item_coords, **item_options)
        elif item_type == "rectangle":
            canvas.create_rectangle(item_coords, **item_options)
        # Add handling for other item types as needed

# Ensure these functions are accessible
__all__ = ["save_game_state", "load_game_state", "clear_game_state", "sync_game_state", "handle_tool_click", "handle_scenario_click", "handle_dot_click"]
