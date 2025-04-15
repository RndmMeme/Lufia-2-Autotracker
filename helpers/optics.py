# optics.py

import tkinter as tk


# optics.py
import tkinter as tk

class Banner(tk.Toplevel):
    def __init__(self, master=None, message="Sync Successful", bg_color="#D3D3D3", duration=2000, x_offset=10, y_offset=10, **kwargs):
        tk.Toplevel.__init__(self, master, **kwargs)
        self.message = message
        self.duration = duration
        self.master = master  # Speichere Referenz zum Hauptfenster

        self.overrideredirect(True)  # Fenster ohne Rahmen
        self.attributes('-alpha', 0.4)  # Weniger durchsichtig für bessere Lesbarkeit

        label = tk.Label(self, text=message, bg=bg_color, padx=10, pady=3, font=("Arial", 9))
        label.pack()

        # Berechne Position relativ zum Hauptfenster
        x = master.winfo_x() + x_offset
        y = master.winfo_y() + y_offset
        self.geometry(f"+{x}+{y}")

        self.after(duration, self.destroy)  # Destroy after duration