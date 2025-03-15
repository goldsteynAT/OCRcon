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
        self.input_folders = []  # List to store multiple input folders

        # Setze die Hintergrundfarbe des Hauptfensters
        self.configure(bg="#f3f4f4")

        # Erstelle einen neuen Stil für Frames mit hellgrauem Hintergrund
        self.style.configure("TFrame", background="#f3f4f4")

        # Frame for input folder selection
        self.input_frame = ttk.Frame(self, style="TFrame")
        self.input_frame.pack(pady=5, fill=tk.X, padx=10)

        # Select Input Folder Button
        self.select_input_button = ttk.Button(self.input_frame, text="Select Input Folder", command=self.select_input)
        self.select_input_button.pack(pady=5)

        # Textfeld für ausgewählte Input-Folder (mehrere Zeilen) mit hellgrauem Hintergrund
        self.input_text = scrolledtext.ScrolledText(self.input_frame, wrap=tk.WORD, height=5, width=60, bg="#f3f4f4")
        self.input_text.pack(side=tk.TOP, fill=tk.X)

        # Frame for output folder selection
        self.output_frame = ttk.Frame(self, style="TFrame")
        self.output_frame.pack(pady=5, fill=tk.X, padx=10)

        # Select Output Folder Button
        self.select_output_button = ttk.Button(self.output_frame, text="Select Output Folder", command=self.select_output)
        self.select_output_button.pack(pady=5)

        # Output Folder Label mit Hintergrundfarbe
        self.output_label = ttk.Label(self.output_frame, text="Output Folder: Not selected", anchor="center", justify="center", background="#f3f4f4")
        self.output_label.pack(side=tk.TOP, fill=tk.X)

        # Control buttons (Start, Pause, Resume)
        self.control_frame = ttk.Frame(self, style="TFrame")
        self.control_frame.pack(pady=10)

        self.start_button = ttk.Button(self.control_frame, text="Start OCR", command=self.start_ocr)
        self.pause_button = ttk.Button(self.control_frame, text="Pause", command=self.pause_ocr, state=DISABLED)
        self.resume_button = ttk.Button(self.control_frame, text="Resume", command=self.resume_ocr, state=DISABLED)

        self.start_button.pack(side=tk.LEFT, padx=5)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        self.resume_button.pack(side=tk.LEFT, padx=5)

        # Progress Bar
        self.progress = ttk.Progressbar(self, length=600, mode='determinate')
        self.progress.pack(pady=10)

        # Log Output mit hellgrauem Hintergrund
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15, bg="#f3f4f4")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Redirect stdout/stderr to the log_text widget
        sys.stdout = RedirectText(self.log_text)
        sys.stderr = RedirectText(self.log_text)

        # OCR processing thread and control variables
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
                self.input_text.insert(tk.END, folder + "\n")  # Add folder to text area
            sys.__stdout__.write(f"User selected {folder} as an input folder.\n")

    def select_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_label.config(text=f"Output Folder: {folder}")
            sys.__stdout__.write(f"User selected {folder} as output folder.\n")


if __name__ == "__main__":
    app = OCRGUI()
    app.mainloop()
