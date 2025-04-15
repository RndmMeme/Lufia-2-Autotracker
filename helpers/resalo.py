# resalo.py

import tkinter as tk
import logging
from shared import  load_json_cached, characters_bw, tool_items_bw, scenario_items_bw, ALWAYS_ACCESSIBLE_LOCATIONS, COLORS, DATA_DIR, tool_items_c, scenario_items_c, characters
from canvas_config import CITIES, update_character_image
from helpers.item_management import clear_items, item_entries, create_item_entry
from logic import LocationLogic
import os
import json
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
import pathlib
from event_handlers import update_tool_image, update_scenario_image
import pyphen


dic = pyphen.Pyphen(lang='en_US')


# This script contains the logic for resetting the app, saving and loading the content


class Reset:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
       
        
        self.locations_logic = load_json_cached(DATA_DIR / "locations_logic.json")
        
    def reset(self):
        """
        Resets the game state, clearing all tracked items and resetting UI elements.
        """
        
        if hasattr(self.app, "timer_ids"):
            for timer in self.app.timer_ids.values():
                self.app.root.after_cancel(timer)
            self.app.timer_ids.clear()

        # Reset all tracking-related checkboxes
        self.app.chars_var.set(False)
        self.app.tools_var.set(False)
        self.app.keys_var.set(False)
        self.app.maidens_var.set(False)
        self.app.position_var.set(False)
        self.app.all_var.set(False)
        
        self.app.obtained_items.clear()
        

        # Clear tool images on the canvas
        for tool_name, tool_info in self.app.tool_images.items():
            bw_image_path = tool_items_bw[tool_name]["image_path"]
            new_image = self.app.load_image_cached(bw_image_path)
            if new_image:
                self.app.tools_canvas.itemconfig(tool_info['position'], image=new_image)
                tool_info['image'] = new_image
        
        # Clear scenario images on the canvas
        for scenario_name, scenario_info in self.app.scenario_images.items():
            bw_image_path = scenario_items_bw[scenario_name]["image_path"]
            new_image = self.app.load_image_cached(bw_image_path)
            if new_image:
                self.app.scenario_canvas.itemconfig(scenario_info['position'], image=new_image)
                scenario_info['image'] = new_image

        # Clear character images
        
        for character_name in list(self.app.character_images.keys()):
            bw_image_path = characters_bw[character_name]["image_path"]
          
            update_character_image(self.app.characters_canvas, self.app, character_name, bw_image_path)
            
           
            from gui_setup import remove_character_location
            remove_character_location(self.app, character_name)
            
        # Clear the maidens on the canvas
        if hasattr(self.app, 'maiden_images') and hasattr(self.app, 'maidens_canvas'):
            for maiden_name, maiden_info in self.app.maiden_images.items():
                bw_image_path = characters_bw.get(maiden_name, {}).get("image_path")
                if bw_image_path:
                    new_image = self.app.load_image_cached(bw_image_path)
                    if new_image:
                        self.app.maidens_canvas.itemconfig(maiden_info['position'], image=new_image)
                        maiden_info['current_image'] = new_image
                        
        # Clear item / spells on the canvas
        
        clear_items(self.app.item_canvas) # Rufe die Funktion zum Leeren auf!

        self.app.item_canvas.configure(scrollregion=self.app.item_canvas.bbox("all"))
        
        # Clear hints
        self.app.hints_canvas.delete("1.0", tk.END)
        self.app.hints_canvas.configure(font=("Helvetica", 12))
        
        
        # Clear map to default
        self.app.location_logic.update_accessible_locations(self.app.obtained_items)
        for location, dot in self.app.location_labels.items():
            if dot:
                if location in ALWAYS_ACCESSIBLE_LOCATIONS:
                    dot_color = COLORS['accessible']
                elif location in CITIES and location in {"Chaed", "Narvick", "Preamarl"}: # Direkte Prüfung
                    dot_color = COLORS['not_accessible'] # explizit rot
                elif location in CITIES:
                    dot_color = COLORS['city'] # Default für andere Städte
                else:
                    dot_color = COLORS['not_accessible'] # Default für normale Orte
                self.app.canvas.itemconfig(dot, fill=dot_color)
                
        
        # Clear player position 
        self.app.position_scanner.canvas.delete('player_dot')  # Entfernt alle Elemente mit dem Tag 'player_dot'
        
    
                
class Save():
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
        
    def get_tools_canvas(self, tools_canvas): # self hinzufügen
        """
        Extracts relevant data from the tools canvas, including the current image path.
        """
        tools_data = []
        for key, info in self.app.tool_images.items():
            if key in self.app.obtained_items:  # Überprüfe, ob das Tool obtained ist
                current_image_path = str(tool_items_c[key]["image_path"])  # Farbige Version
            else:
                current_image_path = str(tool_items_bw[key]["image_path"])  # Schwarz-weiße Version

            tools_data.append({
                "type": "tool",
                "name": key,
                "obtained": key in self.app.obtained_items,
                "current_image_path": current_image_path,
                "position": info["position"]
            })
        return tools_data 
    
    def get_scenario_canvas(self, scenario_canvas): # self hinzufügen
        """
        Extracts relevant data from the scenario canvas, including the current image path.
        """
        scenario_data = []
        for key, info in self.app.scenario_images.items():
            if key in self.app.obtained_items:  # Überprüfe, ob das scenario obtained ist
                current_image_path = str(scenario_items_c[key]["image_path"])  # Farbige Version
            else:
                current_image_path = str(scenario_items_bw[key]["image_path"])  # Schwarz-weiße Version

            scenario_data.append({
                "type": "scenario",
                "name": key,
                "obtained": key in self.app.obtained_items,
                "current_image_path": current_image_path,
                "position": info["position"]
            })
        return scenario_data 
    
    def get_character_data(self, characters_canvas):
        character_data = []
        saved_characters = set()  # Menge, um bereits gespeicherte Charaktere zu verfolgen

        for name, info in self.app.character_images.items():
            if info["is_colored"]:  # Nur "obtained" Charaktere speichern
                image_path = info.get("image_path")
                if image_path:
                    relative_path = str(image_path)  # Relativer Pfad
                    
                    # Prüfen, ob eine Location-Zuordnung vorhanden ist
                location_data = None
                for location, data in self.app.location_character_images.items():
                    if data["character"] == name:
                        location_data = data
                        break  # Schleife verlassen, sobald Location-Daten gefunden wurden

                if location_data:  # Wenn Location-Zuordnung vorhanden ist, diese Daten speichern
                    character_data.append({
                        "type": "location_assignment",
                        "name": name,
                        "image_path": relative_path,
                        "mini_image_coords": location_data["coords"],
                        "location": location,  # Verwende die tatsächliche location Variable
                        "canvas_x": location_data["canvas_x"],
                        "canvas_y": location_data["canvas_y"],
                        "obtained": True,
                        "position": info["position"]
                    })
                else:  # Ansonsten nur die grundlegenden Charakterdaten speichern
                    character_data.append({
                        "type": "character",
                        "name": name,
                        "obtained": True,
                        "image_path": relative_path,
                        "position": info["position"]
                    })

            else:
                pass
                #logging.error(f"Kein gültiges Bild für Charakter {name} gefunden. Speichern übersprungen.")
        return character_data
    
    def get_maiden_data(self, maidens_canvas):
        maiden_data = []
        
        for name, info in self.app.maiden_images.items():   
            if info["is_colored"]:  # Nur "obtained" Charaktere speichern
                image_path = info.get("image_path")
                if image_path:
                    relative_path = str(image_path)  # Relativer Pfad
                    maiden_data.append({
                            "type": "maiden",
                            "name": name,
                            "obtained": True,
                            "image_path": relative_path,
                            "position": info["position"]
                        })       
                        
            else:
                logging.error(f"Kein gültiges Bild für Maiden {name} gefunden. Speichern übersprungen.")
        
        return maiden_data
    
    def get_item_data(self, item_canvas):
        item_data = []
        for text_id, button_id, y, entry_height, item_name, location in item_entries:
            item_data.append({
                "location": location,
                "item_name": item_name
            })
            
        return item_data
    
    def get_hint_data(self, hints_canvas):
        hint_data = hints_canvas.get("1.0", tk.END).strip()  # .strip() entfernt Leerzeichen am Anfang und Ende
        return hint_data
    
    def get_map_data(self):
        map_data = []
        for location, dot in self.app.location_labels.items():
            if dot:
                dot_color = self.app.canvas.itemcget(dot, "fill")
                map_data.append({
                    "location": location,
                    "color": dot_color
                })
        return map_data

    # Is used to save the current state      
    def get_all_canvas_data(self):
        """Sammelt Daten von allen Canvas."""
        all_data = {
            "tools_canvas": self.get_tools_canvas(self.app.tools_canvas),
            "scenario_canvas": self.get_scenario_canvas(self.app.scenario_canvas),
            "characters_canvas": self.get_character_data(self.app.characters_canvas),
            "maidens_canvas": self.get_maiden_data(self.app.maidens_canvas),
            "item_canvas": self.get_item_data(self.app.item_canvas),
            "hint_canvas": self.get_hint_data(self.app.hints_canvas),
            "map_canvas": self.get_map_data()
        }
        
        return all_data     
    
    def save_game_state(self):
        self.logger.info("Saving game...")
        
        """Saves the game state using pickle (only tool data)."""
        try:
            saves_path = os.path.abspath("saves")
            # Open file dialog for saving
            filepath = filedialog.asksaveasfilename(initialdir=saves_path, defaultextension=".json", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])

            if filepath:  # Check if the user selected a path
                game_state = {
                    **self.get_all_canvas_data(),
                }
                with open(filepath, "w" , encoding="utf-8") as f:
                    json.dump(game_state, f, indent=4)
                logging.info(f"Game state saved to {filepath}.")
                self.app.root.title(f"Lufia 2 Tracker - {filepath}") #update window title
            else:
                logging.info("Saving cancelled.")

        except Exception as e:
            logging.error(f"Error during saving: {e}")
            
            
class Load():
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
        
    
        
    def set_tools_canvas(self, tools_data):
        """Setzt den Inhalt des tools_canvas anhand der geladenen Daten."""
        for item in tools_data:
            tool_name = item["name"]

            
            if tool_name in self.app.obtained_items and self.app.obtained_items[tool_name]:
                update_tool_image(self.app, tool_name, obtained=True)
            else:
                update_tool_image(self.app, tool_name, obtained=False)

            if tool_name in self.app.tool_images:
                tool_data = self.app.tool_images[tool_name]
                self.app.tools_canvas.tag_bind(tool_data['position'], "<Button-1>", lambda event, tool=tool_name: self.app.on_tool_click(tool))
            else:
                logging.warning(f"Tool {tool_name} from save not found in current tool list.")
            
    def set_scenario_canvas(self, scenario_data, item_to_location):
        """Setzt den Inhalt des tools_canvas anhand der geladenen Daten."""

        for item in scenario_data:
            key = item["name"]
        

            if key in self.app.obtained_items and self.app.obtained_items[key]:
                update_scenario_image(self.app, key, obtained=True)
            else:
                update_scenario_image(self.app, key, obtained=False)

            if key in self.app.scenario_images:
                scenario_data = self.app.scenario_images[key]
                self.app.scenario_canvas.tag_bind(scenario_data["position"], "<Button-1>", lambda event, scenario=key: self.app.on_scenario_click(scenario))
            else:
                logging.warning(f"Tool {key} from save not found in current tool list.")
    
    def set_characters_canvas(self, character_data):
        """Setzt den Inhalt des characters_canvas anhand der geladenen Daten."""
        
        self.app.location_character_images = {}  # Initialisiere location_character_images
        
        for character in character_data:
            name = character["name"]
            obtained = character["obtained"]
            
            if name in self.app.character_images:
                
                if obtained is not None:
                    self.app.character_images[name]["is_colored"] = obtained
                    if obtained: #Wenn obtained True ist, color_image verwenden
                        new_image_path = self.app.character_images[name]["image_path"].replace("bw", "") #bw aus dem Pfad entfernen
                    else: #Ansonsten bw_image verwenden
                        new_image_path = self.app.character_images[name]["image_path"]
                
                    update_character_image(self.app.characters_canvas, self.app, name, new_image_path) #Korrekter Aufruf mit new_image_path
                
            else:
                logging.error(f"FEHLER: Charakter {name} NICHT im character_images gefunden!")
            
        # 2. Charaktere mit Location auf dem Map-Canvas setzen
        for character in character_data:
            if character["type"] == "location_assignment":
                name = character["name"]
                location = character["location"]
                mini_image_coords = character["mini_image_coords"]
                obtained = character.get("obtained")
                text_x = character["canvas_x"]
                text_y = character["canvas_y"]
               
                                                
                if name in self.app.character_images and obtained is not None:
                    if obtained:
                        character_image_path = self.app.character_images[name]["image_path"].replace("bw", "")
                    else:
                        character_image_path = self.app.character_images[name]["image_path"]
                    try:
                        character_image = Image.open(character_image_path)
                        image_width = 30
                        image_height = 30
                        desired_size =(image_width, image_height)
                        character_image_small = character_image.resize(desired_size)
                        character_image_small = ImageTk.PhotoImage(character_image_small)
                        image_id = self.app.canvas.create_image(mini_image_coords[0], mini_image_coords[1], anchor=tk.NW, image=character_image_small, tags=("location_image", f"location_image_{location}"))
                        self.app.character_images[name]["image_id"] = image_id
                        self.app.canvas.images.append(character_image_small)
                        
                        #location_character_images befüllen
                        if location not in self.app.location_character_images:
                            self.app.location_character_images[location] = {}
                        self.app.location_character_images[location]["character"] = name
                        self.app.location_character_images[location]["image_id"] = image_id

                        
                        if obtained and location: #Stelle sicher, dass die Koordinaten und die Location vorhanden sind
                            max_line_length = 9
                            words = location.split()
                            lines = []
                            for word in words:
                                if len(word) > max_line_length and len(word) > 3:
                                    hyphenated_word = dic.inserted(word)
                                    parts = hyphenated_word.split("-")
                                    for part in parts[:-1]:
                                        lines.append(part + "-")
                                    lines.append(parts[-1])
                                else:
                                    lines.append(word)

                            location_text = "\n".join(lines)
                            x_offset = text_x
                            y_offset = text_y

                            text_id = self.app.characters_canvas.create_text(
                                x_offset, y_offset,
                                text=location_text,
                                fill="white",
                                anchor="nw",
                                tags=(f"location_text_{name}", "location_text")
                            )
                            self.app.characters_canvas.tag_raise(text_id)
                            self.app.character_images[name]["text_id"] = text_id
                            
                        else:
                            logging.error("mini_image_coords oder location sind nicht vorhanden")
                        
                    
                    except FileNotFoundError:
                        logging.error(f"Bilddatei für {name} nicht gefunden: {character_image_path}")
                    except Exception as e:
                        logging.error(f"Fehler beim Laden des Location-Bildes für {name}: {e}")
                        import traceback
                        traceback.print_exc()

                else:
                    logging.warning(f"Charakterinformationen für {name} nicht gefunden oder obtained ist None.")

    
    def set_maidens_canvas(self, maiden_data):
        """Setzt den Inhalt des maidens_canvas anhand der geladenen Daten."""

        for maiden in maiden_data:
            name = maiden["name"]
            obtained = maiden["obtained"]

            if name in self.app.maiden_images:
                if obtained is not None:
                    self.app.maiden_images[name]["is_colored"] = obtained

                    maiden_info = self.app.maiden_images[name] #Referenz auf das Dictionary.

                    if obtained:
                        new_image = maiden_info["color_image"]  # Direktes Zugreifen auf das color_image Objekt
                    else:
                        new_image = maiden_info["bw_image"]  # Direktes Zugreifen auf das bw_image Objekt

                    self.app.maidens_canvas.itemconfig(maiden_info["position"], image=new_image)  # Canvas-Element direkt aktualisieren
                    maiden_info['current_image'] = new_image # current_image aktualisieren

                else:
                    logging.error(f"Obtained ist None für {name}")
            else:
                logging.error(f"FEHLER: Charakter {name} NICHT im maiden_images gefunden!")
    
    def set_item_canvas(self, item_data):
        """Setzt den Inhalt des item_canvas anhand der geladenen Daten."""
        for item in item_data:
            location = item["location"]
            item_name = item["item_name"]
            create_item_entry(self.app.item_canvas, location, item_name)  # create_item_entry verwenden!

        self.app.item_canvas.configure(scrollregion=self.app.item_canvas.bbox("all"))  # Scrollregion anpassen
        self.app.item_canvas.yview_moveto(0) #Nach dem Laden zum Anfang der Liste scrollen
    
    def set_hints_canvas(self, hint_data):
        """Setzt den Inhalt des hint_canvas anhand der geladenen Daten."""
        self.app.hints_canvas.insert(tk.END, hint_data)  # Füge den geladenen Text ein
    
    def set_map_canvas(self, map_data):
        """Setzt den Inhalt des map_canvas anhand der geladenen Daten."""
        for item in map_data:
            location = item["location"]
            dot = self.app.location_labels.get(location)
            if dot:
                self.app.canvas.itemconfig(dot, fill=item["color"])
                
    
    def dispatch_all_canvas_data(self, canvas_data):
            """Verteilt die Canvas-Daten und befüllt obtained_items KORREKT."""
            self.app.obtained_items = {}  # Initialisiere obtained_items

            if "tools_canvas" in canvas_data:
                for tool in canvas_data["tools_canvas"]:
                    if "name" in tool and "obtained" in tool and tool["obtained"]:
                        self.app.obtained_items[tool["name"]] = True
                    
                self.set_tools_canvas(canvas_data["tools_canvas"])
                

            if "scenario_canvas" in canvas_data:
                for scenario in canvas_data["scenario_canvas"]:
                    if "name" in scenario and "obtained" in scenario and scenario["obtained"]: # KORREKTE PRÜFUNG!
                        self.app.obtained_items[scenario["name"]] = True # explizit True setzen

                self.set_scenario_canvas(canvas_data["scenario_canvas"], self.app.item_to_location)
            
            if "characters_canvas" in canvas_data:
                for character in canvas_data["characters_canvas"]:
                    if "name"in character and "obtained" in character and character["obtained"]:
                        self.app.obtained_items[character["name"]] = True
                
                self.set_characters_canvas(canvas_data["characters_canvas"]) #set_characters_canvas aufrufen   

            if "maidens_canvas" in canvas_data:
                for maiden in canvas_data["maidens_canvas"]:
                    if "name" in maiden and "obtained" in maiden and maiden["obtained"]:
                        self.app.obtained_items[maiden["name"]] = True
                
                self.set_maidens_canvas(canvas_data["maidens_canvas"])
                
            if "item_canvas" in canvas_data:
                self.set_item_canvas(canvas_data["item_canvas"])
                
            if "hint_canvas" in canvas_data:    
                self.set_hints_canvas(canvas_data["hint_canvas"])
                
            if "map_canvas" in canvas_data:
                self.set_map_canvas(canvas_data["map_canvas"])
            
    def load_game_state(self):
        self.logger.info("Loading game...")
        # Reset the game state before loading a new one in main.py
        Reset(self.app).reset()
        
        try:
            saves_path = os.path.abspath("saves")
            filepath = filedialog.askopenfilename(initialdir=saves_path, defaultextension=".json", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])

            if filepath:
                
                with open(filepath, "r", encoding="utf-8") as f:
                    game_state = json.load(f)
                    
                self.dispatch_all_canvas_data(game_state)
                
                self.app.obtained_items = {}
                
                for tool in game_state.get("tools_canvas", []): # Sicherstellen, dass tools_canvas existiert
                    if tool.get("obtained"): # Nur wenn "obtained" True ist
                        self.app.obtained_items[tool["name"]] = True
               
                
                for key in game_state.get("scenario_canvas", []): # Sicherstellen, dass scenario_canvas existiert
                    if key.get("obtained"):
                        self.app.obtained_items[key["name"]] = True
                
                self.app.location_logic.update_accessible_locations(self.app.obtained_items)
                
                self.app.handle_manual_input()
                    
                for data in game_state.get("characters_canvas", []):

                    if data["type"] == "location_assignment":

                        name = data["name"]

                        location = data["location"]


                        for char_name, char_data in self.app.character_images.items():

                            for data in game_state.get("characters_canvas", []):

                                if data.get("type") == "location_assignment":

                                    if data.get("name") == char_name:  # Korrekter Vergleich: Charaktername

                                        if "image_id" in char_data:

                                            from gui_setup import make_draggable, assign_character_to_location, remove_character_location

                                            make_draggable(self.app.canvas, char_data["image_id"])
                                            
                                            self.app.characters_canvas.tag_bind(
                                                char_data['position'],
                                                "<Button-3>",
                                                lambda event, loc_images=self.app.location_character_images: (
                                                    remove_character_location(self.app, name)
                                                )
                                            )
                                            break

                        logging.info(f"Game state loaded from {filepath}.")               

            else:

                logging.info("Loading cancelled.")


        except FileNotFoundError:

            logging.error("Save file not found.")

        except json.JSONDecodeError:

            logging.error("Invalid save file format.")

        except Exception as e:

            logging.error(f"Error during loading: {e}")

            import traceback

            traceback.print_exc() 
            
class SoftReset():
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
       
        
        self.locations_logic = load_json_cached(DATA_DIR / "locations_logic.json")
        
    def reset_tools(self):
        """
        Resets the game state, clearing all tracked items and resetting UI elements.
        """
            
        self.app.obtained_items.clear()
            

        # Clear tool images on the canvas
        for tool_name, tool_info in self.app.tool_images.items():
            bw_image_path = tool_items_bw[tool_name]["image_path"]
            new_image = self.app.load_image_cached(bw_image_path)
            if new_image:
                self.app.tools_canvas.itemconfig(tool_info['position'], image=new_image)
                tool_info['image'] = new_image
            
    def reset_scenario(self):
        self.app.obtained_items.clear()
        # Clear scenario images on the canvas
        for scenario_name, scenario_info in self.app.scenario_images.items():
            bw_image_path = scenario_items_bw[scenario_name]["image_path"]
            new_image = self.app.load_image_cached(bw_image_path)
            if new_image:
                self.app.scenario_canvas.itemconfig(scenario_info['position'], image=new_image)
                scenario_info['image'] = new_image

    def reset_characters(self):
        # Clear character images
        
        for character_name in list(self.app.character_images.keys()):
            bw_image_path = characters_bw[character_name]["image_path"]
            
            update_character_image(self.app.characters_canvas, self.app, character_name, bw_image_path)
           
            from gui_setup import remove_character_location
            remove_character_location(self.app, character_name)
        
    def reset_maidens(self):
        # Clear the maidens on the canvas
        if hasattr(self.app, 'maiden_images') and hasattr(self.app, 'maidens_canvas'):
            for maiden_name, maiden_info in self.app.maiden_images.items():
                bw_image_path = characters_bw.get(maiden_name, {}).get("image_path")
                if bw_image_path:
                    new_image = self.app.load_image_cached(bw_image_path)
                    if new_image:
                        self.app.maidens_canvas.itemconfig(maiden_info['position'], image=new_image)
                        maiden_info['current_image'] = new_image
                            
    def reset_map(self):
        # Clear map to default
        self.app.location_logic.update_accessible_locations(self.app.obtained_items)
        for location, dot in self.app.location_labels.items():
            if dot:
                if location in ALWAYS_ACCESSIBLE_LOCATIONS:
                    dot_color = COLORS['accessible']
                elif location in CITIES and location in {"Chaed", "Narvick", "Preamarl"}: # Direkte Prüfung
                    dot_color = COLORS['not_accessible'] # explizit rot
                elif location in CITIES:
                    dot_color = COLORS['city'] # Default für andere Städte
                else:
                    dot_color = COLORS['not_accessible'] # Default für normale Orte
                self.app.canvas.itemconfig(dot, fill=dot_color)
                
    def reset_position(self):
        self.app.position_scanner.canvas.delete('player_dot')  # Entfernt alle Elemente mit dem Tag 'player_dot'
        