# This script handles the logic for adding and removing entries to "items / spells"

import tkinter as tk
from tkinter import ttk, filedialog, Label, messagebox
import os
import json
import logging
from PIL import Image, ImageTk
import tkinter.font as tkFont
from shared import CITIES, item_spells, LOCATIONS



item_entries = []  # Globale Liste zur Speicherung der Einträge
highlighted_item = None #Speichert das aktuell hervorgehobene Item


def add_sort_buttons(root, item_canvas):
    """Fügt Sortierbuttons auf dem Label rechts neben dem Text hinzu (korrigiert)."""
    items_label = None
    for widget in root.winfo_children():
        if isinstance(widget, tk.Label) and widget.cget("text") == "Items/Spells:":
            items_label = widget
            break

    if items_label:
        label_x = items_label.winfo_x() + 111  # X-Koordinate rechts neben dem Text (anpassbar)
        label_y = items_label.winfo_y() + 25  # Y-Koordinate des Labels (angepasst)

        sort_location_button = tk.Button(root, text="Sort by Location", command=lambda: sort_by_location(item_canvas), bg="black", fg="white", font=("Arial", 8))
        sort_location_button.place(x=label_x, y=label_y)

        sort_item_button = tk.Button(root, text="Sort by Item", command=lambda: sort_by_item_name(item_canvas), bg="black", fg="white", font=("Arial", 8))
        sort_item_button.place(x=label_x + 88, y=label_y)  # Abstand zwischen den Buttons
    
        clear_button = tk.Button(root, text="Clear", command=lambda: clear_canvas(item_canvas), bg="black", fg="white", font=("Arial", 8))
        clear_button.place(x=label_x + 154, y=label_y)  # Positioniere den Clear-Button
    else:
        logging.error("Label 'Items/Spells:' not found.")
    
def clear_canvas(item_canvas):
    """Leert den Canvas und die item_entries-Liste."""
    global item_entries
    global highlighted_item

    item_canvas.delete("location_text")  # Lösche nur Einträge mit dem Tag "location_text"
    item_canvas.delete("item_button")  # Lösche alle Buttons

    item_entries = []  # Leere die Liste
    highlighted_item = None  # Setze highlighted_item zurück

    item_canvas.configure(scrollregion=item_canvas.bbox("all"))  # Scrollregion anpassen    

def sort_by_location(item_canvas):
    """Sortiert die Einträge nach Stadt."""
    global item_entries
    item_entries.sort(key=lambda entry: entry[5])  # Sortiere nach dem 6. Element (location)
    reposition_entries(item_canvas)

def sort_by_item_name(item_canvas):
    """Sortiert die Einträge nach Zauber/Item-Name."""
    global item_entries
    item_entries.sort(key=lambda entry: entry[4])  # Sortiere nach dem 5. Element (item_name)
    reposition_entries(item_canvas)

def create_item_entry(canvas, location, item_name):
    """Erstellt einen Eintrag im Canvas und speichert ihn in der Liste."""
    bbox = canvas.bbox("all")
    y = bbox[3] + 5 if bbox else 30

    text = f"{location}: {item_name}"
    text_id = canvas.create_text(10, y, anchor='nw', text=text, fill="white", font=('Arial', 12), tags=("location_text", item_name))
    button_id = canvas.create_text(260, y, anchor='nw', text="x", fill="white", font=('Arial', 12, 'bold'), tags=(f"button_for_{text_id}", "item_button"))

    text_bbox = canvas.bbox(text_id)
    entry_height = text_bbox[3] - text_bbox[1] if text_bbox else 15

    item_entries.append((text_id, button_id, y, entry_height, item_name, location))

    canvas.tag_bind(button_id, "<Button-1>", lambda event, tid=text_id, bid=button_id: remove_entry(canvas, tid, bid))
    canvas.tag_bind(button_id, "<Enter>", lambda event, tid=text_id, bid=button_id: highlight_row(canvas, tid, bid))  # Mouseover für "x"
    canvas.tag_bind(button_id, "<Leave>", lambda event, tid=text_id, bid=button_id: clear_row_highlight(canvas, tid, bid))  # Mouseout für "x"

    return text_id, button_id

def find_duplicate_by_name(canvas, item_name, exclude_current=None):
    """Findet einen Eintrag anhand des item_name (mit optionalem Ausschluss)."""
    for entry in item_entries:
        text_id = entry[0]
        if text_id != exclude_current and entry[4] == item_name:
            return entry
    return None

def highlight_and_scroll(canvas, entry, permanent=False):
    """Hebt einen Eintrag hervor und scrollt zu ihm (nur Textfarbe)."""
    global highlighted_item
    text_id, _, y, entry_height, _, _ = entry

    # Vorheriges Highlight entfernen
    clear_highlight(canvas)

    canvas.itemconfig(text_id, fill="yellow", font=('Arial', 13, 'bold')) # Nur Textfarbe und Fett
    highlighted_item = entry

    all_bbox = canvas.bbox("all")
    if all_bbox:
        canvas_height = canvas.winfo_height()
        if y < canvas.yview()[0] * all_bbox[3] or y + entry_height > (canvas.yview()[0] + canvas_height/all_bbox[3]) * all_bbox[3]:
            canvas.yview_moveto(y / all_bbox[3])
    if not permanent:
        canvas.after(5000, lambda tid=text_id: clear_highlight(canvas))
        
def highlight_row(canvas, text_id, button_id):
    """Hebt die gesamte Zeile hervor."""
    canvas.itemconfig(text_id, fill="red", font=('Arial', 13, 'bold')) #Text hervorheben
    canvas.itemconfig(button_id, fill="red") #Button hervorheben

def clear_row_highlight(canvas, text_id, button_id):
    """Entfernt die Hervorhebung der gesamten Zeile."""
    canvas.itemconfig(text_id, fill="white", font=('Arial', 12)) #Text zurücksetzen
    canvas.itemconfig(button_id, fill="white") #Button zurücksetzen
            
def handle_mouse_enter(canvas, item_name):
    """Behandelt den Mouseover-Event."""
    duplicate_entry = find_duplicate_by_name(canvas, item_name)
    if duplicate_entry:
        highlight_and_scroll(canvas, duplicate_entry)

def clear_highlight(canvas):
    """Entfernt alle Hervorhebungen."""
    global highlighted_item
    if highlighted_item:
        text_id = highlighted_item[0]
        canvas.itemconfig(text_id, fill="white", font=('Arial', 12)) # Zurücksetzen auf ursprüngliche Farbe und Schrift
        highlighted_item = None
        
def remove_entry(canvas, text_id, button_id):
    """Entfernt einen Eintrag aus dem Canvas und der Liste."""
    canvas.delete(text_id)
    canvas.delete(button_id)

    # Korrigierte Schleife: Entpacke alle 6 Werte, aber verwende nur die benötigten
    item_entries[:] = [entry for entry in item_entries if entry[0] != text_id]

    reposition_entries(canvas) #Positionen neu berechnen
    canvas.configure(scrollregion=canvas.bbox("all"))

def reposition_entries(canvas):
    """Positioniert die Einträge im Canvas neu."""
    y = 30 #Startposition
    for text_id, button_id, _, entry_height, _, _ in item_entries: # _ für nicht verwendete Werte
        canvas.coords(text_id, 10, y)
        canvas.coords(button_id, 260, y)
        y += entry_height + 5 # Abstand zwischen den Einträgen
        
def search_item_window(parent, location, app):
    """Opens a search window for items/spells with autofokus and multi selection."""
    search_window = tk.Toplevel(parent)
    search_window.title(f"Search {location}")
    
    # Suchfenster im Vordergrund halten
    search_window.attributes('-topmost', True)  # Diese Zeile wurde hinzugefügt
    search_window.grab_set()  # Diese Zeile wurde hinzugefügt
    
    available_categories = list(app.item_spells.keys())
    
    def change_category(category):
        category_var.set(category)
        update_suggestions()  # Vorschläge aktualisieren

    # Frame für die Buttons erstellen
    button_frame = tk.Frame(search_window)  # Wir erstellen einen Frame, um die Buttons zu gruppieren
    button_frame.pack()  # Der Frame wird oben im Fenster platziert

    # Buttons für die Kategorieauswahl erstellen und in den Frame packen
    for category in available_categories:
        button = tk.Button(button_frame, text=category, command=lambda c=category: change_category(c))
        button.pack(side=tk.LEFT)  # Buttons nebeneinander im Frame anordnen

    category_var = tk.StringVar(search_window)
    category_var.set(available_categories[0])  # Standardmäßig die erste Kategorie auswählen

    entry_field = ttk.Entry(search_window, width=30)
    entry_field.pack()
    search_window.after(1, entry_field.focus_set) #Verzögerung von 1 Millisekunde
    
    suggestions_listbox = tk.Listbox(search_window, selectmode=tk.EXTENDED) #Mehrfachauswahl aktivieren
    suggestions_listbox.pack()
    
    selected_items_in_search = set()  # Menge der aktuell ausgewählten Items im Suchfenster
    selected_index = 0  # Index des aktuell ausgewählten Elements in der Listbox

    def update_suggestions(event=None):
        nonlocal selected_index  # Zugriff auf die äußere Variable
        input_text = entry_field.get().lower()
        selected_category = category_var.get()
        suggestions_listbox.delete(0, tk.END)
        best_match_index = None
        best_match_length = float('inf')

        for i, item in enumerate(app.item_spells[selected_category]):
            if input_text in item['name'].lower():
                suggestions_listbox.insert(tk.END, item['name'])

                if item['name'].lower().startswith(input_text):
                    match_length = len(item['name'])
                    if match_length < best_match_length:
                        best_match_length = match_length
                        best_match_index = i

        if suggestions_listbox.size() > 0:
            if best_match_index is not None:
                selected_index = best_match_index
            else:
                selected_index = 0
            suggestions_listbox.select_clear(0, tk.END)
            suggestions_listbox.select_set(selected_index)
            suggestions_listbox.activate(selected_index)
        else:
            selected_index = -1

        suggestions_listbox.update_idletasks() # WICHTIG: Aktualisierung erzwingen

    entry_field.bind("<KeyRelease>", update_suggestions)
    update_suggestions()

    def items_selected(event=None):
        selected_indices = suggestions_listbox.curselection()
        if selected_indices:
            selected_items = [suggestions_listbox.get(i) for i in selected_indices]
            for selected_item_name in selected_items:
                duplicate_entry = find_duplicate_by_name(app.item_canvas, selected_item_name)
                if duplicate_entry:
                    highlight_and_scroll(app.item_canvas, duplicate_entry, permanent=True)
                else:
                    store_shop_item(app, location, selected_item_name, category.lower())
    
    def navigate_suggestions(event):
        nonlocal selected_index
        if suggestions_listbox.size() > 0:  # Nur wenn Elemente in der Listbox sind
            if event.delta < 0: # Mousewheel runter
                selected_index = (selected_index + 1) % suggestions_listbox.size()
            elif event.delta > 0: # Mousewheel hoch
                selected_index = (selected_index - 1) % suggestions_listbox.size()
            suggestions_listbox.select_clear(0, tk.END)
            suggestions_listbox.select_set(selected_index)
            suggestions_listbox.activate(selected_index)
            return "break"  # Verhindere Standardverhalten

    
    parent.bind_all("<Button-2>", items_selected)  # Mittlere Maustaste
    
    #Mouse-over im Suchfenster
    def handle_search_mouseover(event):
        item_name = suggestions_listbox.get(suggestions_listbox.nearest(event.y))
        duplicate_entry = find_duplicate_by_name(app.item_canvas, item_name)
        if duplicate_entry:
            highlight_and_scroll(app.item_canvas, duplicate_entry)

    suggestions_listbox.bind("<Motion>", handle_search_mouseover)

    suggestions_listbox.bind("<Double-Button-1>", items_selected)
    suggestions_listbox.bind("<Return>", items_selected)
    #Hinzugefügt: Auswahl mit Enter-Taste
    entry_field.bind("<Return>", items_selected)

    # Fokus auf das Fenster, damit Maus-Klicks außerhalb erkannt werden
    search_window.focus_set()
    parent.bind_all("<MouseWheel>", navigate_suggestions)
    
    def close_window(event):
        if event.keysym == "Escape":  # Überprüfen, ob es die Escape-Taste ist
            search_window.destroy()
        elif event.widget != search_window and not isinstance(event.widget, tk.Toplevel) and event.widget != entry_field and event.widget != suggestions_listbox: # Ansonsten die alte Funktion
            search_window.destroy()
    parent.bind("<Button-1>", close_window)
    search_window.bind("<Escape>", close_window)  # Diese Zeile wurde hinzugefügt
    search_window.bind("<FocusOut>", close_window)

def load_items_and_cache():
    """Loads items/spells from the JSON file and caches them for faster lookup."""
    try:
        # Konvertiere das Dictionary in eine Liste von Dictionaries
        processed_items = {}
        for category, items in item_spells.items():
            processed_items[category] = [{"name": name} for name in items.values()] # Nur die Namen
        return processed_items
    except Exception as e: # Fange alle Exceptions
        logging.error(f"Error loading items: {e}")
        return {}
    
def store_shop_item(app, location, item_names, category):
    canvas = app.item_canvas if category in ["weapon", "armor", "iris treasures", "spell"] else None
    if canvas:
        if isinstance(item_names, list):
            for item_name in item_names:
                create_item_entry(canvas, location, item_name)
        else:
            create_item_entry(canvas, location, item_names)
        canvas.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        canvas.yview_moveto(1.0)
        
def clear_items(canvas):
    """Leert den Canvas und die item_entries-Liste."""
    global item_entries
    global highlighted_item

    canvas.delete("location_text") #Lösche nur Einträge mit dem Tag "location_text"
    canvas.delete("item_button") #Lösche alle Buttons

    item_entries = [] #Leere die Liste
    highlighted_item = None #Setze highlighted_item zurück

    canvas.configure(scrollregion=canvas.bbox("all")) #Scrollregion anpassen