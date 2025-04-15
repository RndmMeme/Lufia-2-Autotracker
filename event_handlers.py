# event_handlers.py

from shared import characters_bw, characters, load_image, tool_items_c, scenario_items_c, STATE_ORDER, LOCATION_STATES
from canvas_config import tool_items_bw, scenario_items_bw
import logging


def handle_tool_click(app, tool_name):
   
    try:
        if tool_name in app.obtained_items:
            
            del app.obtained_items[tool_name]
            obtained = False
        else:
        
            app.obtained_items[tool_name] = True
            obtained = True
        
        update_tool_image(app, tool_name, obtained=obtained)
        app.location_logic.update_accessible_locations(app.obtained_items)
        app.handle_manual_input()
    except Exception as e:
        logging.error(f"Error handling tool click for {tool_name}: {e}")

def handle_scenario_click(app, scenario_name):
    
    try:
        if scenario_name in app.obtained_items:
            del app.obtained_items[scenario_name]  # Remove from dictionary
            obtained = False
        else:
            app.obtained_items[scenario_name] = True
            obtained = True # explizit auf true setzen
        update_scenario_image(app, scenario_name, obtained=obtained)
        app.location_logic.update_accessible_locations(app.obtained_items)
        app.handle_manual_input()
    except Exception as e:
        logging.error(f"Error handling scenario click for {scenario_name}: {e}")

def handle_maiden_click(app, maiden_name):
    try:
        if maiden_name in app.obtained_items:
            del app.obtained_items[maiden_name] # Entfernen aus dem Dictionary
            obtained = False
        else:
            app.obtained_items[maiden_name] = True # Hinzufügen zum Dictionary
            obtained = True
            
        update_maiden_image(app, maiden_name, obtained=obtained)
        app.location_logic.update_accessible_locations(app.obtained_items)
        app.handle_manual_input()
    except Exception as e:
        logging.exception(f"Fehler in handle_maiden_click: {e}")
        
def handle_dot_click(app, location):
    """
    Handles clicks on location dots on the map.
    """
    try:
        current_state = app.location_states.get(location, "not_accessible")
        current_index = STATE_ORDER.index(current_state)
        next_state = STATE_ORDER[(current_index + 1) % len(STATE_ORDER)]
        app.location_states[location] = next_state

        dot, label = app.location_labels.get(location, (None, None))
        if dot:
            new_color = LOCATION_STATES[next_state]
            app.canvas.itemconfig(dot, fill=new_color)
            app.canvas.itemconfig(label, fill=new_color)
    except Exception as e:
        logging.error(f"Error handling dot click for location {location}: {e}")

def update_tool_image(app, tool_name, obtained=None):
    """Updates the image of a tool on the canvas.

    Args:
        app: The application instance.
        tool_name: The name of the tool.
        obtained (bool, optional): If True, use the colored image. 
            If False, use the black and white image. If None (default), toggle the image.
    """
    
    try:
        if tool_name in app.tool_images:
            tool_data = app.tool_images[tool_name]
            
            if obtained is None or False:  # Toggle if no explicit state is provided
                tool_data['is_colored'] = not tool_data['is_colored']
            else:
                tool_data['is_colored'] = obtained  # Wert aus dem Save übernehmen

            if tool_data['is_colored']:
                image_path = tool_items_c[tool_name]["image_path"]
            else:
                image_path = tool_items_bw[tool_name]["image_path"]

            new_image = app.load_image_cached(image_path, size=(40, 40))

            if new_image:
                app.tools_canvas.itemconfig(tool_data['position'], image=new_image)
                tool_data['image'] = new_image
                app.tools_canvas.images.append(new_image)
            else:
                logging.error(f"Failed to load image for {tool_name} at {image_path}")

        else:
            logging.error(f"Tool {tool_name} not found in tool_images.")
        
    except Exception as e:
        logging.error(f"Error updating tool image for {tool_name}: {e}")

def update_scenario_image(app, scenario_name, obtained=None):
    """
    Updates the image of a scenario item on the canvas.
    """
    try:
        if scenario_name in app.scenario_images:
            scenario_data = app.scenario_images[scenario_name]
            if obtained is None:
                scenario_data['is_colored'] = not scenario_data['is_colored']
            else:
                scenario_data['is_colored'] = obtained
                
            if scenario_data['is_colored']:
                image_path = scenario_items_c[scenario_name]["image_path"]
            else:
                image_path = scenario_items_bw[scenario_name]["image_path"]
                
            new_image = app.load_image_cached(image_path, size=(40, 40))
            
            if new_image:
                app.scenario_canvas.itemconfig(scenario_data['position'], image=new_image)
                scenario_data['image'] = new_image
                app.scenario_canvas.images.append(new_image)
            else:
                logging.error(f"Failed to load image for {scenario_name} at {image_path}")
        else:
            logging.error(f"Scenario {scenario_name} not found in scenario_images.")
    except Exception as e:
        logging.error(f"Error updating scenario image for {scenario_name}: {e}")
            
def update_maiden_image(app, maiden_name, obtained=None):
    """
    Updates the image of a Maidens on the canvas.
    """
    try:
        
        if maiden_name in app.maiden_images:
            maiden_data = app.maiden_images[maiden_name]
            if obtained is None:
                maiden_data['is_colored'] = not maiden_data['is_colored']
            else:
                maiden_data['is_colored'] = obtained
                
            if maiden_data['is_colored']:
                image_path = characters[maiden_name]["image_path"]
            else:
                image_path = characters_bw[maiden_name]["image_path"]
            
            new_image = app.load_image_cached(image_path, size=(40, 40))
            
            if new_image:
                app.maidens_canvas.itemconfig(maiden_data['position'], image=new_image)
                maiden_data['image'] = new_image
                app.maidens_canvas.images.append(new_image)
    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Maiden-Bildes für {maiden_name}: {e}")
