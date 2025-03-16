import threading
import sys
import os
from tkinter import filedialog
import model  # Delegates to model.py

def handle_drop(self, event):
    dropped_files = self.tk.splitlist(event.data)
    for file in dropped_files:
        if os.path.isdir(file):
            if file not in self.input_folders:
                self.input_folders.append(file)
                # Use the controller’s insert method (which now will show all subfolders)
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

def start_ocr(self):
    if not self.running:
        self.running = True
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.resume_button.config(state="disabled")
        self.ocr_thread = threading.Thread(target=self.run_ocr)
        self.ocr_thread.start()
        self.update_progress_bar()

def run_ocr(self):
    if not self.input_folders or not hasattr(self, "output_folder") or not self.output_folder:
        print("Please select at least one input folder and an output folder before starting OCR.\n")
        self.running = False
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="disabled")
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
    self.start_button.config(state="normal")
    self.pause_button.config(state="disabled")
    self.resume_button.config(state="disabled")

def pause_ocr(self):
    self.resume_event.clear()
    self.pause_button.config(state="disabled")
    self.resume_button.config(state="normal")
    print("OCR processing paused.\n")

def resume_ocr(self):
    self.resume_event.set()
    self.pause_button.config(state="normal")
    self.resume_button.config(state="disabled")
    print("OCR processing resumed.\n")

def update_progress_bar(self):
    if self.running:
        current = self.progress['value']
        if self.resume_event.is_set() and current < 100:
            self.progress['value'] = current + 1
        self.after(1000, self.update_progress_bar)
    else:
        self.progress['value'] = 100

import model  # Assuming model.py contains select_input(), remove_input(), etc.

import os

class PdfTrackerSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PdfTrackerSingleton, cls).__new__(cls, *args, **kwargs)
            cls._instance.totalPdfs = 0
            cls._instance.pdfsTobeProcessed = 0
            cls._instance._update_callback = None
        return cls._instance

    def set_update_callback(self, callback):
        """Register a callback that gets called whenever PDFs count updates."""
        self._update_callback = callback

    def _notify_update(self):
        """Notify the registered callback about current totals."""
        if self._update_callback:
            self._update_callback(self.totalPdfs, self.pdfsTobeProcessed)

    def update_pdf_count(self, controller):
        """
        Example method to update PDF counts based on controller's input folders.
        Call _notify_update() whenever totalPdfs changes, so the GUI can react.
        """
        total = 0
        for folder in controller.input_folders:
            for _, _, files in os.walk(folder):
                total += sum(1 for file in files if file.lower().endswith('.pdf'))
        self.totalPdfs = total
        self.pdfsTobeProcessed = total
        self._notify_update()

    def select_input(self, controller):
        """Example method that might be called when 'Add Folder' is clicked."""
        # Do your logic, e.g. model.select_input(controller)
        # Then update counts:
        self.update_pdf_count(controller)

    def remove_input(self, controller):
        """Example method that might be called when 'Remove Folder' is clicked."""
        # Do your logic, e.g. model.remove_input(controller)
        # Then update counts:
        self.update_pdf_count(controller)



class BatchPdfProcessedSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(BatchPdfProcessedSingleton, cls).__new__(cls, *args, **kwargs)
            cls._instance.totalProcessedPdfs = 0
            cls._instance.pdfsProcessedOfBatch = 0
            cls._instance.numberOfPdfsToBeProcessed = 0
        return cls._instance
