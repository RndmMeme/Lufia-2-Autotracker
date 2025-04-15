# logic.py

import os
from shared import load_json_cached, ALWAYS_ACCESSIBLE_LOCATIONS, CITIES, COLORS, DATA_DIR
import logging
import traceback

class LocationLogic:
    def __init__(self, script_dir, location_labels, canvas, maidens_images):
        """
        Initializes the LocationLogic with the necessary data and components.
        
        :param script_dir: The base directory for script files.
        :param location_labels: Dictionary mapping locations to their corresponding canvas elements.
        :param canvas: The Tkinter canvas where the locations are drawn.
        """
        self.locations_logic = load_json_cached(DATA_DIR / "locations_logic.json")
        self.location_labels = location_labels
        self.canvas = canvas
        self.maidens_images = maidens_images  # Store the maidens' status

    def update_accessible_locations(self, obtained_items):
        if not obtained_items:  # Check if obtained_items is empty
            for location, _ in self.locations_logic.items():
                self.mark_location(location, False)  # Reset color to inaccessible
        else:
            for location, logic in self.locations_logic.items():
                accessible = self.is_location_accessible(obtained_items, location)
                self.mark_location(location, accessible)
        
        logging.info("Accessible locations updated.")

    def is_location_accessible(self, obtained_items, location):
        """
        Determines if a location is accessible based on the given logic and obtained items.
        
        :param obtained_items: A set of items that have been obtained by the player.
        :param location: The location to check for accessibility.
        :return: True if the location is accessible, False otherwise.
        """
        if location in ALWAYS_ACCESSIBLE_LOCATIONS:
            return True

        logic = self.locations_logic.get(location)
        if logic is None:
            return False  # Location not found in logic, treat as inaccessible

        access_rules = logic.get("access_rules", [])
        if not access_rules:
            return True # if access_rules is empty, then the location is accessible.

        for rule in access_rules:
            rule_items = rule.split(',')
            if all(item.strip() in obtained_items for item in rule_items):
                return True
        return False

    def mark_location(self, location, accessible, cleared=False):
        """
        Marks a location on the canvas as accessible or not accessible, excluding "cleared" locations.
        """
        dot = self.location_labels.get(location)

        if dot:
            if cleared:
                self.canvas.itemconfig(dot, fill=COLORS['cleared'])
                return
            
            current_color = self.canvas.itemcget(dot, "fill") #Aktuelle Farbe abrufen

            if current_color == COLORS['cleared']: #Wenn die Location bereits cleared ist, nichts machen
                return

            if location in ALWAYS_ACCESSIBLE_LOCATIONS:
                dot_color = COLORS['accessible']
            elif location in CITIES:
                dot_color = COLORS['city'] if accessible else COLORS['not_accessible']
            else:
                dot_color = COLORS['accessible'] if accessible else COLORS['not_accessible']

            self.canvas.itemconfig(dot, fill=dot_color)
            
