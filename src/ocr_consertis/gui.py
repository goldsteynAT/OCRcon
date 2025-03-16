import threading
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sys
import os
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk

from viewmodel import PdfTrackerSingleton

# Create the singleton instance directly
pdf_tracker = PdfTrackerSingleton()

# Redirect stdout to a Text widget
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
    def write(self, s):
        self.text_widget.insert(tk.END, s)
        self.text_widget.see(tk.END)
    def flush(self):
        pass

class LogoSection(ttk.Frame):
    def __init__(self, parent, logo_path, scale_factor=0.3, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        image = Image.open(logo_path)
        w, h = image.size
        image = image.resize((int(w * scale_factor), int(h * scale_factor)), Image.LANCZOS)
        self.logo_image = ImageTk.PhotoImage(image)
        self.logo_label = ttk.Label(self, image=self.logo_image)
        self.logo_label.pack(anchor="center")

class InputSection(ttk.Frame):
    """
    Input section that displays folders and updates when the PdfTrackerSingleton changes.
    """
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.app = app
        self.pdf_tracker = PdfTrackerSingleton()  # Get singleton instance

        # Register GUI update callback with singleton
        self.pdf_tracker.set_update_callback(self.update_pdf_display)

        self.input_label_desc = ttk.Label(self, text="📂 Input Folders:", font=("Segoe UI Emoji", 12), anchor="w")
        self.input_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))

        # Label to show total PDFs
        self.input_status_label = ttk.Label(
            self, text=f"Total PDFs: {self.pdf_tracker.totalPdfs}, To be processed: {self.pdf_tracker.pdfsTobeProcessed}",
            font=("Segoe UI", 10)
        )
        self.input_status_label.pack(fill=tk.X, padx=5, pady=(0, 5), anchor="ne")

        # Tree view for folders
        self.input_tree_frame = ttk.Frame(self)
        self.input_tree_frame.pack(fill=tk.BOTH, padx=5, pady=(5, 0))
        self.input_tree = ttk.Treeview(self.input_tree_frame, show="tree")
        self.input_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_tree_scrollbar = ttk.Scrollbar(self.input_tree_frame, orient=tk.VERTICAL, command=self.input_tree.yview)
        self.input_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_tree.config(yscrollcommand=self.input_tree_scrollbar.set)

        # Buttons to add/remove folders
        self.input_buttons_frame = ttk.Frame(self)
        self.input_buttons_frame.pack(fill=tk.X, padx=5, pady=5, anchor="e")

        self.remove_input_button = ttk.Button(
            self.input_buttons_frame,
            text="➖ Remove Folder",
            command=self.remove_folder
        )
        self.remove_input_button.pack(side=tk.RIGHT, padx=5)

        self.select_input_button = ttk.Button(
            self.input_buttons_frame,
            text="➕ Add Folder",
            command=self.select_folder
        )
        self.select_input_button.pack(side=tk.RIGHT, padx=5)

    def update_pdf_display(self, total_pdfs, to_be_processed):
        """Update the GUI when the singleton updates its variables."""
        self.input_status_label.config(text=f"Total PDFs: {total_pdfs}, To be processed: {to_be_processed}")

    def select_folder(self):
        """Call the singleton method to select a folder."""
        self.pdf_tracker.select_input(self.app)

    def remove_folder(self):
        """Call the singleton method to remove a folder."""
        self.pdf_tracker.remove_input(self.app)


class OutputSection(ttk.Frame):
    """
    Takes 'app' as an extra parameter so we can call app.set_output_folder().
    """
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.app = app
        self.output_label_desc = ttk.Label(self, text="📁 Output Folder:", font=("Segoe UI Emoji", 12), anchor="w")
        self.output_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.output_entry = ttk.Entry(self, state="readonly")
        self.output_entry.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.select_output_button = ttk.Button(self, text="🔎 Browse", command=self.app.set_output_folder)
        self.select_output_button.pack(anchor="e", padx=5, pady=5)

class ControlSection(ttk.Frame):
    """
    Takes 'app' as an extra parameter so we can call app.start_ocr(), app.pause_ocr(), etc.
    """
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.app = app
        self.start_button = ttk.Button(self, text="🚀 Start OCR", command=self.app.start_ocr)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.pause_button = ttk.Button(self, text="⏸️ Pause", command=self.app.pause_ocr, state=DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        self.resume_button = ttk.Button(self, text="🔄 Resume", command=self.app.resume_ocr, state=DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=5)

class NotebookSection(ttk.Notebook):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.next_frame = ttk.Frame(self)
        self.add(self.next_frame, text="Next")
        self.next_status_label = ttk.Label(self.next_frame, text="Number of PDFs to be processed: 0", font=("Segoe UI", 10))
        self.next_status_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.next_tree = ttk.Treeview(self.next_frame, columns=("File",), show="tree")
        self.next_tree.pack(fill=tk.BOTH, expand=True)
        self.next_scrollbar = ttk.Scrollbar(self.next_frame, orient=tk.VERTICAL, command=self.next_tree.yview)
        self.next_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.next_tree.config(yscrollcommand=self.next_scrollbar.set)
        self.completed_frame = ttk.Frame(self)
        self.add(self.completed_frame, text="Completed")
        self.completed_status_label = ttk.Label(self.completed_frame, text="Number of completed PDFs: 0", font=("Segoe UI", 10))
        self.completed_status_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.completed_tree = ttk.Treeview(self.completed_frame, columns=("File",), show="tree")
        self.completed_tree.pack(fill=tk.BOTH, expand=True)
        self.completed_scrollbar = ttk.Scrollbar(self.completed_frame, orient=tk.VERTICAL, command=self.completed_tree.yview)
        self.completed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.completed_tree.config(yscrollcommand=self.completed_scrollbar.set)

class LogSection(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.log_text = tk.Text(self, wrap=tk.WORD, height=15)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=self.log_scrollbar.set)

class OCRGUI(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        # These attributes are used by model.py
        self.input_folders = []
        self.output_folder = None

        style = ttk.Style(theme='flatly')
        self.title("OCRcon - Control. Connect. Consertis.")
        self.geometry("800x800")
        style.configure('TButton', font=('Segoe UI Emoji', 10))
        self.tracker = PdfTrackerSingleton()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "image.png")
        self.logo_section = LogoSection(self, logo_path=logo_path)
        self.logo_section.pack(fill="x", pady=10)
        self.folder_frame = ttk.Frame(self, borderwidth=1, relief="solid")
        self.folder_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.input_section = InputSection(self, self)
        self.input_section.pack()

        # Simulating the PdfTrackerSingleton for updating
        self.pdf_tracker = PdfTrackerSingleton()
        self.separator = ttk.Separator(self.folder_frame, orient="horizontal")
        self.separator.pack(fill="x", padx=5, pady=5)
        self.output_section = OutputSection(self.folder_frame, app=self)
        self.output_section.pack(fill=tk.X, padx=5, pady=5)
        self.control_section = ControlSection(self, app=self)
        self.control_section.pack(pady=10)
        self.progress = ttk.Progressbar(self, length=600, mode='determinate')
        self.progress.pack(pady=10)
        self.current_label = ttk.Label(self, text="Currently Processing: None", font=("Segoe UI", 10), anchor="center", justify="center")
        self.current_label.pack(fill=tk.X, padx=10, pady=(10, 0))
        self.notebook_section = NotebookSection(self)
        self.notebook_section.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        self.log_section = LogSection(self)
        self.log_section.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sys.stdout = RedirectText(self.log_section.log_text)
        sys.stderr = RedirectText(self.log_section.log_text)
        self.ocr_thread = None
        self.running = False
        self.resume_event = threading.Event()
        self.resume_event.set()

    def add_folder(self):
        self.tracker.select_input(self)
        self._update_ui_from_tracker()

    def remove_folder(self):
        self.tracker.remove_input(self)
        self._update_ui_from_tracker()

    def set_output_folder(self):
        self.tracker.select_output(self)
        self._update_ui_from_tracker()

    def handle_drop(self, event):
        from viewmodel import handle_drop  # Importiere die Funktion aus viewmodel
        handle_drop(self, event)

    def on_treeview_open(self, event):
        print("Treeview node opened")

    def start_ocr(self):
        print("Starting OCR...")

    def pause_ocr(self):
        print("Pausing OCR...")

    def resume_ocr(self):
        print("Resuming OCR...")

    def _update_ui_from_tracker(self):
        total = self.tracker.totalPdfs
        to_be_processed = self.tracker.pdfsTobeProcessed
        self.input_section.input_status_label.configure(
            text=f"Total PDFs: {total}, To be processed: {to_be_processed}"
        )
        self.notebook_section.next_status_label.configure(
            text=f"Number of PDFs to be processed: {to_be_processed}"
        )

    # Bridge functions so that model.py can access expected controller members.
    @property
    def input_tree(self):
        return self.input_section.input_tree

    @property
    def output_entry(self):
        return self.output_section.output_entry

    def insert_folder(self, folder):
        # (Not used in the recursive insertion now because model.select_input directly inserts nodes.)
        self.input_tree.insert("", "end", iid=folder, text=folder)

    def update_input_folder_status(self):
        self._update_ui_from_tracker()

    def load_subfolders(self, parent):
        import model
        model.load_all_subfolders(self, parent, self.input_tree.item(parent, "text"))

    def has_subfolder(self, folder):
        try:
            for entry in os.listdir(folder):
                full_path = os.path.join(folder, entry)
                if os.path.isdir(full_path):
                    return True
            return False
        except Exception:
            return False

if __name__ == "__main__":
    app = OCRGUI()
    app.mainloop()
