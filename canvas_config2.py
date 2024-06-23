
import tkinter as tk
import tkinter.ttk as ttk
from PIL import Image, ImageTk, ImageEnhance
import os
from shared import tool_items_bw, scenario_items_bw, CITIES, IMAGES_DIR, ALWAYS_ACCESSIBLE_LOCATIONS, COLORS, characters, characters_bw, WIDGET_STORE
from helpers.file_loader import load_image
from logic import LocationLogic

# Path to the map image
map_address = os.path.join(IMAGES_DIR / "map", "map.jpg")

def setup_item_canvas(root):
    """
    Set up a canvas to display shop items.
    """
    item_canvas = tk.Canvas(root, bg='black', width=300, height=100)
    item_canvas.grid(column=0, row=0, padx=5, pady=5, sticky="nsew")
    return item_canvas

def setup_tools_canvas(root):
    """
    Set up a canvas to display tools.
    """
    tools_canvas = tk.Canvas(root, bg='black', width=300, height=100)
    tools_canvas.grid(column=1, row=0, padx=5, pady=5, sticky="nsew")
    return tools_canvas

def setup_maidens_canvas(root):
    """
    Set up a canvas to display maidens.
    """
    maidens_canvas = tk.Canvas(root, bg='black', width=300, height=100)
    maidens_canvas.grid(column=2, row=0, padx=5, pady=5, sticky="nsew")
    return maidens_canvas

def setup_spells_canvas(root):
    """
    Set up a canvas to display spells.
    """
    spells_canvas = tk.Canvas(root, bg='black', width=300, height=100)
    spells_canvas.grid(column=0, row=1, padx=5, pady=5, sticky="nsew")
    return spells_canvas

def setup_thief_canvas(root):
    """
    Set up a canvas to display thief-related information.
    """
    thief_canvas = tk.Canvas(root, bg='black', width=300, height=100)
    thief_canvas.grid(column=0, row=2, padx=5, pady=5, sticky="nsew")
    return thief_canvas

def setup_hints_canvas(root):
    """
    Set up a writable Text widget for hints.
    """
    hints_canvas = tk.Text(root, wrap="word", bg='black', fg='white', undo=True)
    hints_canvas.grid(column=0, row=3, padx=5, pady=5, sticky="nsew")
    return hints_canvas

def setup_map_canvas(root, map_address, locations, location_logic, inventory, scenario_items, dot_click_callback, right_click_callback=None):
    """
    Set up a canvas to display the map and handle location interactions.
    """
    try:
        # Create the canvas for the map
        canvas = tk.Canvas(root, bg='black', width=600, height=400)
        canvas.grid(column=1, row=3, columnspan=2, rowspan=2, padx=5, pady=5, sticky="nsew")

        # Load and resize the map image
        map_image = Image.open(map_address)
        scale_factor = min(600 / map_image.width, 400 / map_image.height)
        resized_map_image = map_image.resize((int(map_image.width * scale_factor), int(map_image.height * scale_factor)), Image.Resampling.LANCZOS)
        map_photo = ImageTk.PhotoImage(resized_map_image)

        # Configure the canvas with the map image
        canvas.config(width=int(map_image.width * scale_factor), height=int(map_image.height * scale_factor))
        canvas.create_image(0, 0, anchor=tk.NW, image=map_photo)
        canvas.scale_factor = scale_factor

        # Dictionary to store location labels
        location_labels = {}
        tooltips = {}

        # Add location dots to the canvas
        for location, coords in locations.items():
            x_scaled, y_scaled = coords[0] * scale_factor, coords[1] * scale_factor
            color = determine_location_color(location, inventory, scenario_items, location_logic)
            dot = canvas.create_oval(x_scaled - 5, y_scaled - 5, x_scaled + 5, y_scaled + 5, fill=color, outline=color, tags=f"dot_{location}")
            label = canvas.create_text(x_scaled, y_scaled + 10, text=location, fill="white", tags=f"label_{location}")
            location_labels[location] = (dot, label)
            
            # Set up tooltip handling
            tooltip = ToolTip(canvas)
            tooltips[dot] = tooltip

            access_rules = location_logic.get(location, {}).get('access_rules', [])
            required_items = "\n".join([f"• {rule}" for rule in access_rules]) if access_rules else "No specific items required."

            # Bind the tooltip to the dot
            canvas.tag_bind(dot, "<Enter>", lambda event, text=required_items: tooltips[dot].showtip(text, event.x_root, event.y_root))
            canvas.tag_bind(dot, "<Leave>", lambda event: tooltips[dot].hidetip())
            canvas.tag_bind(dot, "<Button-1>", lambda event, loc=location: dot_click_callback(loc))

            # Bind the right-click event to show the context menu, if the callback is provided
            if right_click_callback:
                canvas.tag_bind(dot, "<Button-3>", lambda event, loc=location: right_click_callback(event, loc))

        return canvas, map_image, map_photo, location_labels
    except Exception as e:
        print(f"Error in setup_map_canvas: {e}")
        raise


def setup_scenario_canvas(root):
    """
    Set up a canvas to display scenario-related information.
    """
    scenario_canvas = tk.Canvas(root, bg='black', width=900, height=200)
    scenario_canvas.grid(column=0, row=5, columnspan=3, rowspan=2, padx=5, pady=5, sticky="nsew")
    return scenario_canvas

def setup_characters_canvas(root):
    """
    Set up a canvas to display characters.
    """
    characters_canvas = tk.Canvas(root, bg='black', width=600, height=200)
    characters_canvas.grid(column=1, row=1, columnspan=2, rowspan=2, padx=5, pady=5, sticky="nsew")
    return characters_canvas

##############################

def update_character_image(characters_canvas, character_images, name, is_active):
    """
    Update the character image to colored if active, or dimmed (black-and-white) if inactive.
    """
    character_info = character_images.get(name)
    if character_info:
        new_image = character_info['color_image'] if is_active else character_info['bw_image']

        # Update the canvas with the new image
        characters_canvas.itemconfig(character_info['position'], image=new_image)
        character_info['current_image'] = new_image  # Update the current image reference
        character_info['is_colored'] = is_active

        # Keep a reference to the image to prevent it from being garbage collected
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
        print(f"Error adding location {location} at ({coords[0]}, {coords[1]}): {e}")

def check_access(location, inventory, scenario_items, location_logic):
    rules = location_logic.get(location, {}).get('access_rules', [])
    if not rules:
        return 'accessible'
    for rule in rules:
        items = rule.split(',')
        if all(item in inventory or item in scenario_items for item in items):
            return 'accessible'
    return 'partly_accessible' if any(item in inventory or item in scenario_items for rule in rules for item in rule.split(',')) else 'not_accessible'

class ToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None
        self.text = None

    def showtip(self, text, x, y):
        "Display text in tooltip window at a given position"
        self.text = text
        if self.tip_window or not self.text:
            return
        # Adjust x and y to place the tooltip closer to the image
        x = x + 10  # Offset slightly to the right
        y = y + 10  # Offset slightly down
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # removes the window decorations
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe0", relief=tk.SOLID, borderwidth=1,
            font=("tahoma", "8", "normal")
        )
        label.pack(ipadx=1)

    def hidetip(self):
        "Hide the tooltip"
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()
            