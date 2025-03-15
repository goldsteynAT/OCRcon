import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sys
import time
import os
from ocr_processing import batch_ocr_pdfs
from tkinterdnd2 import TkinterDnD, DND_FILES

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
        # Verwende nun TkinterDnD.Tk als Basisklasse
        TkinterDnD.Tk.__init__(self)
        style = ttk.Style(theme='flatly')
        self.title("OCRcon - Control. Connect. Consertis.")
        self.geometry("800x600")
        self.input_folders = []  # Liste für mehrere Input-Ordner

        # Einheitliche Button-Schriftart setzen
        style.configure('TButton', font=('Segoe UI Emoji', 10))

        # Übergeordneter Frame für Quell- und Zielordner
        self.folder_frame = ttk.Frame(self, borderwidth=1, relief="solid")
        self.folder_frame.pack(fill=tk.X, padx=10, pady=10)

        # Quellordner Frame (mit Label, Listbox und Buttons)
        self.input_frame = ttk.Frame(self.folder_frame)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.input_label_desc = ttk.Label(self.input_frame, text="📂 Input Folders:", font=("Segoe UI Emoji", 12), anchor="w")
        self.input_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))

        # Listbox mit Scrollbar einbetten
        self.input_listbox_frame = ttk.Frame(self.input_frame)
        self.input_listbox_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.input_listbox = tk.Listbox(self.input_listbox_frame, height=5)
        self.input_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.input_scrollbar = ttk.Scrollbar(self.input_listbox_frame, orient=tk.VERTICAL, command=self.input_listbox.yview)
        self.input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.input_listbox.config(yscrollcommand=self.input_scrollbar.set)

        # Registriere die Listbox als Drop-Ziel
        self.input_listbox.drop_target_register(DND_FILES)
        self.input_listbox.dnd_bind('<<Drop>>', self.handle_drop)

        # Button-Frame für Add/Remove-Buttons, rechtsbündig
        self.input_buttons_frame = ttk.Frame(self.input_frame)
        self.input_buttons_frame.pack(fill=tk.X, padx=5, pady=5, anchor="e")

        self.remove_input_button = ttk.Button(self.input_buttons_frame, text="➖ Remove Folder", command=self.remove_input)
        self.remove_input_button.pack(side=tk.RIGHT, padx=5)

        self.select_input_button = ttk.Button(self.input_buttons_frame, text="➕ Add Folder", command=self.select_input)
        self.select_input_button.pack(side=tk.RIGHT, padx=5)

        # Separator zwischen Quellordner und Zielordner
        self.separator = ttk.Separator(self.folder_frame, orient="horizontal")
        self.separator.pack(fill="x", padx=5, pady=5)

        # Zielordner Frame (mit Label, Entry und Button)
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
        self.paused = False

    def handle_drop(self, event):
        # event.data enthält die abgelegten Dateipfade als String; Umwandlung in eine Liste
        dropped_files = self.tk.splitlist(event.data)
        for file in dropped_files:
            if os.path.isdir(file):
                if file not in self.input_folders:
                    self.input_folders.append(file)
                    self.input_listbox.insert(tk.END, file)
                    message = f"Added folder: {file}\n"
                    print(message)
                    sys.__stdout__.write(message)

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
                jobs=4
            )

        self.running = False
        self.start_button.config(state=NORMAL)
        self.pause_button.config(state=DISABLED)
        self.resume_button.config(state=DISABLED)

    def pause_ocr(self):
        self.paused = True
        self.pause_button.config(state=DISABLED)
        self.resume_button.config(state=NORMAL)
        print("OCR processing paused.\n")

    def resume_ocr(self):
        self.paused = False
        self.pause_button.config(state=NORMAL)
        self.resume_button.config(state=DISABLED)
        print("OCR processing resumed.\n")

    def update_progress_bar(self):
        if self.running:
            current = self.progress['value']
            if not self.paused and current < 100:
                self.progress['value'] = current + 1
            self.after(1000, self.update_progress_bar)
        else:
            self.progress['value'] = 100

    def select_input(self):
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            if folder not in self.input_folders:
                self.input_folders.append(folder)
                self.input_listbox.insert(tk.END, folder)
                message = f"Added folder: {folder}\n"
                print(message)
                sys.__stdout__.write(message)

    def remove_input(self):
        selected_indices = self.input_listbox.curselection()
        if not selected_indices:
            message = "No folder selected to remove.\n"
            print(message)
            sys.__stdout__.write(message)
            return
        for index in reversed(selected_indices):
            folder = self.input_listbox.get(index)
            self.input_listbox.delete(index)
            if folder in self.input_folders:
                self.input_folders.remove(folder)
            message = f"Removed folder: {folder}\n"
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

if __name__ == "__main__":
    app = OCRGUI()
    app.mainloop()
