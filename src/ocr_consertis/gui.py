import threading
import tkinter as tk
from tkinter import scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sys
import time
from ocr_processing import batch_ocr_pdfs
from tkinter import filedialog


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

        # Folder selection buttons and labels
        self.folder_frame = ttk.Frame(self)
        self.folder_frame.pack(pady=10)

        self.select_input_button = ttk.Button(self.folder_frame, text="Select Input Folder", command=self.select_input)
        self.select_output_button = ttk.Button(self.folder_frame, text="Select Output Folder", command=self.select_output)

        self.input_label = ttk.Label(self.folder_frame, text="Input Folder: Not selected")
        self.output_label = ttk.Label(self.folder_frame, text="Output Folder: Not selected")

        # Layout for folder selection
        self.select_input_button.pack(side=tk.LEFT, padx=5)
        self.select_output_button.pack(side=tk.LEFT, padx=5)
        self.input_label.pack(side=tk.LEFT, padx=5)
        self.output_label.pack(side=tk.LEFT, padx=5)


        # Create UI elements
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(pady=10)
        self.start_button = ttk.Button(self.control_frame, text="Start OCR", command=self.start_ocr)
        self.pause_button = ttk.Button(self.control_frame, text="Pause", command=self.pause_ocr, state=DISABLED)
        self.resume_button = ttk.Button(self.control_frame, text="Resume", command=self.resume_ocr, state=DISABLED)
        self.progress = ttk.Progressbar(self, length=600, mode='determinate')
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15)

        # Layout UI elements
        self.start_button.pack(pady=10)
        self.pause_button.pack(pady=5)
        self.resume_button.pack(pady=5)
        self.progress.pack(pady=10)
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
            # Start OCR processing in a background thread
            self.ocr_thread = threading.Thread(target=self.run_ocr)
            self.ocr_thread.start()
            self.update_progress_bar()

    def run_ocr(self):
        # Check if both input and output folders have been selected
        if not hasattr(self, "input_folder") or not self.input_folder or not hasattr(self, "output_folder") or not self.output_folder:
            print("Please select both input and output folders before starting OCR.\n")
            self.running = False
            self.start_button.config(state=NORMAL)
            self.pause_button.config(state=DISABLED)
            self.resume_button.config(state=DISABLED)
            return

        # Call the batch OCR process using user-selected folders
        batch_ocr_pdfs(
            input_dir=self.input_folder,
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
        # For simplicity, we simulate a pause by setting a flag
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
        # Dummy progress update: In a real implementation, you might poll shared status updates.
        if self.running:
            current = self.progress['value']
            # Only update if not paused
            if not self.paused and current < 100:
                self.progress['value'] = current + 1
            self.after(1000, self.update_progress_bar)
        else:
            self.progress['value'] = 100
    
    def select_input(self):
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.input_folder = folder
            self.input_label.config(text=f"Input Folder: {folder}")
            sys.__stdout__.write(f"User selected {folder} as input folder.\n")

    def select_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_label.config(text=f"Output Folder: {folder}")
            sys.__stdout__.write(f"User selected {folder} as output folder.\n")



if __name__ == "__main__":
    app = OCRGUI()
    app.mainloop()
