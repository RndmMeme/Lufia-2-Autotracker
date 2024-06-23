import tkinter as tk
import tkinter.ttk as ttk
from PIL import Image, ImageTk, ImageEnhance
import os
from shared import tool_items_bw, scenario_items_bw, CITIES, IMAGES_DIR, ALWAYS_ACCESSIBLE_LOCATIONS, COLORS, characters, characters_bw, WIDGET_STORE
from helpers.file_loader import load_image
from logic import LocationLogic


# Path to the map image
map_address = os.path.join(IMAGES_DIR / "map", "map.jpg")

def check_access(location, inventory, scenario_items, location_logic):
    rules = location_logic.get(location, {}).get('access_rules', [])
    if not rules:
        return 'accessible'
    for rule in rules:
        items = rule.split(',')
        if all(item in inventory or item in scenario_items for item in items):
            return 'accessible'
    return 'partly_accessible' if any(item in inventory or item in scenario_items for rule in rules for item in rule.split(',')) else 'not_accessible'

def setup_canvas(root, map_address, locations, location_logic, inventory, scenario_items, dot_click_callback, right_click_callback=None):
    try:
        canvas = tk.Canvas(root, width=1500, height=1500)
        canvas.grid(column=2, row=0, rowspan=200, padx=1, pady=75, sticky="nsew")

        map_image = Image.open(map_address)
        scale_factor = min(1200 / map_image.width, 500 / map_image.height)
        resized_map_image = map_image.resize((int(map_image.width * scale_factor), int(map_image.height * scale_factor)), Image.Resampling.LANCZOS)
        map_photo = ImageTk.PhotoImage(resized_map_image)
        canvas.config(width=int(map_image.width * scale_factor), height=int(map_image.height * scale_factor))
        canvas.create_image(0, 0, anchor=tk.NW, image=map_photo)
        canvas.scale_factor = scale_factor

        location_labels = {}
        tooltips = {}

        for location, coords in locations.items():
            x_scaled, y_scaled = coords[0] * scale_factor, coords[1] * scale_factor
            color = determine_location_color(location, inventory, scenario_items, location_logic)
            dot = canvas.create_oval(x_scaled - 5, y_scaled - 5, x_scaled + 5, y_scaled + 5, fill=color, outline=color, tags=f"dot_{location}")
            label = canvas.create_text(x_scaled, y_scaled + 10, text=location, fill="white", tags=f"label_{location}")
            location_labels[location] = (dot, label)
            

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
        print(f"Error in setup_canvas: {e}")
        raise

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

def on_resize(event, root, original_width, original_height, map_image, canvas, location_labels, locations):
    try:
        new_width = root.winfo_width()
        new_height = root.winfo_height()
        

        # Calculate the new scale factor based on the new size
        new_scale_factor = min(new_width / original_width, new_height / original_height)
        

        # Resize the map image
        new_map_width = int(original_width * new_scale_factor)
        new_map_height = int(original_height * new_scale_factor)
        resized_map_image = map_image.resize((new_map_width, new_map_height), Image.Resampling.LANCZOS)
        map_photo = ImageTk.PhotoImage(resized_map_image)

        # Update the canvas and image
        canvas.config(width=new_map_width, height=new_map_height)
        canvas.create_image(0, 0, anchor=tk.NW, image=map_photo)
        canvas.scale_factor = new_scale_factor
        

        # Update the locations
        for location, (dot, label) in location_labels.items():
            x, y = locations[location]
            x_scaled = x * new_scale_factor
            y_scaled = y * new_scale_factor
            canvas.coords(dot, x_scaled - 5, y_scaled - 5, x_scaled + 5, y_scaled + 5)
            canvas.coords(label, x_scaled, y_scaled + 10)
    except Exception as e:
        print(f"Error in on_resize: {e}")

def load_image(path):
    try:
        image = Image.open(path)
        image = image.resize((40, 40), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception as e:
        print(f"Error loading image at {path}: {e}")
        return None
    
def load_image_cached(path, image_cache, size=(40, 40)):
    """
    Load an image from the given path using the cache if available.
    """
    cache_key = (str(path), size)
    if cache_key in image_cache:
        return image_cache[cache_key]

    try:
        image = Image.open(path)
        image = image.resize(size, Image.Resampling.LANCZOS)
        photo_image = ImageTk.PhotoImage(image)
        image_cache[cache_key] = photo_image  # Cache the loaded and resized image
        return photo_image
    except Exception as e:
        print(f"Error loading image at {path}: {e}")
        return None



def load_image_with_size(path, image_cache, size=None):
    """
    Load an image from the given path using the cache if available, with an optional size parameter to resize.
    
    Args:
    path (str): Path to the image file.
    image_cache (dict): A dictionary used to cache images.
    size (tuple): Desired size as (width, height).

    Returns:
    ImageTk.PhotoImage: The loaded image object.
    """
    if path in image_cache:
        return image_cache[path]

    try:
        image = Image.open(path)
        if size:
            image = image.resize(size, Image.Resampling.LANCZOS)
        photo_image = ImageTk.PhotoImage(image)
        image_cache[path] = photo_image
        return photo_image
    except Exception as e:
        print(f"Error loading image at {path}: {e}")
        return None


def setup_tools_canvas(root, tools_keys, tool_click_callback, image_cache):
    tools_canvas = tk.Canvas(root, bg="black", highlightthickness=0, width=300, height=70)
    tools_canvas.grid(column=2, row=0, padx=2, pady=5, sticky="nw")
    

    tool_images = {}
    for i, key in enumerate(tools_keys):
        image_path = tool_items_bw[key]["image_path"]
        image = load_image_cached(image_path, image_cache)
        if image:
            x = 20 + i * 60  # Calculate x position for each image
            y = 10  # Fixed y position
            image_id = tools_canvas.create_image(x, y, anchor="nw", image=image)
            tools_canvas.create_text(x + 13, y + 32, anchor="n", text=key, fill="white", font=("Arial", 8))
            tool_images[key] = {'image': image, 'position': image_id}  # Store image and position
            
            # Bind the click event to the tool image
            tools_canvas.tag_bind(image_id, "<Button-1>", lambda event, tool=key: tool_click_callback(tool))
            
            # Save the reference to the image to prevent it from being garbage collected
            if not hasattr(tools_canvas, 'images'):
                tools_canvas.images = []
            tools_canvas.images.append(image)

    return tools_canvas, tool_images

def setup_scenario_canvas(root, scenario_keys, item_to_location, scenario_click_callback, image_cache):
    scenario_canvas = tk.Canvas(root, bg="black", highlightthickness=0, width=150, height=724)
    scenario_canvas.grid(column=2, row=0, padx=545, pady=5, sticky="nw")

    scenario_images = {}
    tooltips = {}

    for i, key in enumerate(scenario_keys):
        item_info = scenario_items_bw[key]
        image_path = item_info["image_path"]

        # Load and resize the image to 30x30 for scenario items
        image = load_image_with_size(image_path, image_cache, size=(30, 30))

        if image:
            x = 20 + (i % 2) * 80  # Calculate x position for each image
            y = 30 + (i // 2) * 65  # Calculate y position for each image
            image_id = scenario_canvas.create_image(x, y, anchor="nw", image=image)
            scenario_canvas.create_text(x + 15, y + 35, anchor="n", text=key, fill="white", font=("Arial", 8))
            scenario_images[key] = {'image': image, 'position': image_id}  # Store image and position

            # Bind the click event to the scenario item image
            scenario_canvas.tag_bind(image_id, "<Button-1>", lambda event, scenario=key: scenario_click_callback(scenario))

            # Determine the locations for this item
            locations = item_to_location.get(key, [])
            location_text = ", ".join(locations) if locations else "No specific location"

            # Create tooltip for each scenario item
            tooltip = ToolTip(scenario_canvas)
            tooltips[image_id] = tooltip
            
            # Bind the tooltip to mouse events
            scenario_canvas.tag_bind(image_id, "<Enter>", lambda event, location_text=location_text: tooltips[event.widget.find_withtag("current")[0]].showtip(location_text, event.x_root, event.y_root))
            scenario_canvas.tag_bind(image_id, "<Leave>", lambda event: tooltips[event.widget.find_withtag("current")[0]].hidetip())

            # Save the reference to the image to prevent it from being garbage collected
            if not hasattr(scenario_canvas, 'images'):
                scenario_canvas.images = []
            scenario_canvas.images.append(image)

    return scenario_canvas, scenario_images

def setup_characters_canvas(root, characters, image_cache, app):
    characters_canvas = tk.Canvas(root, bg="black", highlightthickness=0, width=537, height=180)
    characters_canvas.grid(column=2, row=0, padx=3, pady=578, sticky="nw")
    
    character_images = {}
    start_x = 20  # Starting x position for characters
    y = 30  # Adjusted fixed y position to move characters lower

    # Determine the character sets to be displayed
    first_row_characters = list(characters.keys())[:7]  # First 7 characters
    second_row_characters = list(characters.keys())[-7:]  # Last 7 characters (capsules)

    # Function to determine the black-and-white image path
    def get_bw_image_path(original_path):
        base, ext = os.path.splitext(original_path)
        return base + "bw" + ext

    def add_characters_to_canvas(characters_list, start_x, y):
        for i, name in enumerate(characters_list):
            original_image_path = characters[name]["image_path"]
            bw_image_path = get_bw_image_path(original_image_path)

            # Check if the black-and-white image exists, if not, fallback to the original image
            image_path_to_load = bw_image_path if os.path.exists(bw_image_path) else original_image_path
            image = load_image_cached(image_path_to_load, image_cache, size=(40, 40))  # Ensure 40x40 size

            if image:
                x = start_x + i * 75  # Position x based on index, adjust spacing as needed
                image_id = characters_canvas.create_image(x, y, anchor="nw", image=image)
                characters_canvas.create_text(x + 20, y + 45, anchor="n", text=name, fill="white", font=("Arial", 10))  # Adjusted text position
                character_images[name] = {
                    'bw_image': load_image_cached(bw_image_path, image_cache, size=(40, 40)),
                    'color_image': load_image_cached(original_image_path, image_cache, size=(40, 40)),
                    'current_image': image,
                    'image_path': image_path_to_load,
                    'position': image_id,  # Store the canvas item ID
                    'is_colored': False  # Initialize as not colored
                }

                # Bind the click event to toggle the character image
                characters_canvas.tag_bind(image_id, "<Button-1>", lambda event, n=name: toggle_character_image(characters_canvas, character_images, n, app))

                # Save the reference to the image to prevent it from being garbage collected
                if not hasattr(characters_canvas, 'images'):
                    characters_canvas.images = []
                characters_canvas.images.append(image)

    # Add the first row of characters
    add_characters_to_canvas(first_row_characters, start_x, y)

    # Add the second row of characters
    add_characters_to_canvas(second_row_characters, start_x, y + 90)  # Adjusted y position for the second row

    app.character_images = character_images  # Ensure app has the character images

    return characters_canvas, character_images


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

def setup_maidens_canvas(root, characters, characters_bw, image_cache, check_all_colored):
    """
    Set up the maidens canvas with black and white images initially.
    """
    # Create the canvas
    maidens_canvas = tk.Canvas(root, bg="black", highlightthickness=0, width=235, height=70)
    maidens_canvas.grid(column=2, row=0, padx=305, pady=5, sticky="nw")

    maiden_images = {}

    # Define the maidens and their corresponding images
    maiden_names = ["Claire", "Lisa", "Marie"]
    row_y = 3  # Fixed y position for the single row of maidens

    for i, name in enumerate(maiden_names):
        # Load the black and white image path
        bw_image_path = characters_bw.get(name, {}).get("image_path")
        if bw_image_path:
            bw_image_path = os.path.join(IMAGES_DIR, bw_image_path)  # Resolve full path
            bw_image = load_image_cached(bw_image_path, image_cache)
        else:
            print(f"Error: BW image path not found for {name}. Skipping...")
            continue

        # Load the colored image path
        color_image_path = characters.get(name, {}).get("image_path")
        if color_image_path:
            color_image_path = os.path.join(IMAGES_DIR, color_image_path)  # Resolve full path
            color_image = load_image_cached(color_image_path, image_cache)
        else:
            print(f"Error: Color image path not found for {name}.")
            color_image = bw_image  # Fallback to BW image if color image is not found

        if bw_image:
            x = 50 + i * 60  # Adjust x position for proper spacing
            y = row_y
            image_id = maidens_canvas.create_image(x, y, anchor="nw", image=bw_image)
            maidens_canvas.create_text(x + 20, y + 40, anchor="n", text=name, fill="white", font=("Arial", 10))

            maiden_images[name] = {
                'default_image': bw_image,
                'color_image': color_image,
                'current_image': bw_image,
                'image_path': bw_image_path,
                'color_image_path': color_image_path,
                'position': image_id,
                'is_colored': False  # Initialize as not colored
            }

            # Bind the click event to toggle the image
            maidens_canvas.tag_bind(image_id, "<Button-1>", lambda event, n=name: toggle_maiden_image(maidens_canvas, maiden_images, n, check_all_colored))

            # Save the reference to the image to prevent it from being garbage collected
            if not hasattr(maidens_canvas, 'images'):
                maidens_canvas.images = []
            maidens_canvas.images.append(bw_image)

    return maidens_canvas, maiden_images


def toggle_maiden_image(canvas, maiden_images, name, check_all_colored):
    maiden_info = maiden_images.get(name)
    if maiden_info:
        # Determine the new image based on the current image
        if maiden_info['current_image'] == maiden_info['default_image']:
            new_image = maiden_info['color_image']
            maiden_info['is_colored'] = True  # Mark as colored
        else:
            new_image = maiden_info['default_image']
            maiden_info['is_colored'] = False  # Mark as not colored

        # Update the canvas item with the new image
        canvas.itemconfig(maiden_info['position'], image=new_image)
        maiden_info['current_image'] = new_image  # Update the current image reference

        # Keep a reference to the image to prevent garbage collection
        if not hasattr(canvas, 'images'):
            canvas.images = []
        canvas.images.append(new_image)

        # Check if all maidens are colored
        check_all_colored()


def toggle_character_image(characters_canvas, character_images, name, app):
    character_info = character_images.get(name)
    if character_info:
        new_image = character_info['bw_image'] if character_info['is_colored'] else character_info['color_image']
        
        # Update the canvas with the new image
        characters_canvas.itemconfig(character_info['position'], image=new_image)
        character_info['current_image'] = new_image  # Update the current image reference
        
        # Toggle the is_colored state
        character_info['is_colored'] = not character_info['is_colored']
        app.manual_toggles[name] = character_info['is_colored']

        # Keep a reference to the image to prevent it from being garbage collected
        if not hasattr(characters_canvas, 'images'):
            characters_canvas.images = []
        characters_canvas.images.append(new_image)
        
        print(f"Character {name} toggled manually. Current state: {'colored' if character_info['is_colored'] else 'black-and-white'}.")


def create_tabbed_interface(root):
    """
    Creates a tabbed interface with a scrollable canvas for each tab.
    """
    left_frame = ttk.Frame(root)
    left_frame.grid(row=0, column=0, sticky='nsew')
    root.grid_columnconfigure(0, weight=0)  # Non-resizable

    # Create a notebook (tabbed interface)
    notebook = ttk.Notebook(left_frame)
    notebook.pack(expand=1, fill='both')

    # Tab names
    tabs = ["Shop Item", "Spell", "Thief", "Hints"]

    # Dictionary to hold tab references
    tab_references = {}

    # Create a tab with a scrollable canvas for each tab name
    for tab_name in tabs:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=tab_name)

        if tab_name == "Hints":
            # For the "Hints" tab, add a Text widget for user input
            hints_text = tk.Text(frame, wrap="word", bg='white', fg='black', undo=True)
            hints_text.pack(expand=1, fill='both', padx=5, pady=5)

            # Optionally, add a scrollbar for the Text widget
            scrollbar = ttk.Scrollbar(frame, command=hints_text.yview)
            scrollbar.pack(side='right', fill='y')
            hints_text.config(yscrollcommand=scrollbar.set)

            # Save the reference to the Text widget for later use
            frame.hints_text = hints_text
            tab_references[tab_name] = hints_text  # Store the reference
        else:
            # Create a canvas with a black background for other tabs
            canvas = tk.Canvas(frame, bg='black', width=200, height=100)

            # Create scrollbars
            v_scrollbar = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(frame, orient='horizontal', command=canvas.xview)

            # Configure the canvas to use the scrollbars
            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

            # Pack the canvas and scrollbars
            canvas.pack(side='left', expand=True, fill='both')
            v_scrollbar.pack(side='right', fill='y')
            h_scrollbar.pack(side='bottom', fill='x')

            # Create a frame inside the canvas to hold the content
            scrollable_frame = ttk.Frame(canvas, style="Tab.TFrame")
            scrollable_frame.bind("<Configure>", lambda e, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")))

            # Add the frame to the canvas
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

            tab_references[tab_name] = scrollable_frame  # Store the reference

    return notebook, tab_references  # Return the notebook and the tab references


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

    
