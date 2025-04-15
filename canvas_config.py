# canvas_config.py
import tkinter as tk
from PIL import Image, ImageTk
import os
from shared import tool_items_c, tool_items_bw, scenario_items_bw, CITIES, IMAGES_DIR, ALWAYS_ACCESSIBLE_LOCATIONS, COLORS, characters, characters_bw
from helpers.file_loader import load_image
from logic import LocationLogic
import logging
from helpers.item_management import add_sort_buttons


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

# Path to the map image
map_address = os.path.join(IMAGES_DIR, "map", "map.jpg")

def setup_item_canvas(root):
    
    items_label = tk.Label(root, anchor="w", bg='black', fg='white', font=("Arial", 13), text="Items/Spells:")
    items_label.place(x=3, y=25, width=298)  # Positioniere das Label
    
    item_canvas = tk.Canvas(root, bg='black', width=301, height=284)
    item_canvas.place(x=1, y=50, width=301, height=264)
    
    #Füge die Sortierbuttons hinzu
    add_sort_buttons(root, item_canvas)
    
    # Configure the canvas scroll region
    item_canvas.configure(scrollregion=item_canvas.bbox("all"))
    
    # Bind mouse wheel events to the canvas
    item_canvas.bind("<Enter>", lambda event: item_canvas.bind_all("<MouseWheel>", lambda event: on_mousewheel(event, item_canvas)))
    item_canvas.bind("<Leave>", lambda event: item_canvas.unbind_all("<MouseWheel>"))
    
    return item_canvas

def setup_tools_canvas(root, tools_keys, tool_click_callback, image_cache):
    tools_canvas = tk.Canvas(root, bg='black', width=290, height=60)
    tools_canvas.images = []
    tools_canvas.place(x=300, y=226, width=290, height=60)

    tool_images = {}
    for i, key in enumerate(tools_keys):
        image_path = tool_items_bw[key]["image_path"]
        image = load_image_cached(image_path, image_cache, size=(40, 40))
        if image:
            x = 5 + i *40
            y = 5
            image_id = tools_canvas.create_image(x, y, anchor="nw", image=image)
            tools_canvas.create_text(x + 18, y + 32, anchor="n", text=key, fill="white", font=("Arial", 8))
            tool_images[key] = {'image': image, 'position': image_id}
            tools_canvas.tag_bind(image_id, "<Button-1>", lambda event, tool=key: tool_click_callback(tool))
            tools_canvas.images.append(image)
                
    return tools_canvas, tool_images

def setup_maidens_canvas(root, characters, characters_bw, image_cache, app, maiden_click_callback):
    maidens_canvas = tk.Canvas(root, bg='black', width=120, height=57) 
    maidens_canvas.images = []
    maidens_canvas.place(x=580, y=226, width=120, height=57)

    maiden_images = {}
    
    maiden_names = ["Claire", "Lisa", "Marie"]
    start_x = 1
    row_y = 1

    def get_bw_image_path(original_path):
        base, ext = os.path.splitext(original_path)
        return base + "bw" + ext

    def add_maidens_to_canvas(characters_list, start_x, y):
        
        for i, name in enumerate(characters_list):
            try:

                original_image_path = characters.get(name, {}).get("image_path")
                bw_image_path = characters_bw.get(name, {}).get("image_path")

                image_path_to_load = bw_image_path if bw_image_path and os.path.exists(bw_image_path) else original_image_path
                
                image = load_image_cached(image_path_to_load, image_cache, size=(40, 40))

                if image:
                    x = start_x + i * 40
                    image_id = maidens_canvas.create_image(x, y, anchor="nw", image=image)
                    maidens_canvas.create_text(x + 20, y + 40, anchor="n", text=name, fill="white", font=("Arial", 9))
                    maiden_images[name] = {
                        'bw_image': load_image_cached(bw_image_path, image_cache, size=(40, 40)) if bw_image_path else None,
                        'color_image': load_image_cached(original_image_path, image_cache, size=(40, 40)),
                        'current_image': image,
                        'image_path': image_path_to_load,
                        'position': image_id,
                        'is_colored': False
                    }
                    maidens_canvas.tag_bind(image_id, "<Button-1>", lambda event, name=name, app=app: maiden_click_callback(name))
                    
                    maidens_canvas.images.append(image)

            except Exception as e:
                logging.error(f"Error processing maiden {name}: {type(e).__name__}: {e}")
    
    add_maidens_to_canvas(maiden_names, start_x, row_y)
    app.maiden_images = maiden_images

    return maidens_canvas, maiden_images

def setup_hints_canvas(root):
    hints_label = tk.Label(root, anchor="w", bg='black', fg='white', font=("Arial", 13), text="Hints:")
    hints_label.place(x=3, y=314, width=298)  # Positioniere das Label

    hints_text = tk.Text(root, bg='black', fg='white', width=298, height=466, wrap='word', insertbackground='white')  # Höhe angepasst
    hints_text.place(x=3, y=341, width=298, height=486)  # Positioniere das Text-Widget unter dem Label

    hints_text.configure(font=("Helvetica", 12))
    hints_text.focus()

    hints_text.bind_all("<MouseWheel>", lambda event: on_mousewheel(event, hints_text))

    return hints_text  # Gib das Text-Widget zurück

def setup_canvas(root, map_address, locations, location_logic, inventory, scenario_items, dot_click_callback, right_click_callback=None, manual_input_active=False):  
    try:
        canvas = tk.Canvas(root, bg='black', width=400, height=400)
        canvas.images = []
        canvas.place(x=300, y=429, width=400, height=400)

        map_image = Image.open(map_address)
        resized_map_image = map_image.resize((400,400), Image.Resampling.LANCZOS)
        map_photo = ImageTk.PhotoImage(resized_map_image)
        canvas.create_image(0, 0, anchor=tk.NW, image=map_photo, tags="map")
        canvas.map_photo = map_photo
        canvas.images.append(map_photo)

        scale_factor_x = 400 / 4096
        scale_factor_y = 400 / 4096
        
        # *** NEU: Skalierungsfaktoren im Canvas speichern ***
        canvas.scale_factor_x = scale_factor_x
        canvas.scale_factor_y = scale_factor_y

        location_labels = {}
        tooltips = {}
        
        city_limit = 28
        locations_list = list(locations.items())

        for index, (location, coords) in enumerate(locations_list):
            x_scaled = coords[0] * scale_factor_x 
            y_scaled = coords[1] * scale_factor_y
            color = determine_location_color(location, inventory, scenario_items, location_logic)
            
            if index < city_limit:
                # Draw circles for cities
                dot = canvas.create_oval(x_scaled - 5, y_scaled - 5, x_scaled + 5, y_scaled + 5, fill=color, tags=f"dot_{location}")
            else:
                # Draw rectangles for other locations
                dot = canvas.create_rectangle(x_scaled - 6, y_scaled - 6, x_scaled + 6, y_scaled + 6, fill=color, tags=f"dot_{location}")

            #label = canvas.create_text(x_scaled, y_scaled - 10, text=location, fill="white", anchor="s", tags=f"label_{location}")
            location_labels[location] = dot

            tooltip = ToolTip(canvas)
            tooltips[dot] = tooltip

            access_rules = location_logic.get(location, {}).get('access_rules', [])
            required_items = "\n".join([f"• {rule}" for rule in access_rules]) if access_rules else "No items required."
            tooltip_text = f"{location}\n\nRequired items:\n{required_items}"

            canvas.tag_bind(dot, "<Enter>", lambda event, text=tooltip_text: tooltips[event.widget.find_withtag("current")[0]].showtip(text, event.x_root, event.y_root))
            canvas.tag_bind(dot, "<Leave>", lambda event: tooltips[event.widget.find_withtag("current")[0]].hidetip())
            canvas.tag_bind(dot, "<Button-1>", lambda event, loc=location: dot_click_callback(loc))
            
            if right_click_callback:
                canvas.tag_bind(dot, "<Button-3>", lambda event, loc=location: right_click_callback(event, loc))

        return canvas, map_image, map_photo, location_labels
    except Exception as e:
        logging.error(f"Error in setup_canvas: {e}")
        raise

def setup_scenario_canvas(root, scenario_keys, item_to_location, scenario_click_callback, image_cache):
    scenario_canvas = tk.Canvas(root, bg='black', width=400, height=150)
    scenario_canvas.images = []
    scenario_canvas.place(x=300, y=281, width=400, height=150) 

    scenario_images = {}
    tooltips = {}

    # Constants for grid layout
    columns = 6  # Number per row
    spacing_x = 65  # Horizontal spacing between items
    spacing_y = 45  # Vertical spacing between items
    start_x = 30  # Starting X position
    start_y = 2  # Starting Y position

    # Calculate total number of rows needed
    total_rows = (len(scenario_keys) + columns - 1) // columns

    for i, key in enumerate(scenario_keys):
        item_info = scenario_items_bw[key]
        image_path = item_info["image_path"]
        
        image = load_image_cached(image_path, image_cache, size=(40, 40))

        if image:
            col = i % columns  # Column position
            row = i // columns  # Row position
            
            # Center the last row if it is not a full row (angepasst für Reihen)
            if row == total_rows - 1 and len(scenario_keys) % columns != 0:
                start_x_adjusted = start_x + ((columns - len(scenario_keys) % columns) * spacing_x) / 2
                x = start_x_adjusted + col * spacing_x
            else:
                x = start_x + col * spacing_x
            
            y = start_y + row * spacing_y
            image_id = scenario_canvas.create_image(x, y, anchor="nw", image=image)
                
            text_y = y + 45  # Place the text below the image
            scenario_canvas.create_text(x + 15, text_y, anchor='center', text=key, fill="white", font=("Arial", 10))
            scenario_images[key] = {'image': image, 'position': image_id}
            
            # Debug message added here
            scenario_canvas.tag_bind(image_id, "<Button-1>", lambda event, scenario=key: scenario_click_callback(scenario))

            locations = item_to_location.get(key, [])
            location_text = ", ".join(locations) if locations else "No specific location"

            tooltip = ToolTip(scenario_canvas)
            tooltips[image_id] = tooltip

            # Ensure the correct tooltip text is displayed
            scenario_canvas.tag_bind(image_id, "<Enter>", lambda event, location_text=location_text, item_id=image_id: tooltips[item_id].showtip(location_text, event.x_root, event.y_root))
            scenario_canvas.tag_bind(image_id, "<Leave>", lambda event, item_id=image_id: tooltips[item_id].hidetip())

            scenario_canvas.images.append(image)
        

    return scenario_canvas, scenario_images

def setup_characters_canvas(root, characters, image_cache, app):
    characters_canvas = tk.Canvas(root, bg='black', width=400, height=205)
    characters_canvas.images = []
    characters_canvas.place(x=300, y=23, width=400, height=205)
    

    character_images = {}
    start_x = 3
    y = 5

    first_row_characters = list(characters.keys())[:7]
    second_row_characters = list(characters.keys())[-7:]

    def get_bw_image_path(original_path):
        base, ext = os.path.splitext(original_path)
        return base + "bw" + ext
 
    def add_characters_to_canvas(characters_list, start_x, y):
        for i, name in enumerate(characters_list):
            original_image_path = characters[name]["image_path"]
            bw_image_path = get_bw_image_path(original_image_path)
            image_path_to_load = bw_image_path if os.path.exists(bw_image_path) else original_image_path
            image = load_image_cached(image_path_to_load, image_cache, size=(40, 40))

            if image:
                x = start_x + i * 56
                image_id = characters_canvas.create_image(x, y, anchor="nw", image=image)
                characters_canvas.create_text(x + 20, y + 40, anchor="n", text=name, fill="white", font=("Arial", 10))
                character_images[name] = {
                    'bw_image': load_image_cached(bw_image_path, image_cache, size=(40, 40)),
                    'color_image': load_image_cached(original_image_path, image_cache, size=(40, 40)),
                    'current_image': image,
                    'image_path': image_path_to_load,
                    'position': image_id,
                    'is_colored': False
                }
                characters_canvas.tag_bind(image_id, "<Button-1>", lambda event, n=name: toggle_character_image(characters_canvas, character_images, n, app))
                characters_canvas.images.append(image)

    add_characters_to_canvas(first_row_characters, start_x, y)
    add_characters_to_canvas(second_row_characters, start_x, y + 100)

    app.character_images = character_images
    return characters_canvas, character_images


def load_image(path):
    try:
        image = Image.open(path)
        image = image.resize((30, 30), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception as e:
        logging.error(f"Error loading image at {path}: {e}")
        return None
    
def load_image_cached(path, image_cache, size=None):
    cache_key = (str(path), size)
    if cache_key in image_cache:
        return image_cache[cache_key]

    try:
        image = Image.open(path)
        image = image.resize(size, Image.Resampling.LANCZOS)
        photo_image = ImageTk.PhotoImage(image)
        image_cache[cache_key] = photo_image
        return photo_image
    except Exception as e:
        logging.error(f"Error loading image at {path}: {e}")
        return None


        
def on_mousewheel(event, canvas):
    # Determine the direction of the scroll
    direction = 1 if event.delta < 0 else -1
    canvas.yview_scroll(direction, "units")

def update_character_image(canvas, app, name, new_image_path):
    # used in gui_setup for updating the character image on characters_canvas
    character_info = app.character_images.get(name)
    if character_info:
        new_image = load_image_cached(new_image_path, app.image_cache, size=(40,40))
        canvas.itemconfig(character_info['position'], image=new_image)
        character_info['current_image'] = new_image
        if not hasattr(canvas, 'images'):
            canvas.images = []
        if new_image not in canvas.images:
            canvas.images.append(new_image)
      
def determine_location_color(location, inventory, scenario_items, location_logic):
    if location in ALWAYS_ACCESSIBLE_LOCATIONS:
        return COLORS['accessible']
    elif location in CITIES: # Hier findet die Änderung statt!
        access_status = check_access(location, inventory, scenario_items, location_logic)
        # Überprüfe, ob die Stadt Anforderungen hat und ob diese NICHT erfüllt sind
        if location_logic.get(location, {}).get('access_rules') and access_status != 'accessible':
            return COLORS['not_accessible'] # Rot, wenn Anforderungen nicht erfüllt
        else:
            return COLORS['city'] # Gelb, wenn keine Anforderungen oder Anforderungen erfüllt
    else:
        access_status = check_access(location, inventory, scenario_items, location_logic)
        return COLORS[access_status]

def add_location(canvas, location, coords, location_labels, color):
    try:
        x, y = coords
        x_scaled = x * canvas.scale_factor
        y_scaled = y * canvas.scale_factor
        dot = canvas.create_oval(x_scaled - 5, y_scaled - 5, x_scaled + 5, y_scaled + 5, fill=color, outline="white", tags=f"dot_{location}")
        label = canvas.create_text(x_scaled, y_scaled + 10, text=location, fill="white", tags=f"label_{location}")
        location_labels[location] = (dot, label)
    except Exception as e:
        logging.error(f"Error adding location {location} at ({coords[0]}, {coords[1]}): {e}")

def check_access(location, inventory, scenario_items, location_logic):
    rules = location_logic.get(location, {}).get('access_rules', [])
    if not rules:
        return 'accessible'
    for rule in rules:
        items = rule.split(',')
        if all(item in inventory or item in scenario_items for item in items):
            return 'accessible'
    return 'partially_accessible' if any(item in inventory or item in scenario_items for rule in rules for item in rule.split(',')) else 'not_accessible'
    
def toggle_character_image(characters_canvas, character_images, name, app):
    character_info = character_images.get(name)
    if character_info:
        new_image = character_info['bw_image'] if character_info['is_colored'] else character_info['color_image']
        characters_canvas.itemconfig(character_info['position'], image=new_image)
        character_info['current_image'] = new_image
        character_info['is_colored'] = not character_info['is_colored']
        app.manual_toggles[name] = character_info['is_colored']
        if not hasattr(characters_canvas, 'images'):
            characters_canvas.images = []
        characters_canvas.images.append(new_image)
    

class ToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None
        self.text = None

    def showtip(self, text, x, y):
        self.text = text
        if self.tip_window or not self.text:
            return
        x = x + 10
        y = y + 10
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy() 
            