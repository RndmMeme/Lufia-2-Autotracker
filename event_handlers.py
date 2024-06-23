# event_handlers.py

from shared import load_image, tool_items_c, scenario_items_c, STATE_ORDER, LOCATION_STATES
from canvas_config import tool_items_bw, scenario_items_bw
import time

def handle_tool_click(app, tool_name):
    print(f"Tool clicked: {tool_name}")

    if tool_name in app.obtained_items:
        app.obtained_items.remove(tool_name)
        new_image_path = tool_items_bw[tool_name]["image_path"]
    else:
        app.obtained_items.add(tool_name)
        new_image_path = tool_items_c[tool_name]["image_path"]

    update_tool_image(app, tool_name, new_image_path)
    app.update_map_based_on_tools()

    app.handle_manual_input()  # Flag that a manual input has occurred

def handle_scenario_click(app, scenario_name):
    print(f"Scenario item clicked: {scenario_name}")

    if scenario_name in app.obtained_items:
        app.obtained_items.remove(scenario_name)
        new_image_path = scenario_items_bw[scenario_name]["image_path"]
    else:
        app.obtained_items.add(scenario_name)
        new_image_path = scenario_items_c[scenario_name]["image_path"]

    update_scenario_image(app, scenario_name, new_image_path)
    app.update_map_based_on_tools()

    app.handle_manual_input()  # Flag that a manual input has occurred


def handle_dot_click(app, location):
    """
    Handles clicks on location dots on the map.
    """
    print(f"Location dot clicked: {location}")

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
    """
    Updates the image of a tool on the canvas.
    """
    new_image = app.load_image_cached(image_path)
    if new_image:
        tool_image_info = app.tool_images[tool_name]
        position = tool_image_info['position']
        app.tools_canvas.itemconfig(position, image=new_image)
        tool_image_info['image'] = new_image
        # Append to the images list to prevent garbage collection
        app.tools_canvas.images.append(new_image)

def update_scenario_image(app, scenario_name, image_path):
    """
    Updates the image of a scenario item on the canvas.
    """
    new_image = app.load_image_cached(image_path)
    if new_image:
        scenario_image_info = app.scenario_images[scenario_name]
        position = scenario_image_info['position']
        app.scenario_canvas.itemconfig(position, image=new_image)
        scenario_image_info['image'] = new_image
        # Append to the images list to prevent garbage collection
        app.scenario_canvas.images.append(new_image)
