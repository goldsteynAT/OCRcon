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
        self.logo_frame.pack(fill="x", pady=10)
        image = Image.open(logo_path)
        original_width, original_height = image.size
        scale_factor = 0.3
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        image = image.resize((new_width, new_height), Image.LANCZOS)
        self.logo_image = ImageTk.PhotoImage(image)
        self.logo_label = ttk.Label(self.logo_frame, image=self.logo_image)
        self.logo_label.pack(anchor="center")

        # Übergeordneter Frame für Quell- und Zielordner
        self.folder_frame = ttk.Frame(self, borderwidth=1, relief="solid")
        self.folder_frame.pack(fill=tk.X, padx=10, pady=10)

        # Input Folder Frame (mit Label, Treeview, Buttons und Status-Label)
        self.input_frame = ttk.Frame(self.folder_frame)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.input_label_desc = ttk.Label(self.input_frame, text="📂 Input Folders:", font=("Segoe UI Emoji", 12), anchor="w")
        self.input_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))
        # Neues Status-Label für die Input Folder Box (rechts oben)
        self.input_status_label = ttk.Label(self.input_frame, text="Total PDFs: 0, To be processed: 0", font=("Segoe UI", 10))
        self.input_status_label.pack(fill=tk.X, padx=5, pady=(0,5), anchor="ne")

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
        self.input_tree.bind("<<TreeviewOpen>>", self.on_treeview_open)

        # Button-Frame für Add/Remove-Buttons
        self.input_buttons_frame = ttk.Frame(self.input_frame)
        self.input_buttons_frame.pack(fill=tk.X, padx=5, pady=5, anchor="e")
        self.remove_input_button = ttk.Button(self.input_buttons_frame, text="➖ Remove Folder", command=self.remove_input)
        self.remove_input_button.pack(side=tk.RIGHT, padx=5)
        self.select_input_button = ttk.Button(self.input_buttons_frame, text="➕ Add Folder", command=self.select_input)
        self.select_input_button.pack(side=tk.RIGHT, padx=5)

        # Separator zwischen Input und Output
        self.separator = ttk.Separator(self.folder_frame, orient="horizontal")
        self.separator.pack(fill="x", padx=5, pady=5)

        # Output Folder Frame
        self.output_frame = ttk.Frame(self.folder_frame)
        self.output_frame.pack(fill=tk.X, padx=5, pady=5)
        self.output_label_desc = ttk.Label(self.output_frame, text="📁 Output Folder:", font=("Segoe UI Emoji", 12), anchor="w")
        self.output_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.output_entry = ttk.Entry(self.output_frame, state="readonly")
        self.output_entry.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.select_output_button = ttk.Button(self.output_frame, text="🔎 Browse", command=self.select_output)
        self.select_output_button.pack(anchor="e", padx=5, pady=5)

        # Steuerungselemente (Start, Pause, Resume)
        self.control_frame = ttk.Frame(self, style="TFrame")
        self.control_frame.pack(pady=10)
        self.start_button = ttk.Button(self.control_frame, text="🚀 Start OCR", command=self.start_ocr)
        self.pause_button = ttk.Button(self.control_frame, text="⏸️ Pause", command=self.pause_ocr, state=DISABLED)
        self.resume_button = ttk.Button(self.control_frame, text="🔄 Resume", command=self.resume_ocr, state=DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        self.resume_button.pack(side=tk.LEFT, padx=5)

        # Fortschrittsbalken
        self.progress = ttk.Progressbar(self, length=600, mode='determinate')
        self.progress.pack(pady=10)

        # Label für aktuell verarbeitete PDF oberhalb des Notebooks
        self.current_label = ttk.Label(self, text="Currently Processing: None", font=("Segoe UI", 10), anchor="center", justify="center")
        self.current_label.pack(fill=tk.X, padx=10, pady=(10, 0))


        # Notebook für Statusanzeigen (Next / Completed)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        # Tab für Next PDFs
        self.next_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.next_frame, text="Next")
        self.next_status_label = ttk.Label(self.next_frame, text="Number of PDFs to be processed: 0", font=("Segoe UI", 10))
        self.next_status_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.next_tree = ttk.Treeview(self.next_frame, columns=("File",), show="tree")
        self.next_tree.pack(fill=tk.BOTH, expand=True)
        self.next_scrollbar = ttk.Scrollbar(self.next_frame, orient=tk.VERTICAL, command=self.next_tree.yview)
        self.next_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.next_tree.config(yscrollcommand=self.next_scrollbar.set)
        # Tab für Completed PDFs
        self.completed_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.completed_frame, text="Completed")
        self.completed_status_label = ttk.Label(self.completed_frame, text="Number of completed PDFs: 0", font=("Segoe UI", 10))
        self.completed_status_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.completed_tree = ttk.Treeview(self.completed_frame, columns=("File",), show="tree")
        self.completed_tree.pack(fill=tk.BOTH, expand=True)
        self.completed_scrollbar = ttk.Scrollbar(self.completed_frame, orient=tk.VERTICAL, command=self.completed_tree.yview)
        self.completed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.completed_tree.config(yscrollcommand=self.completed_scrollbar.set)

        # Log-Ausgabe
        self.log_frame = ttk.Frame(self)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=self.log_scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sys.stdout = RedirectText(self.log_text)
        sys.stderr = RedirectText(self.log_text)

        # OCR-Thread und Steuerungsvariablen
        self.ocr_thread = None
        self.running = False
        self.resume_event = threading.Event()
        self.resume_event.set()

    def update_input_folder_status(self):
        """Berechnet und aktualisiert die Gesamtzahl der PDFs und die noch zu verarbeitenden PDFs in den Input-Folders."""
        total = 0
        for folder in self.input_folders:
            for root, dirs, files in os.walk(folder):
                total += sum(1 for file in files if file.lower().endswith('.pdf'))
        
        # Lade die bereits verarbeiteten PDFs aus der Statusdatei
        from status_manager import load_status
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logs_dir = os.path.join(project_root, "logs")
        status_file = os.path.join(logs_dir, "ocr_status.json")
        processed_list = load_status(status_file)
        processed_count = len(processed_list)
        
        to_be_processed = total - processed_count
        self.input_status_label.config(text=f"Total PDFs: {total}, To be processed: {to_be_processed}")



    def update_status_table(self, completed, current, next_items, current_index, total):
        """Updates the status display in the Notebook and current label."""
        self.current_label.config(text="Currently Processing: " + (current if current else "None"))
        self.next_status_label.config(text=f"Number of PDFs to be processed: {len(next_items)}")
        for row in self.next_tree.get_children():
            self.next_tree.delete(row)
        for file in next_items:
            self.next_tree.insert("", tk.END, text=file)
        self.completed_status_label.config(text=f"Number of completed PDFs: {len(completed)}")
        for row in self.completed_tree.get_children():
            self.completed_tree.delete(row)
        for file in completed:
            self.completed_tree.insert("", tk.END, text=file)

    def schedule_update_status(self, completed, current, next_items, current_index, total):
        self.after(0, lambda: self.update_status_table(completed, current, next_items, current_index, total))

    def has_subfolder(self, folder):
        try:
            for entry in os.listdir(folder):
                full_path = os.path.join(folder, entry)
                if os.path.isdir(full_path):
                    return True
            return False
        except Exception:
            return False

    def insert_folder(self, folder):
        self.input_tree.insert("", "end", iid=folder, text=folder)
        if self.has_subfolder(folder):
            self.input_tree.insert(folder, "end", text="dummy")

    def handle_drop(self, event):
        dropped_files = self.tk.splitlist(event.data)
        for file in dropped_files:
            if os.path.isdir(file):
                if file not in self.input_folders:
                    self.input_folders.append(file)
                    self.insert_folder(file)
                    message = f"Added folder: {file}\n"
                    print(message)
                    sys.__stdout__.write(message)
        self.update_input_folder_status()

    def on_treeview_open(self, event):
        item = self.input_tree.focus()
        children = self.input_tree.get_children(item)
        if children:
            first_child = children[0]
            if self.input_tree.item(first_child, "text") == "dummy":
                self.input_tree.delete(first_child)
                self.load_subfolders(item)

    def load_subfolders(self, parent):
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
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            if folder not in self.input_folders:
                self.input_folders.append(folder)
                self.insert_folder(folder)
                message = f"Added folder: {folder}\n"
                print(message)
                sys.__stdout__.write(message)
            self.update_input_folder_status()

    def remove_input(self):
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
        self.update_input_folder_status()

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
                pause_event=self.resume_event,
                update_status_callback=lambda completed, current, next_items, current_index, total: 
                    self.schedule_update_status(completed, current, next_items, current_index, total)
            )

        self.running = False
        self.start_button.config(state=NORMAL)
        self.pause_button.config(state=DISABLED)
        self.resume_button.config(state=DISABLED)

    def pause_ocr(self):
        self.resume_event.clear()
        self.pause_button.config(state=DISABLED)
        self.resume_button.config(state=NORMAL)
        print("OCR processing paused.\n")

    def resume_ocr(self):
        self.resume_event.set()
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
