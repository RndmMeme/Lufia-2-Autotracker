import tkinter as tk
import tkinter.ttk as ttk
from PIL import Image, ImageTk
import os
from shared import tool_items_bw, scenario_items_bw, CITIES, IMAGES_DIR, ALWAYS_ACCESSIBLE_LOCATIONS, COLORS, characters, characters_bw, WIDGET_STORE
from helpers.file_loader import load_image
from logic import LocationLogic
import logging


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
    item_canvas = tk.Canvas(root, bg='black', width=297, height=93)
    item_canvas.place(x=5, y=285, width=297, height=93)
    item_canvas.create_text(10, 10, anchor="w", text="Items / Spells:", fill="white", font=("Arial", 10))
    
    # Configure the canvas scroll region
    item_canvas.configure(scrollregion=item_canvas.bbox("all"))
    
    # Bind mouse wheel events to the canvas
    item_canvas.bind("<Enter>", lambda event: item_canvas.bind_all("<MouseWheel>", lambda event: on_mousewheel(event, item_canvas)))
    item_canvas.bind("<Leave>", lambda event: item_canvas.unbind_all("<MouseWheel>"))
    
    return item_canvas

def setup_tools_canvas(root, tools_keys, tool_click_callback, image_cache):
    tools_canvas = tk.Canvas(root, bg='black', width=300, height=70)
    tools_canvas.images = []
    tools_canvas.place(x=5, y=220, width=300, height=70)

    tool_images = {}
    for i, key in enumerate(tools_keys):
        image_path = tool_items_bw[key]["image_path"]
        image = load_image_cached(image_path, image_cache)
        if image:
            x = 20 + i * 60
            y = 15
            image_id = tools_canvas.create_image(x, y, anchor="nw", image=image)
            tools_canvas.create_text(x + 13, y + 32, anchor="n", text=key, fill="white", font=("Arial", 8))
            tool_images[key] = {'image': image, 'position': image_id}
            tools_canvas.tag_bind(image_id, "<Button-1>", lambda event, tool=key: tool_click_callback(tool))
            tools_canvas.images.append(image)
                
    return tools_canvas, tool_images

def setup_maidens_canvas(root, characters, characters_bw, image_cache, check_all_colored):
    maidens_canvas = tk.Canvas(root, bg='black', width=191, height=67) 
    maidens_canvas.images = []
    maidens_canvas.place(x=300, y=223, width=191, height=67)

    maiden_images = {}
    maiden_names = ["Claire", "Lisa", "Marie"]
    row_y = 3

    for i, name in enumerate(maiden_names):
        
        bw_image_path = characters_bw.get(name, {}).get("image_path")
        if bw_image_path:
            bw_image_path = os.path.join(IMAGES_DIR, bw_image_path)
            bw_image = load_image_cached(bw_image_path, image_cache)
        else:
            logging.error(f"BW image path not found for {name}. Skipping...")
            continue

        color_image_path = characters.get(name, {}).get("image_path")
        if color_image_path:
            color_image_path = os.path.join(IMAGES_DIR, color_image_path)
            color_image = load_image_cached(color_image_path, image_cache)
        else:
            logging.error(f"Color image path not found for {name}.")
            color_image = bw_image

        if bw_image:
            x = 10 + i * 60
            y = row_y
            image_id = maidens_canvas.create_image(x, y, anchor="nw", image=bw_image)
            maidens_canvas.create_text(x + 20, y + 40, anchor="n", text=name, fill="white", font=("Arial", 8))
            maiden_images[name] = {
                'default_image': bw_image,
                'color_image': color_image,
                'current_image': bw_image,
                'image_path': bw_image_path,
                'color_image_path': color_image_path,
                'position': image_id,
                'is_colored': False
            }
            maidens_canvas.tag_bind(image_id, "<Button-1>", lambda event, n=name: toggle_maiden_image(maidens_canvas, maiden_images, n, check_all_colored))
            maidens_canvas.images.append(bw_image)

    return maidens_canvas, maiden_images

def setup_hints_canvas(root):
    # Create the Text widget
    hints_canvas = tk.Text(root, bg='black', fg='white', width=293, height=426, wrap='word', insertbackground='white')
    hints_canvas.place(x=7, y=378, width=293, height=426)
    
    # Configure the Text widget to have a specific font
    hints_canvas.configure(font=("Helvetica", 10))

    # Add static text as a label at the beginning
    hints_canvas.insert(tk.END, "Hints:\n")
    
    # Make the "Hints:" text non-editable
    hints_canvas.tag_add("static", "1.0", "1.end")
    hints_canvas.tag_configure("static", foreground="white", background="black")
    hints_canvas.configure(state='normal')  # Set the Text widget to editable state
    
    # Ensure that the "Hints:" text remains non-editable
    hints_canvas.bind("<Key>", lambda e: 'break' if hints_canvas.index(tk.INSERT).startswith("1.") else None)

    # Set focus to the Text widget to display the cursor
    hints_canvas.focus()
    
    #Bind mouse wheel events to the canvas
    hints_canvas.bind_all("<MouseWheel>", lambda event: on_mousewheel(event, hints_canvas))
    
    return hints_canvas

def setup_canvas(root, map_address, locations, location_logic, inventory, scenario_items, dot_click_callback, right_click_callback=None, manual_input_active=False):  
    try:
        canvas = tk.Canvas(root, bg='black', width=300, height=70)
        canvas.images = []
        canvas.place(x=300, y=285, width=570, height=520)

        map_image = Image.open(map_address)
        resized_map_image = map_image.resize((570, 520), Image.Resampling.LANCZOS)
        map_photo = ImageTk.PhotoImage(resized_map_image)
        canvas.create_image(0, 0, anchor=tk.NW, image=map_photo)
        canvas.map_photo = map_photo
        canvas.images.append(map_photo)

        scale_factor_x = 570 / map_image.width
        scale_factor_y = 520 / map_image.height
        
         # Create autoscan status label
        autoscan_label = ttk.Label(root, text="Autoscan: On", foreground="green", background="black")
        autoscan_label.place(x=790, y=290)  # Adjust position as needed

        location_labels = {}
        tooltips = {}
        
        city_limit = 29
        locations_list = list(locations.items())

        for index, (location, coords) in enumerate(locations_list):
            x_scaled = coords[0] * scale_factor_x 
            y_scaled = coords[1] * scale_factor_y
            color = determine_location_color(location, inventory, scenario_items, location_logic)
            
            if index < city_limit:
                # Draw circles for cities
                dot = canvas.create_oval(x_scaled - 7, y_scaled - 7, x_scaled + 7, y_scaled + 7, fill=color, outline=color, tags=f"dot_{location}")
            else:
                # Draw rectangles for other locations
                dot = canvas.create_rectangle(x_scaled - 7, y_scaled - 7, x_scaled + 7, y_scaled + 7, fill=color, outline=color, tags=f"dot_{location}")

            location_labels[location] = dot

            tooltip = ToolTip(canvas)
            tooltips[dot] = tooltip

            access_rules = location_logic.get(location, {}).get('access_rules', [])
            required_items = "\n".join([f"• {rule}" for rule in access_rules]) if access_rules else "No specific items required."
            tooltip_text = f"{location}\n\nRequired items:\n{required_items}"

            canvas.tag_bind(dot, "<Enter>", lambda event, text=tooltip_text: tooltips[event.widget.find_withtag("current")[0]].showtip(text, event.x_root, event.y_root))
            canvas.tag_bind(dot, "<Leave>", lambda event: tooltips[event.widget.find_withtag("current")[0]].hidetip())
            canvas.tag_bind(dot, "<Button-1>", lambda event, loc=location: dot_click_callback(loc))

            if right_click_callback:
                canvas.tag_bind(dot, "<Button-3>", lambda event, loc=location: right_click_callback(event, loc))

        return canvas, map_image, map_photo, location_labels, autoscan_label
    except Exception as e:
        logging.error(f"Error in setup_canvas: {e}")
        raise

def setup_scenario_canvas(root, scenario_keys, item_to_location, scenario_click_callback, image_cache):
    scenario_canvas = tk.Canvas(root, bg='black', width=381, height=285)
    scenario_canvas.images = []
    scenario_canvas.place(x=489, y=5, width=381, height=285) 

    scenario_images = {}
    tooltips = {}

    # Constants for grid layout
    columns = 4  # Number of columns
    spacing_x = 90  # Horizontal spacing between items
    spacing_y = 55  # Vertical spacing between items
    start_x = 35  # Starting X position
    start_y = 5  # Starting Y position

    # Calculate total number of rows needed
    total_rows = (len(scenario_keys) + columns - 1) // columns

    for i, key in enumerate(scenario_keys):
        item_info = scenario_items_bw[key]
        image_path = item_info["image_path"]
        
        image = load_image_with_size(image_path, image_cache, size=(30, 30))

        if image:
            col = i % columns  # Column position
            row = i // columns  # Row position
            
            # Center the last row if it is not a full row
            if row == total_rows - 1 and len(scenario_keys) % columns != 0:
                start_x_adjusted = start_x + ((columns - len(scenario_keys) % columns) * spacing_x) / 2
                x = start_x_adjusted + col * spacing_x
            else:
                x = start_x + col * spacing_x
            
            y = start_y + row * spacing_y
            image_id = scenario_canvas.create_image(x, y, anchor="nw", image=image)
                
            text_y = y + 35  # Place the text below the image
            scenario_canvas.create_text(x + 15, text_y, anchor='center', text=key, fill="white", font=("Arial", 8))
            scenario_images[key] = {'image': image, 'position': image_id}
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
    characters_canvas = tk.Canvas(root, bg='black', width=486, height=220)
    characters_canvas.images = []
    characters_canvas.place(x=5, y=5, width=486, height=220)
    

    character_images = {}
    start_x = 10
    y = 10

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
                x = start_x + i * 70
                image_id = characters_canvas.create_image(x, y, anchor="nw", image=image)
                characters_canvas.create_text(x + 20, y + 45, anchor="n", text=name, fill="white", font=("Arial", 10))
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
    add_characters_to_canvas(second_row_characters, start_x, y + 95)

    app.character_images = character_images
    return characters_canvas, character_images


def load_image(path):
    try:
        image = Image.open(path)
        image = image.resize((40, 40), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception as e:
        logging.error(f"Error loading image at {path}: {e}")
        return None
    
def load_image_cached(path, image_cache, size=(40, 40)):
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

def load_image_with_size(path, image_cache, size=(30, 30)):
    try:
        cache_key = (str(path), size)
        if cache_key in image_cache:
            return image_cache[cache_key]

        image = Image.open(path)
        image = image.resize(size, Image.Resampling.LANCZOS)
        photo_image = ImageTk.PhotoImage(image)
        image_cache[cache_key] = photo_image  # Cache the loaded and resized image
        return photo_image
    except Exception as e:
        logging.error(f"Error loading image at {path}: {e}")
        return None

def update_autoscan_label(label, is_auto_scan_on):
    if is_auto_scan_on:
        label.config(text="Autoscan: On", foreground="green")
    else:
        label.config(text="Autoscan: Off", foreground="red")
        
def on_mousewheel(event, canvas):
    # Determine the direction of the scroll
    direction = 1 if event.delta < 0 else -1
    canvas.yview_scroll(direction, "units")


def update_character_image(characters_canvas, character_images, name, is_active):
    character_info = character_images.get(name)
    if character_info:
        new_image = character_info['color_image'] if is_active else character_info['bw_image']
        characters_canvas.itemconfig(character_info['position'], image=new_image)
        character_info['current_image'] = new_image
        character_info['is_colored'] = is_active
        if not hasattr(characters_canvas, 'images'):
            characters_canvas.images = []
        characters_canvas.images.append(new_image)
        
def determine_location_color(location, inventory, scenario_items, location_logic):
    if location in ALWAYS_ACCESSIBLE_LOCATIONS:
        return COLORS['accessible']
    elif location in CITIES:
        return COLORS['city']
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
    return 'partly_accessible' if any(item in inventory or item in scenario_items for rule in rules for item in rule.split(',')) else 'not_accessible'

def toggle_maiden_image(canvas, maiden_images, name, check_all_colored):
    maiden_info = maiden_images.get(name)
    if maiden_info:
        if maiden_info['current_image'] == maiden_info['default_image']:
            new_image = maiden_info['color_image']
            maiden_info['is_colored'] = True
        else:
            new_image = maiden_info['default_image']
            maiden_info['is_colored'] = False

        canvas.itemconfig(maiden_info['position'], image=new_image)
        maiden_info['current_image'] = new_image
        if not hasattr(canvas, 'images'):
            canvas.images = []
        canvas.images.append(new_image)
        check_all_colored()

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
