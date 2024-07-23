# logic.py

import os
from shared import load_json_cached, ALWAYS_ACCESSIBLE_LOCATIONS, CITIES, COLORS, DATA_DIR
import logging

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
        """
        Updates the accessibility status of locations based on the obtained items.
        
        :param obtained_items: A set of items that have been obtained by the player.
        """
        logging.info("Updating accessible locations based on obtained items...")
        
        for location, logic in self.locations_logic.items():
            accessible = self.is_location_accessible(logic, obtained_items, location)
            self.mark_location(location, accessible)
        
        logging.info("Accessible locations updated.")

    def is_location_accessible(self, logic, obtained_items, location):
        """
        Determines if a location is accessible based on the given logic and obtained items.
        
        :param logic: The access rules for the location.
        :param obtained_items: A set of items that have been obtained by the player.
        :return: True if the location is accessible, False otherwise.
        """
        # Special check for "Daos' Shrine" based on the colored status of all maidens
        if location == "Daos' Shrine":
            if all(self.maidens_images[maiden]['is_colored'] for maiden in ["Claire", "Lisa", "Marie"]) and self.scenario_items["engine"]['is_colored']:
                return True

        access_rules = logic.get("access_rules", [])
        for rule in access_rules:
            rule_items = rule.split(',')
            if all(item in obtained_items for item in rule_items):
                return True
        return False

    def mark_location(self, location, accessible):
        """
        Marks a location on the canvas as accessible or not accessible.
        
        :param location: The name of the location to update.
        :param accessible: Boolean indicating whether the location is accessible.
        """
        dot = self.location_labels.get(location)
        
        if dot:
            if location in ALWAYS_ACCESSIBLE_LOCATIONS:
                dot_color = COLORS['accessible']
            elif location in CITIES:
                dot_color = COLORS['city']
            else:
                dot_color = COLORS['accessible'] if accessible else COLORS['not_accessible']

            self.canvas.itemconfig(dot, fill=dot_color)
            
