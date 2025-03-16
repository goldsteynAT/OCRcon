import threading
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sys
import os
from ocr_processing import batch_ocr_pdfs
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk

# Redirect stdout to a Text widget
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, s):
        self.text_widget.insert(tk.END, s)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class OCRGUI(TkinterDnD.Tk):
    def __init__(self):
        # Verwende TkinterDnD.Tk als Basisklasse für Drag & Drop
        TkinterDnD.Tk.__init__(self)
        style = ttk.Style(theme='flatly')
        self.title("OCRcon - Control. Connect. Consertis.")
        self.geometry("800x800")
        self.input_folders = []  # Liste der hinzugefügten Root-Ordner

        # Einheitliche Button-Schriftart setzen
        style.configure('TButton', font=('Segoe UI Emoji', 10))

        # Relativer Pfad zum Logo (ausgehend vom Git-Hauptordner)
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logo_path = os.path.join(script_dir, "image.png")

        # Logo-Frame für die zentrale Positionierung
        self.logo_frame = ttk.Frame(self)
        self.logo_frame.pack(fill="x", pady=10)  # Volle Breite für zentrierte Platzierung

        # Bild laden und prozentual skalieren
        image = Image.open(logo_path)
        original_width, original_height = image.size  # Originalgröße holen

        scale_factor = 0.3  # Skalierungsfaktor (30% der Originalgröße)
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)

        image = image.resize((new_width, new_height), Image.LANCZOS)  # Proportionale Skalierung
        self.logo_image = ImageTk.PhotoImage(image)

        # Label für das Logo zentriert platzieren
        self.logo_label = ttk.Label(self.logo_frame, image=self.logo_image)
        self.logo_label.pack(anchor="center")  # Mittig ausrichten

        # Übergeordneter Frame für Quell- und Zielordner
        self.folder_frame = ttk.Frame(self, borderwidth=1, relief="solid")
        self.folder_frame.pack(fill=tk.X, padx=10, pady=10)

        # Input Folder Frame (mit Label, Treeview und Buttons)
        self.input_frame = ttk.Frame(self.folder_frame)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.input_label_desc = ttk.Label(self.input_frame, text="📂 Input Folders:", font=("Segoe UI Emoji", 12), anchor="w")
        self.input_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))

        # Treeview für hierarchische Ordnerstruktur
        self.input_tree_frame = ttk.Frame(self.input_frame)
        self.input_tree_frame.pack(fill=tk.BOTH, padx=5, pady=(5, 0))

        self.input_tree = ttk.Treeview(self.input_tree_frame, show="tree")
        self.input_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.input_tree_scrollbar = ttk.Scrollbar(self.input_tree_frame, orient=tk.VERTICAL, command=self.input_tree.yview)
        self.input_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_tree.config(yscrollcommand=self.input_tree_scrollbar.set)

        # Registriere Treeview als Drop-Ziel
        self.input_tree.drop_target_register(DND_FILES)
        self.input_tree.dnd_bind('<<Drop>>', self.handle_drop)
        # Binde Expand-Ereignis zum Lazy Loading
        self.input_tree.bind("<<TreeviewOpen>>", self.on_treeview_open)

        # Button-Frame für Add/Remove-Buttons, rechtsbündig
        self.input_buttons_frame = ttk.Frame(self.input_frame)
        self.input_buttons_frame.pack(fill=tk.X, padx=5, pady=5, anchor="e")

        self.remove_input_button = ttk.Button(self.input_buttons_frame, text="➖ Remove Folder", command=self.remove_input)
        self.remove_input_button.pack(side=tk.RIGHT, padx=5)

        self.select_input_button = ttk.Button(self.input_buttons_frame, text="➕ Add Folder", command=self.select_input)
        self.select_input_button.pack(side=tk.RIGHT, padx=5)

        # Separator zwischen Input und Output
        self.separator = ttk.Separator(self.folder_frame, orient="horizontal")
        self.separator.pack(fill="x", padx=5, pady=5)

        # Output Folder Frame (mit Label, Entry und Button)
        self.output_frame = ttk.Frame(self.folder_frame)
        self.output_frame.pack(fill=tk.X, padx=5, pady=5)

        self.output_label_desc = ttk.Label(self.output_frame, text="📁 Zielordner:", font=("Segoe UI Emoji", 12), anchor="w")
        self.output_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.output_entry = ttk.Entry(self.output_frame, state="readonly")
        self.output_entry.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.select_output_button = ttk.Button(self.output_frame, text="🔎 Durchsuchen", command=self.select_output)
        self.select_output_button.pack(anchor="e", padx=5, pady=5)

        # --- Steuerungselemente (Start, Pause, Resume) ---
        self.control_frame = ttk.Frame(self, style="TFrame")
        self.control_frame.pack(pady=10)

        self.start_button = ttk.Button(self.control_frame, text="🚀 Start OCR", command=self.start_ocr)
        self.pause_button = ttk.Button(self.control_frame, text="⏸️ Pause", command=self.pause_ocr, state=DISABLED)
        self.resume_button = ttk.Button(self.control_frame, text="🔄 Fortsetzen", command=self.resume_ocr, state=DISABLED)

        self.start_button.pack(side=tk.LEFT, padx=5)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        self.resume_button.pack(side=tk.LEFT, padx=5)

        # Fortschrittsbalken
        self.progress = ttk.Progressbar(self, length=600, mode='determinate')
        self.progress.pack(pady=10)

        # Neue Status Table oberhalb der Logbox
        self.status_table_frame = ttk.Frame(self)
        self.status_table_frame.pack(fill=tk.BOTH, padx=10, pady=(10, 0))
        self.status_table = ttk.Treeview(self.status_table_frame, columns=("Status", "File"), show="headings")
        self.status_table.heading("Status", text="Status")
        self.status_table.heading("File", text="File Path")
        self.status_table.column("Status", width=100)
        self.status_table.column("File", width=600)
        self.status_table.pack(fill=tk.BOTH, expand=True)

        # Log-Ausgabe mit separatem Frame und eigener Scrollbar
        self.log_frame = ttk.Frame(self)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log_scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text.config(yscrollcommand=self.log_scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Umleitung von stdout/stderr auf das Log-Textfeld
        sys.stdout = RedirectText(self.log_text)
        sys.stderr = RedirectText(self.log_text)

        # OCR-Thread und Steuerungsvariablen
        self.ocr_thread = None
        self.running = False
        # Verwende ein threading.Event für Pause/Resume-Steuerung:
        self.resume_event = threading.Event()
        self.resume_event.set()  # Initial set – d.h. nicht pausiert

    def update_status_table(self, completed, current, next_items, current_index, total):
        """Updates the status table with the conversion state."""
        # Clear current rows
        for row in self.status_table.get_children():
            self.status_table.delete(row)
        # Add rows for each category
        for file in completed:
            self.status_table.insert("", tk.END, values=("Completed", file))
        if current:
            self.status_table.insert("", tk.END, values=("In Progress", current))
        for file in next_items:
            self.status_table.insert("", tk.END, values=("Next", file))

    def schedule_update_status(self, completed, current, next_items, current_index, total):
        """Schedules an update of the status table in the main thread."""
        self.after(0, lambda: self.update_status_table(completed, current, next_items, current_index, total))

    def has_subfolder(self, folder):
        """Prüft, ob der Ordner mindestens einen Unterordner enthält."""
        try:
            for entry in os.listdir(folder):
                full_path = os.path.join(folder, entry)
                if os.path.isdir(full_path):
                    return True
            return False
        except Exception:
            return False

    def insert_folder(self, folder):
        """Fügt den Root-Ordner in die Treeview ein und lädt ggf. einen Dummy-Knoten für Lazy Loading."""
        self.input_tree.insert("", "end", iid=folder, text=folder)
        if self.has_subfolder(folder):
            # Dummy-Knoten hinzufügen, um anzuzeigen, dass Unterordner vorhanden sind
            self.input_tree.insert(folder, "end", text="dummy")

    def handle_drop(self, event):
        """Verarbeitet Drag & Drop: Fügt abgelegte Ordner hinzu."""
        dropped_files = self.tk.splitlist(event.data)
        for file in dropped_files:
            if os.path.isdir(file):
                if file not in self.input_folders:
                    self.input_folders.append(file)
                    self.insert_folder(file)
                    message = f"Added folder: {file}\n"
                    print(message)
                    sys.__stdout__.write(message)

    def on_treeview_open(self, event):
        """Lädt Unterordner, wenn ein Knoten erweitert wird."""
        item = self.input_tree.focus()
        children = self.input_tree.get_children(item)
        if children:
            # Prüfe, ob der erste Kindknoten ein Dummy ist
            first_child = children[0]
            if self.input_tree.item(first_child, "text") == "dummy":
                self.input_tree.delete(first_child)
                self.load_subfolders(item)

    def load_subfolders(self, parent):
        """Lädt die Unterordner des angegebenen Parent-Ordners in die Treeview."""
        folder = self.input_tree.item(parent, "text")
        try:
            for entry in os.listdir(folder):
                full_path = os.path.join(folder, entry)
                if os.path.isdir(full_path):
                    self.input_tree.insert(parent, "end", iid=full_path, text=full_path)
                    if self.has_subfolder(full_path):
                        self.input_tree.insert(full_path, "end", text="dummy")
        except Exception as e:
            message = f"Error loading subfolders for {folder}: {e}\n"
            print(message)
            sys.__stdout__.write(message)

    def select_input(self):
        """Öffnet den Ordner-Auswahldialog und fügt den gewählten Ordner hinzu."""
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            if folder not in self.input_folders:
                self.input_folders.append(folder)
                self.insert_folder(folder)
                message = f"Added folder: {folder}\n"
                print(message)
                sys.__stdout__.write(message)

    def remove_input(self):
        """Entfernt den ausgewählten Ordner (Root-Knoten) aus der Treeview und der internen Liste."""
        selected = self.input_tree.selection()
        if not selected:
            message = "No folder selected to remove.\n"
            print(message)
            sys.__stdout__.write(message)
            return
        for node in selected:
            if self.input_tree.parent(node) == "":
                if node in self.input_folders:
                    self.input_folders.remove(node)
            self.input_tree.delete(node)
            message = f"Removed folder: {node}\n"
            print(message)
            sys.__stdout__.write(message)

    def select_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_entry.config(state="normal")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            self.output_entry.config(state="readonly")
            sys.__stdout__.write(f"User selected {folder} as output folder.\n")

    def start_ocr(self):
        if not self.running:
            self.running = True
            self.start_button.config(state=DISABLED)
            self.pause_button.config(state=NORMAL)
            self.resume_button.config(state=DISABLED)
            self.ocr_thread = threading.Thread(target=self.run_ocr)
            self.ocr_thread.start()
            self.update_progress_bar()

    def run_ocr(self):
        if not self.input_folders or not hasattr(self, "output_folder") or not self.output_folder:
            print("Please select at least one input folder and an output folder before starting OCR.\n")
            self.running = False
            self.start_button.config(state=NORMAL)
            self.pause_button.config(state=DISABLED)
            self.resume_button.config(state=DISABLED)
            return

        for folder in self.input_folders:
            batch_ocr_pdfs(
                input_dir=folder,
                output_dir=self.output_folder,
                use_gpu=False,
                language="deu+eng",
                deskew=True,
                jobs=4,
                pause_event=self.resume_event,  # Übergibt das Event für Pause/Resume
                update_status_callback=lambda completed, current, next_items, current_index, total: 
                    self.schedule_update_status(completed, current, next_items, current_index, total)
            )

        self.running = False
        self.start_button.config(state=NORMAL)
        self.pause_button.config(state=DISABLED)
        self.resume_button.config(state=DISABLED)

    def pause_ocr(self):
        self.resume_event.clear()  # Blockiert den OCR-Thread
        self.pause_button.config(state=DISABLED)
        self.resume_button.config(state=NORMAL)
        print("OCR processing paused.\n")

    def resume_ocr(self):
        self.resume_event.set()  # Gibt den OCR-Thread frei
        self.pause_button.config(state=NORMAL)
        self.resume_button.config(state=DISABLED)
        print("OCR processing resumed.\n")

    def update_progress_bar(self):
        if self.running:
            current = self.progress['value']
            if self.resume_event.is_set() and current < 100:
                self.progress['value'] = current + 1
            self.after(1000, self.update_progress_bar)
        else:
            self.progress['value'] = 100

if __name__ == "__main__":
    app = OCRGUI()
    app.mainloop()
