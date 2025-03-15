import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sys
import time
from ocr_processing import batch_ocr_pdfs

# Redirect stdout to a Text widget
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, s):
        self.text_widget.insert(tk.END, s)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class OCRGUI(ttk.Window):
    def __init__(self):
        super().__init__(themename="litera")
        self.title("OCR Consertis - Desktop Application")
        self.geometry("800x600")
        self.input_folders = []  # Liste für mehrere Input-Ordner

        # Hintergrundfarbe des Hauptfensters setzen
        self.configure(bg="#f3f4f4")

        # --- Input-Bereich in Labelframe ---
        self.input_labelframe = ttk.Labelframe(self, text="Ordner wählen", bootstyle="primary")
        self.input_labelframe.pack(pady=5, fill=tk.X, padx=10)

        # Mehrzeiliges Textfeld zur Anzeige der ausgewählten Ordner
        self.input_text = scrolledtext.ScrolledText(self.input_labelframe, wrap=tk.WORD, height=5, bg="#f3f4f4")
        self.input_text.pack(fill=tk.X, padx=5, pady=(5, 0))

        # Button "Select Input Folder" (rechtsbündig, unterhalb der Textbox)
        self.select_input_button = ttk.Button(self.input_labelframe, text="Select Input Folder", command=self.select_input)
        self.select_input_button.pack(anchor="e", padx=5, pady=5)

        # --- Output-Bereich in Labelframe ---
        self.output_labelframe = ttk.Labelframe(self, text="Output Folder:", bootstyle="primary")
        self.output_labelframe.pack(pady=5, fill=tk.X, padx=10)

        # Einzeilige Entry-Box zur Anzeige des ausgewählten Output-Ordners
        self.output_entry = ttk.Entry(self.output_labelframe, state="readonly")
        self.output_entry.pack(fill=tk.X, padx=5, pady=(5, 0))

        # Button "Select Output Folder" (rechtsbündig, unterhalb der Entry-Box)
        self.select_output_button = ttk.Button(self.output_labelframe, text="Select Output Folder", command=self.select_output)
        self.select_output_button.pack(anchor="e", padx=5, pady=5)

        # --- Steuerungselemente (Start, Pause, Resume) ---
        self.control_frame = ttk.Frame(self, style="TFrame")
        self.control_frame.pack(pady=10)

        self.start_button = ttk.Button(self.control_frame, text="Start OCR", command=self.start_ocr)
        self.pause_button = ttk.Button(self.control_frame, text="Pause", command=self.pause_ocr, state=DISABLED)
        self.resume_button = ttk.Button(self.control_frame, text="Resume", command=self.resume_ocr, state=DISABLED)

        self.start_button.pack(side=tk.LEFT, padx=5)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        self.resume_button.pack(side=tk.LEFT, padx=5)

        # Fortschrittsbalken
        self.progress = ttk.Progressbar(self, length=600, mode='determinate')
        self.progress.pack(pady=10)

        # Log-Ausgabe mit hellgrauem Hintergrund
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15, bg="#f3f4f4")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Umleitung von stdout/stderr auf das Log-Textfeld
        sys.stdout = RedirectText(self.log_text)
        sys.stderr = RedirectText(self.log_text)

        # OCR-Thread und Steuerungsvariablen
        self.ocr_thread = None
        self.running = False
        self.paused = False

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
                self.input_text.insert(tk.END, folder + "\n")  # Ordner zur Textbox hinzufügen
            sys.__stdout__.write(f"User selected {folder} as an input folder.\n")

    def select_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            # Aktualisiere die Entry-Box mit dem ausgewählten Ordner
            self.output_entry.config(state="normal")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            self.output_entry.config(state="readonly")
            sys.__stdout__.write(f"User selected {folder} as output folder.\n")

if __name__ == "__main__":
    app = OCRGUI()
    app.mainloop()
