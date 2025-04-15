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
import tkinter as tk
from tkinter import ttk, filedialog, Label, messagebox
import tkinter.font as tkFont
import tkinter.scrolledtext as scrolledtext
import os
import json
import logging
from PIL import Image, ImageTk
import tkinter.font as tkFont
from shared import characters, characters_bw, CITIES, item_spells, LOCATIONS, COLORS
import pyphen
from helpers.resalo import Reset, Save, Load
from helpers.item_management import create_item_entry, search_item_window , sort_by_location, sort_by_item_name
from auto.sync_game import sync_with_game, sync_tools, sync_keys, sync_chars, sync_maiden, sync_pos
from auto.inventory_scan import InventoryScanner, ScenarioScanner, CharacterScanner, MaidenScanner, SpoilerScanner, LocationScanner, PositionScanner, initialize_shared_variables
from auto.start_auto import startTracker

dic = pyphen.Pyphen(lang='en_US')

# Setting up the general window dimensions
def setup_interface(app):
    """
    Set up the main interface of the application.
    """
    app.root.geometry("700x830")  # Adjusted to a larger view for better visibility
    app.root.bind("<Configure>", app.on_resize)
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.root.resizable(False, False) # Fenstergröße fixieren
    
    style = ttk.Style()
    style.configure('Custom.TFrame', background='black')
    style.configure('Custom.TLabel', foreground='white', background='black')
    style.configure('Custom.TButton', width=2)
    
    create_custom_menu(app) # Benutzerdefiniertes Menü erstellen
    
    app.root.update()  # Force update

# Setting up the canvases
def setup_canvases(app):
    """
    Set up the various canvases in the application.
    """
    app.canvas, app.map_image, app.map_photo, app.location_labels = setup_canvas(
        app.root, app.map_address, app.LOCATIONS, app.locations_logic, app.inventory, app.scenario_items,
        dot_click_callback=app.on_dot_click, 
        right_click_callback=lambda event, loc: right_click_handler(app, event, loc),
        
    )

    app.item_canvas = setup_item_canvas(app.root)
    
    app.hints_canvas = setup_hints_canvas(app.root)
    
    app.tools_canvas, app.tool_images = setup_tools_canvas(
        app.root, list(app.tool_items_bw.keys()), app.on_tool_click, app.image_cache)    
     
    app.scenario_canvas, app.scenario_images = setup_scenario_canvas(
        app.root, list(app.scenario_items_bw.keys()), app.item_to_location, app.on_scenario_click, app.image_cache)
    
    app.characters_canvas, app.character_images = setup_characters_canvas(app.root, app.characters, app.image_cache, app)
    
    app.maidens_canvas, app.maidens_images = setup_maidens_canvas(app.root, app.characters, app.characters_bw, app.image_cache, app, app.on_maiden_click)
    
    return app.canvas

# creating and filling the About window
def show_about_window():
    """Show the 'About' window."""
    about_window = tk.Toplevel()
    about_window.title("About")
    about_window.geometry("300x400")  # Set window size

    # Create a scrolled text widget
    text_widget = scrolledtext.ScrolledText(about_window, wrap=tk.WORD, padx=10, pady=10, font=("Arial", 8))
    text_widget.pack(expand=True, fill=tk.BOTH)

    # Define font styles
    bold_font = tkFont.Font(weight="bold", family="Arial", size=8)

    # Insert text with formatting
    text_widget.insert(tk.END, "Thank you for using Lufia 2 Auto Tracker!\n\n", bold_font)
    text_widget.insert(tk.END, "This was my first project and took me quite some time.\n")
    text_widget.insert(tk.END, "Feel free to report any bugs or suggestions to:\n\n", bold_font)

    text_widget.insert(tk.END, "My Git Repository:\n", bold_font)
    text_widget.insert(tk.END, "https://github.com/RndmMeme/Lufia-2-Autotracker\n\n")

    text_widget.insert(tk.END, "My Discord:\n", bold_font)
    text_widget.insert(tk.END, "Rndmmeme#5100\n\n")

    text_widget.insert(tk.END, "Lufia 2 Community on Discord:\n", bold_font)
    text_widget.insert(tk.END, "Ancient Cave\n\n")

    text_widget.insert(tk.END, "Many thanks to:\n\n", bold_font)

    text_widget.insert(tk.END, "abyssonym (Creator of Lufia 2 Randomizer \"terrorwave\"):\n", bold_font)
    text_widget.insert(tk.END, "https://github.com/abyssonym/terrorwave\n")
    text_widget.insert(tk.END, "who patiently explained a lot of the secrets to me :)\n\n")

    text_widget.insert(tk.END, "The3X (Testing and Feedback):\n", bold_font)
    text_widget.insert(tk.END, "https://www.twitch.tv/the3rdx\n\n")

    text_widget.insert(tk.END, "The Lufia 2 Community\n\n", bold_font)

    text_widget.insert(tk.END, "And of course, you, who decided to use my tracker!\n\n", bold_font)

    text_widget.insert(tk.END, "Disclaimer:\n", bold_font)
    text_widget.insert(tk.END, "If you want to use this tracker for competitive plays please make sure it is accepted for tracking. ")
    text_widget.insert(tk.END, "Also make sure to either not use the auto tracking function or to ask whether it is allowed to be used.\n\n")
    
    text_widget.insert(tk.END, "RndmMeme\n", bold_font)
    text_widget.insert(tk.END, "Lufia 2 Auto Tracker v1.3 @2024-2025\n", bold_font)

    # Make text read-only
    text_widget.config(state=tk.DISABLED)


# creating and filling the Help window
def show_help_window():
    """Show the 'Help' window."""
    help_window = tk.Toplevel()
    help_window.title("Help")
    help_window.geometry("300x400")  # Set window size

    # Create a scrolled text widget
    text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, padx=10, pady=10, font=("Arial", 8))
    text_widget.pack(expand=True, fill=tk.BOTH)

    # Define font styles
    bold_font = tkFont.Font(weight="bold", family="Arial", size=8)

    # Insert text with formatting
    text_widget.insert(tk.END, "Welcome to Lufia 2 Auto Tracker!\n\n", bold_font)
    text_widget.insert(tk.END, "If you want to explore the application on your own, feel free to do so.\n")
    text_widget.insert(tk.END, "Otherwise, here are a few tips:\n\n", bold_font)

    text_widget.insert(tk.END, "Item/Spell Management:\n", bold_font)
    text_widget.insert(tk.END, "  - Right-click on cities (dots) to open the sub-menu.\n")
    text_widget.insert(tk.END, "    Search for your item and click on an entry to save it to the items/spells section.\n")
    text_widget.insert(tk.END, "  - The search window will auto-focus. You can also select multiple items.\n")
    text_widget.insert(tk.END, "  - Double-click on an item to save it to the item/spell section.\n")
    text_widget.insert(tk.END, "    Press 'ENTER' to add one or more items.\n\n")

    text_widget.insert(tk.END, "Character Management:\n", bold_font)
    text_widget.insert(tk.END, "  - Right-click on locations (squares) to open the character menu.\n")
    text_widget.insert(tk.END, "    Click on a character name to mark the character as 'obtained' and display the location where you found it.\n")
    text_widget.insert(tk.END, "  - A mini sprite of the character will appear at the location on the map.\n")
    text_widget.insert(tk.END, "  - If another location is obscured by the image, drag and drop it where you like.\n")
    text_widget.insert(tk.END, "  - A simple left-click on a character will color (and uncolor) it, but without location or mini-image.\n")
    text_widget.insert(tk.END, "  - A right-click on an obtained character will reset the character and remove the location and mini-image.\n\n")

    text_widget.insert(tk.END, "Location Management:\n", bold_font)
    text_widget.insert(tk.END, "  - Left-click on a square to change its color.\n\n")

    text_widget.insert(tk.END, "Color Codes:\n", bold_font)
    text_widget.insert(tk.END, "  red - not accessible\n")
    text_widget.insert(tk.END, "  orange - partially accessible\n")
    text_widget.insert(tk.END, "  green - fully accessible\n")
    text_widget.insert(tk.END, "  grey - cleared\n\n")

    text_widget.insert(tk.END, "Tracker:\n", bold_font)
    text_widget.insert(tk.END, "  Pressing any subcategory in 'Sync' will read your ingame progress.\n")
    text_widget.insert(tk.END, "  Pressing 'Player Color' let's you choose the color of the dot for your location.\n\n")

    # Make text read-only
    text_widget.config(state=tk.DISABLED)
    
# creating the custom menu ribbon
def create_custom_menu(app):
    """
    Create a custom menu ribbon.
    """
    menu_frame = tk.Frame(app.root ,bg=app.root.cget("bg")) # Frame erstellen
    menu_frame.pack(fill=tk.X, padx=3) # Frame anordnen
    
    options_button = tk.Menubutton(menu_frame, text="Options", relief=tk.RAISED) # Button erstellen
    options_button.pack(side=tk.LEFT) # Button anordnen
    
    options_menu = tk.Menu(options_button, tearoff=0) # Dropdown-Menü erstellen
    
    def reset_game_state():
        Reset(app).reset()
    
    def save_game_state():
        Save(app).save_game_state() 
    
    def load_game_state():
        Load(app).load_game_state() 

    options_menu.add_command(label="Reset", command=reset_game_state)
    options_menu.add_command(label="Save", command=save_game_state)
    options_menu.add_command(label="Load", command=load_game_state)

    options_button["menu"] = options_menu  # Attach the menu to the button
    
    # Tracker-Button (neu)
    tracker_button = tk.Menubutton(menu_frame, text="Tracker", relief=tk.RAISED)
    tracker_button.pack(side=tk.LEFT)
    tracker_menu = tk.Menu(tracker_button, tearoff=0)
        
    sync_menu = tk.Menu(tracker_menu, tearoff=0)
    
    sync_menu.add_command(label="All", command=lambda: sync_with_game(menu_frame, app))
    sync_menu.add_command(label="Tools", command=lambda: sync_tools(menu_frame, app))
    sync_menu.add_command(label="Keys", command=lambda: sync_keys(menu_frame, app))
    sync_menu.add_command(label="Chars", command=lambda: sync_chars(menu_frame, app))
    sync_menu.add_command(label="Maiden", command=lambda: sync_maiden(menu_frame, app))
    sync_menu.add_command(label="Pos", command=lambda: sync_pos(menu_frame, app))

    tracker_menu.add_cascade(label="Sync", menu=sync_menu)

    def choose_player_dot_color_wrapper(app):
        """Wrapper für die Farbauswahl."""
        if app.position_scanner:
            app.position_scanner.choose_predefined_color() # Neue Funktion aufrufen

    tracker_menu.add_command(label="Auto", command=lambda: toggle_checkboxes(menu_frame, app))
    tracker_menu.add_command(label="Player Color", command=lambda: choose_player_dot_color_wrapper(app))
    
    tracker_button["menu"] = tracker_menu
    
    auto_label = tk.Label(menu_frame, text=" ", bg=menu_frame.cget("bg")) # Label erstellen
    auto_label.pack(side=tk.LEFT) # Label anordnen
    
    # Checkbox-Variablen
    app.all_var = tk.BooleanVar()
    app.chars_var = tk.BooleanVar()
    app.tools_var = tk.BooleanVar()
    app.keys_var = tk.BooleanVar()
    app.maidens_var = tk.BooleanVar()
    app.position_var = tk.BooleanVar()
    
    # Checkboxen erstellen (anfangs ausgeblendet)
    all_checkbox = tk.Checkbutton(menu_frame, text="All", variable=app.all_var, command=lambda: update_checkbox_states(app))
    chars_checkbox = tk.Checkbutton(menu_frame, text="Chars", variable=app.chars_var, command=lambda: tracking(app, menu_frame, auto_label, app.chars_var, app.tools_var, app.keys_var, app.maidens_var, app.position_var))
    tools_checkbox = tk.Checkbutton(menu_frame, text="Tools", variable=app.tools_var, command=lambda: tracking(app, menu_frame, auto_label, app.chars_var, app.tools_var, app.keys_var, app.maidens_var, app.position_var))
    keys_checkbox = tk.Checkbutton(menu_frame, text="Keys", variable=app.keys_var, command=lambda: tracking(app, menu_frame, auto_label, app.chars_var, app.tools_var, app.keys_var, app.maidens_var, app.position_var))
    maidens_checkbox = tk.Checkbutton(menu_frame, text="Maidens", variable=app.maidens_var, command=lambda: tracking(app, menu_frame, auto_label, app.chars_var, app.tools_var, app.keys_var, app.maidens_var, app.position_var))
    position_checkbox = tk.Checkbutton(menu_frame, text="Pos", variable=app.position_var, command=lambda: tracking(app, menu_frame, auto_label, app.chars_var, app.tools_var, app.keys_var, app.maidens_var, app.position_var))
    
    def toggle_checkboxes(menu_frame, app):
        if app.auto_tracking_checkboxes_visible:
            # Checkboxen ausblenden
            app.auto_tracking_checkboxes_visible = False
            all_checkbox.pack_forget()
            chars_checkbox.pack_forget()
            tools_checkbox.pack_forget()
            keys_checkbox.pack_forget()
            maidens_checkbox.pack_forget()
            position_checkbox.pack_forget()
            auto_label.config(background=menu_frame.cget("bg"), text=" ")
        else:
            # Checkboxen einblenden
            app.auto_tracking_checkboxes_visible = True
            all_checkbox.pack(side=tk.LEFT)
            chars_checkbox.pack(side=tk.LEFT)
            tools_checkbox.pack(side=tk.LEFT)
            keys_checkbox.pack(side=tk.LEFT)
            maidens_checkbox.pack(side=tk.LEFT)
            position_checkbox.pack(side=tk.LEFT)
            auto_label.config(text="Auto Tracking:")
            update_checkbox_states(app)
            tracking(app, menu_frame, auto_label, app.chars_var, app.tools_var, app.keys_var, app.maidens_var, app.position_var)  
                
                
    def tracking(app, menu_frame, auto_label, chars_var, tools_var, keys_var, maidens_var, position_var,
             char_interval=10000, tools_interval=10000, keys_interval=10000, maidens_interval=10000, position_interval=700):

        if not hasattr(app, 'auto_tracker') or app.auto_tracker is None:
            app.auto_tracker = startTracker()

        if app.process is None or app.base_address is None:
            logging.info("Auto Tracking: Attempting to connect to emulator.")
            app.auto_tracker.retrieve_base_address()
            app.process, app.base_address = app.auto_tracker.process, app.auto_tracker.base_address
            if app.process is None or app.base_address is None:
                logging.warning("Auto Tracking: Emulator not found. Automatic tracking will not start.")
                auto_label.config(background=menu_frame.cget("bg"), text="Auto Tracking: (Emulator not found)")
                return

        tracking_aktiv = False

        # Cancel all existing timers first
        if hasattr(app, "timer_ids"):
            for key in list(app.timer_ids.keys()):
                app.root.after_cancel(app.timer_ids[key])
            app.timer_ids.clear()
        else:
            app.timer_ids = {}
            
        if not hasattr(app, "sync_already_initialized"):
            app.sync_already_initialized = set()

        def schedule_auto_sync(name, interval, sync_function):
            """Utility function to auto-sync on a timer silently."""
            def loop():
                # Only show banner on first run, if not suppressed
                is_first = name not in app.sync_already_initialized
                app.sync_already_initialized.add(name)

                
                sync_function(menu_frame, app, silent=True) if name == "maidens" else sync_function(menu_frame, app)
                app.timer_ids[name] = app.root.after(interval, loop)
            loop()

        # Chars
        if chars_var.get():
            tracking_aktiv = True
            schedule_auto_sync("char", char_interval, sync_chars)

        # Tools
        if tools_var.get():
            tracking_aktiv = True
            schedule_auto_sync("tools", tools_interval, sync_tools)

        # Keys
        if keys_var.get():
            tracking_aktiv = True
            schedule_auto_sync("keys", keys_interval, sync_keys)

        # Maidens
        if maidens_var.get():
            tracking_aktiv = True
            schedule_auto_sync("maidens", maidens_interval, sync_maiden)

        # Position-Scan
        if position_var.get():
            tracking_aktiv = True

            def auto_sync_pos():
                sync_pos(menu_frame, app, silent=True)
                app.timer_ids["position"] = app.root.after(position_interval, auto_sync_pos)

            auto_sync_pos()
        else:
            if "position" in app.timer_ids:
                app.root.after_cancel(app.timer_ids["position"])
                del app.timer_ids["position"]


        # Auto-Label aktualisieren
        if tracking_aktiv:
            auto_label.config(background="lightgreen", text="Auto Tracking:")
        else:
            auto_label.config(background=menu_frame.cget("bg"), text="Auto Tracking:")

    app.auto_tracking_checkboxes_visible = False  # Checkboxen anfangs ausgeblendet

    
    def update_checkbox_states(app):
        if app.all_var.get():
            
            app.chars_var.set(True)
            app.tools_var.set(True)
            app.keys_var.set(True)
            app.maidens_var.set(True)
            app.position_var.set(True)
            auto_label.config(background="lightgreen")
        else:
            app.chars_var.set(False)
            app.tools_var.set(False)
            app.keys_var.set(False)
            app.maidens_var.set(False)
            app.position_var.set(False)
            auto_label.config(background=menu_frame.cget("bg")) 
        
        app.root.after_idle(lambda: tracking(app, app.root.children['!frame'], app.root.children['!frame'].children['!label'],
             app.chars_var, app.tools_var, app.keys_var, app.maidens_var, app.position_var))
    
    about_button = tk.Button(menu_frame, text="About", command=show_about_window) # Button erstellen
    about_button.pack(side=tk.RIGHT) # Button anordnen

    help_button = tk.Button(menu_frame, text="Help", command=show_help_window) # Button erstellen
    help_button.pack(side=tk.RIGHT) # Button anordnen
    
    def update_tracking_started(event):
        tracker_menu.entryconfig("Auto", background="lightgreen")
        auto_label.config(background="lightgreen", text="Auto Tracking: Active")

    def update_tracking_stopped(event):
        tracker_menu.entryconfig("Auto", background=menu_frame.cget("bg"))
        auto_label.config(background=menu_frame.cget("bg"), text="Auto Tracking: Inactive")

    app.root.bind("<<TrackingStarted>>", update_tracking_started)
    app.root.bind("<<TrackingStopped>>", update_tracking_stopped)
    
        
# right click handler for the context menus
def right_click_handler(app, event, location):
    show_context_menu(app, event, location)

def show_context_menu(app, event, location):
    context_menu = tk.Menu(app.root, tearoff=0)

    # Set the font size for the context menu
    new_font = tkFont.Font(family="Helvetica", size=10)  # You can change the size and family as desired
    app.root.option_add("*Menu*Font", new_font)

    if location in CITIES:
        context_menu.add_command(label="Search",
                                 command=lambda: search_item_window(context_menu, location, app))
                                 
    else:
        context_menu.add_command(label="Assign Character", command=lambda: show_character_menu(app, location))

    context_menu.configure(font=new_font)
    context_menu.post(event.x_root, event.y_root)

# functions to add (and remove) location name and mini character image to the map and canvas
     
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
        
def make_draggable(canvas, item):
    """Macht ein Canvas-Item mit der Maus verschiebbar."""
    data = {"x": 0, "y": 0}

    def on_drag_start(event):
        """Merkt sich die Startposition der Maus beim Ziehen."""
        data["x"] = event.x
        data["y"] = event.y
        canvas.itemconfig(item, state="normal") #Stellt sicher, dass das Item nicht ausgeblendet ist

    def on_drag_motion(event):
        """Bewegt das Item während des Ziehens."""
        delta_x = event.x - data["x"]
        delta_y = event.y - data["y"]
        canvas.move(item, delta_x, delta_y)
        data["x"] = event.x
        data["y"] = event.y

    def on_drag_release(event):
        """Wird aufgerufen, wenn die Maustaste losgelassen wird."""
        pass # Hier könnten weitere Aktionen ausgeführt werden, z.B. Speichern der neuen Position

    canvas.tag_bind(item, "<ButtonPress-1>", on_drag_start) #ButtonPress anstatt nur Button
    canvas.tag_bind(item, "<B1-Motion>", on_drag_motion)
    canvas.tag_bind(item, "<ButtonRelease-1>", on_drag_release) #ButtonRelease hinzufügen

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

    if hasattr(app, 'location_character_images') and location in app.location_character_images:
        existing_character = app.location_character_images[location]['character']
        # *** Remove the existing character ***
        if existing_character:  # Überprüfen, ob ein Charakter existiert, bevor wir ihn entfernen
            remove_character_location(app, existing_character)
            
    image_width = 30
    image_height = 30

    
    update_character_image(app.characters_canvas, app.character_images, character_name, True)

    # Intelligente Textaufteilung (verbessert)
    max_line_length = 9
    words = location.split()
    lines = []
    
    for word in words :
        if len(word) > max_line_length and len(word) > 3:
            hyphenated_word = dic.inserted(word) #Silbentrennung mit pyphen
            parts = hyphenated_word.split("-")
            for part in parts[:-1]: #Alle Teile außer dem letzten
                lines.append(part + "-") #Bindestrich hinzufügen
            lines.append(parts[-1]) #Letzten Teil ohne Bindestrich hinzufügen
        else:
            lines.append(word)

    location_text = "\n".join(lines)
    

    char_info = app.character_images.get(character_name)
    if not char_info:
        return

    char_image_id = char_info['position']
    char_position = app.characters_canvas.coords(char_image_id)
    
    if not char_position:
        return

    # Text erstellen (mit korrekter Positionierung)
    x_offset = char_position[0] + 1 # Start x-Position des Textes = Start x-Position des Bildes
    y_offset = char_position[1] + image_height + 25 # Direkt unter dem Bild + kleiner Abstand

    text_id = app.characters_canvas.create_text(
        x_offset, y_offset,
        text=location_text,
        fill="white",
        anchor="nw",  # Wichtig: Anker auf "nw" (northwest) setzen
        tags=(f"location_text_{character_name}", "location_text")
    )
    app.characters_canvas.tag_bind(char_info['position'], "<Button-3>", lambda event: remove_character_location(app, character_name))

    app.characters_canvas.tag_raise(text_id)
    app.characters_canvas.update_idletasks()

    # *** NEU: Bild auf der Karte hinzufügen ***
    character_image_path = characters[character_name]["image_path"]
    character_image = Image.open(character_image_path)
    
    desired_size =(image_width, image_height)
    character_image_small = character_image.resize(desired_size)  # Größe anpassen

    # Convert to PhotoImage for Tkinter canvas
    character_image_small = ImageTk.PhotoImage(character_image_small)

    # Koordinaten der Location abrufen (jetzt mit location_name)
    location_coords = LOCATIONS[location]
    x_scaled = location_coords[0] * app.canvas.scale_factor_x  # Skalierung in x-Richtung
    y_scaled = location_coords[1] * app.canvas.scale_factor_y  # Skalierung in y-Richtung
    
    # Bild auf der Karte platzieren (mit etwas Offset)
    image_id = app.canvas.create_image(x_scaled + 10, y_scaled - 10, anchor=tk.NW, image=character_image_small, tags=(f"location_image_{character_name}", "location_image"))
    app.canvas.images.append(character_image_small)
    make_draggable(app.canvas, image_id)
    
    # Speichern der Bild-ID und Zuordnung in app
    if not hasattr(app, 'location_character_images'):
        app.location_character_images = {}
    app.location_character_images[location] = {
        'character': character_name, 
        'character_position': char_image_id,
        'canvas_x': x_offset,  # Nur die x-Koordinate
        'canvas_y': y_offset,  # Nur die y-Koordinate
        'image_id': image_id, 
        'coords': (x_scaled + 10, y_scaled - 10), 
        "image_path": characters[character_name]["image_path"]
        } 
    
    # *** NEU: Farbe des Punkts ändern ***
    if location in app.location_labels:  # Überprüfen, ob ein Punkt für die Location existiert
        dot = app.location_labels[location]
        app.canvas.itemconfig(dot, fill=COLORS['cleared']) # Farbe auf "cleared" setzen
    

def remove_character_location(app, character_name):
    
    text_tags = f"location_text_{character_name}"
    
    app.characters_canvas.delete(text_tags)
    
    app.manual_toggles[character_name] = False
    update_character_image(app.characters_canvas, app.character_images, character_name, False)

    # *** NEU: Bild von der Karte entfernen ***
    if hasattr(app, 'location_character_images'):
        locations_to_remove = []
        for location, data in app.location_character_images.items():
            if data['character'] == character_name:
                app.canvas.delete(data['image_id'])
                app.canvas.update_idletasks()
                locations_to_remove.append(location)
        for location in locations_to_remove:
            del app.location_character_images[location]
    
    

    

    
