# setup.py

from canvas_config import (
    setup_canvas, 
    setup_tools_canvas, 
    setup_scenario_canvas, 
    setup_maidens_canvas, 
    setup_characters_canvas
)
from .inventory_scan import InventoryScanner, ScenarioScanner, CharacterScanner
from tkinter import Menu
from .button_functions import clear_game_state, sync_game_state
from shared import tool_items_bw, scenario_items_bw, characters, map_address

def setup_interface(app):
    app.root.geometry("1100x665")
    app.root.bind("<Configure>", app.on_resize)
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
    create_menu(app)

def setup_canvases(app):
    """
    Set up all the canvases for the application.
    """
    print("Setting up canvases...")
    app.canvas, app.map_image, app.map_photo, app.location_labels = setup_canvas(
        app.root, map_address, app.LOCATIONS, app.locations_logic, app.inventory, app.scenario_items, dot_click_callback=app.on_dot_click)
    
    # Use a shared image cache to minimize image loading
    image_cache = app.image_cache
    
    app.tools_canvas, app.tool_images = setup_tools_canvas(app.root, list(tool_items_bw.keys()), app.on_tool_click, image_cache)
    app.scenario_canvas, app.scenario_images = setup_scenario_canvas(app.root, list(scenario_items_bw.keys()), app.item_to_location, app.on_scenario_click, image_cache)
    app.characters_canvas, app.character_images = setup_characters_canvas(app.root, characters, image_cache)
    app.maidens_canvas, app.maidens_images = setup_maidens_canvas(app.root, characters, image_cache)
    print("Canvases setup complete.")

def setup_scanners(app):
    """
    Set up inventory and scenario scanners.
    """
    print("Setting up scanners...")
    app.scanner = InventoryScanner(app, app.tools_canvas, app.tool_images, app.location_labels)
    app.sscanner = ScenarioScanner(app, app.scenario_canvas, app.scenario_images, app.location_labels)
    app.cscanner = CharacterScanner(app, app.characters_canvas, app.character_images, app.maidens_canvas, app.maidens_images)
    print("Scanners setup complete.")

def create_menu(app):
    """
    Create the application menu.
    """
    menubar = Menu(app.root)
    app.root.config(menu=menubar)
    
    options_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Options", menu=options_menu)
    
    options_menu.add_command(label="Clear", command=lambda: clear_game_state(app))
    options_menu.add_command(label="Sync", command=lambda: sync_game_state(app))
    options_menu.add_command(label="Location Names", command=app.toggle_location_labels)
    options_menu.add_command(label="Toggle City Names", command=app.toggle_city_labels)
    print("Menu created.")
