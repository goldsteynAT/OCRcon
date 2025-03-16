import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sys
import os
from PIL import Image, ImageTk
from tkinterdnd2 import TkinterDnD, DND_FILES
from viewmodel import OCRViewModel

# Redirect stdout to a Text widget
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, s):
        self.text_widget.insert(tk.END, s)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class OCRView(TkinterDnD.Tk):
    """Main view class for the OCR application."""
    
    def __init__(self):
        # Initialize base Tkinter window with drag & drop support
        TkinterDnD.Tk.__init__(self)
        style = ttk.Style(theme='flatly')
        self.title("OCRcon - Control. Connect. Consertis.")
        self.geometry("800x900")
        
        # Get the ViewModel singleton instance
        self.viewmodel = OCRViewModel()
        
        # Set unified button font
        style.configure('TButton', font=('Segoe UI Emoji', 10))
        
        # Create the GUI components
        self._create_logo_section()
        self._create_folder_section()
        self._create_control_section()
        self._create_notebook_section()
        self._create_log_section()
        
        # Register callbacks with ViewModel
        self.viewmodel.add_status_subscriber(self.update_status)
        self.viewmodel.add_progress_subscriber(self.update_progress)
        self.viewmodel.add_time_subscriber(self.update_time_stats)
        
        # Register window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _create_logo_section(self):
        """Create the logo section at the top of the window."""
        # Find logo path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "image.png")
        
        # Logo frame for central positioning
        self.logo_frame = ttk.Frame(self)
        self.logo_frame.pack(fill="x", pady=10)
        
        # Load and resize logo if exists
        if os.path.exists(logo_path):
            try:
                image = Image.open(logo_path)
                original_width, original_height = image.size
                scale_factor = 0.3
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                image = image.resize((new_width, new_height), Image.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(image)
                self.logo_label = ttk.Label(self.logo_frame, image=self.logo_image)
                self.logo_label.pack(anchor="center")
            except Exception as e:
                print(f"Error loading logo: {e}")
                # Create text label as fallback
                self.logo_label = ttk.Label(self.logo_frame, text="OCRcon", font=("Segoe UI", 24, "bold"))
                self.logo_label.pack(anchor="center")
    
    def _create_folder_section(self):
        """Create the folder selection section."""
        # Parent frame for source and target folders
        self.folder_frame = ttk.Frame(self, borderwidth=1, relief="solid")
        self.folder_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # --- Input Folder Frame ---
        self.input_frame = ttk.Frame(self.folder_frame)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.input_label_desc = ttk.Label(self.input_frame, text="📂 Input Folders:", font=("Segoe UI Emoji", 12), anchor="w")
        self.input_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Status label for input folder box
        self.input_status_label = ttk.Label(self.input_frame, text="Total PDFs: 0, To be processed: 0", font=("Segoe UI", 10))
        self.input_status_label.pack(fill=tk.X, padx=5, pady=(0,5), anchor="ne")
        
        # Treeview for hierarchical folder structure
        self.input_tree_frame = ttk.Frame(self.input_frame)
        self.input_tree_frame.pack(fill=tk.BOTH, padx=5, pady=(5, 0))
        
        self.input_tree = ttk.Treeview(self.input_tree_frame, show="tree")
        self.input_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.input_tree_scrollbar = ttk.Scrollbar(self.input_tree_frame, orient=tk.VERTICAL, command=self.input_tree.yview)
        self.input_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_tree.config(yscrollcommand=self.input_tree_scrollbar.set)
        
        # Register Treeview as drop target
        self.input_tree.drop_target_register(DND_FILES)
        self.input_tree.dnd_bind('<<Drop>>', self.handle_drop)
        self.input_tree.bind("<<TreeviewOpen>>", self.on_treeview_open)
        
        # Buttons for Add/Remove
        self.input_buttons_frame = ttk.Frame(self.input_frame)
        self.input_buttons_frame.pack(fill=tk.X, padx=5, pady=5, anchor="e")
        
        self.remove_input_button = ttk.Button(self.input_buttons_frame, text="➖ Remove Folder", command=self.remove_input)
        self.remove_input_button.pack(side=tk.RIGHT, padx=5)
        
        self.select_input_button = ttk.Button(self.input_buttons_frame, text="➕ Add Folder", command=self.select_input)
        self.select_input_button.pack(side=tk.RIGHT, padx=5)
        
        # Separator between Input and Output
        self.separator = ttk.Separator(self.folder_frame, orient="horizontal")
        self.separator.pack(fill="x", padx=5, pady=5)
        
        # --- Output Folder Frame ---
        self.output_frame = ttk.Frame(self.folder_frame)
        self.output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.output_label_desc = ttk.Label(self.output_frame, text="📁 Output Folder:", font=("Segoe UI Emoji", 12), anchor="w")
        self.output_label_desc.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        self.output_entry = ttk.Entry(self.output_frame, state="readonly")
        self.output_entry.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        self.select_output_button = ttk.Button(self.output_frame, text="🔎 Browse", command=self.select_output)
        self.select_output_button.pack(anchor="e", padx=5, pady=5)
    
    def _create_control_section(self):
        """Create the control buttons and progress bar section."""
        # Control elements (Start, Pause, Resume)
        self.control_frame = ttk.Frame(self, style="TFrame")
        self.control_frame.pack(pady=10)
        
        self.start_button = ttk.Button(self.control_frame, text="🚀 Start OCR", command=self.start_ocr)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = ttk.Button(self.control_frame, text="⏸️ Pause", command=self.pause_ocr, state=DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.resume_button = ttk.Button(self.control_frame, text="🔄 Resume", command=self.resume_ocr, state=DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(self, length=600, mode='determinate')
        self.progress.pack(pady=(10, 5))
        
        # Detailed status label under progress bar
        self.detailed_status_frame = ttk.Frame(self)
        self.detailed_status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.detailed_status_label = ttk.Label(
            self.detailed_status_frame, 
            text="0/0 PDFs processed [0.0%] - 0s passed - estimated time until completion: 0s",
            font=("Segoe UI", 10),
            anchor="center",
            justify="center"
        )
        self.detailed_status_label.pack(fill=tk.X)
    
    def _create_notebook_section(self):
        """Create the notebook with tabs for next, completed and total completed PDFs."""
        # Label for currently processed PDF
        self.current_label = ttk.Label(self, text="Currently Processing: None", font=("Segoe UI", 10), anchor="center", justify="center")
        self.current_label.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # Create a frame to contain both notebook and log sections
        self.content_frame = ttk.Frame(self, borderwidth=1, relief="solid")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Notebook for status displays (Next / Completed / Total Completed)
        self.notebook = ttk.Notebook(self.content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab for Next PDFs
        self.next_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.next_frame, text="Next")
        
        self.next_status_label = ttk.Label(self.next_frame, text="Number of PDFs to be processed: 0", font=("Segoe UI", 10))
        self.next_status_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Create a frame to contain the tree and scrollbar for proper layout
        self.next_tree_container = ttk.Frame(self.next_frame)
        self.next_tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar first (right side)
        self.next_scrollbar = ttk.Scrollbar(self.next_tree_container, orient=tk.VERTICAL)
        self.next_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add tree with attached scrollbar
        self.next_tree = ttk.Treeview(self.next_tree_container, columns=("File",), show="tree", 
                                     yscrollcommand=self.next_scrollbar.set)
        self.next_tree.column("#0", width=800, minwidth=400, stretch=True)
        self.next_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbar to tree
        self.next_scrollbar.config(command=self.next_tree.yview)
        
        # Tab for Completed PDFs (current session)
        self.completed_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.completed_frame, text="Completed")
        
        self.completed_status_label = ttk.Label(self.completed_frame, text="Number of completed PDFs (this session): 0", font=("Segoe UI", 10))
        self.completed_status_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Create a frame to contain the tree and scrollbar for proper layout
        self.completed_tree_container = ttk.Frame(self.completed_frame)
        self.completed_tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar first (right side)
        self.completed_scrollbar = ttk.Scrollbar(self.completed_tree_container, orient=tk.VERTICAL)
        self.completed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add tree with attached scrollbar
        self.completed_tree = ttk.Treeview(self.completed_tree_container, columns=("File",), show="tree",
                                         yscrollcommand=self.completed_scrollbar.set)
        self.completed_tree.column("#0", width=800, minwidth=400, stretch=True)
        self.completed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbar to tree
        self.completed_scrollbar.config(command=self.completed_tree.yview)
        
        # Tab for Total Completed PDFs (all sessions)
        self.total_completed_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.total_completed_frame, text="Total Completed")
        
        self.total_completed_status_label = ttk.Label(self.total_completed_frame, 
                                                     text="Total number of completed PDFs (all sessions): 0", 
                                                     font=("Segoe UI", 10))
        self.total_completed_status_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Create a frame to contain the tree and scrollbar for proper layout
        self.total_completed_tree_container = ttk.Frame(self.total_completed_frame)
        self.total_completed_tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar first (right side)
        self.total_completed_scrollbar = ttk.Scrollbar(self.total_completed_tree_container, orient=tk.VERTICAL)
        self.total_completed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add tree with attached scrollbar
        self.total_completed_tree = ttk.Treeview(self.total_completed_tree_container, columns=("File",), show="tree",
                                               yscrollcommand=self.total_completed_scrollbar.set)
        self.total_completed_tree.column("#0", width=800, minwidth=400, stretch=True)
        self.total_completed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbar to tree
        self.total_completed_scrollbar.config(command=self.total_completed_tree.yview)
    
    def _create_log_section(self):
        """Create the log output section."""
        # The log frame now goes inside the content_frame instead of directly in the window
        self.log_frame = ttk.Frame(self.content_frame)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add a separator between notebook and log
        self.log_separator = ttk.Separator(self.content_frame, orient="horizontal")
        self.log_separator.pack(fill="x", padx=5, pady=5, before=self.log_frame)
        
        # Add a label for the log section
        # self.log_label = ttk.Label(self.log_frame, text="Log Output:", font=("Segoe UI", 10))
        # self.log_label.pack(fill=tk.X, padx=5, pady=(0, 5), anchor="w")
        
        # Create a frame to contain the text widget and scrollbar
        self.log_text_container = ttk.Frame(self.log_frame)
        self.log_text_container.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar first (right side)
        self.log_scrollbar = ttk.Scrollbar(self.log_text_container, orient=tk.VERTICAL)
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add text widget with attached scrollbar
        self.log_text = tk.Text(self.log_text_container, wrap=tk.WORD, height=10, 
                              yscrollcommand=self.log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbar to text widget
        self.log_scrollbar.config(command=self.log_text.yview)
        
        # Redirect stdout and stderr to log text widget
        sys.stdout = RedirectText(self.log_text)
        sys.stderr = RedirectText(self.log_text)
    
    # Event handlers that call ViewModel methods
    def handle_drop(self, event):
        """Handle drag & drop of folders onto the input tree."""
        dropped_files = self.tk.splitlist(event.data)
        for file in dropped_files:
            if os.path.isdir(file):
                self.viewmodel.add_input_folder(file)
                if file not in self.get_all_tree_items():
                    self.insert_folder(file)
                    message = f"Added folder: {file}\n"
                    print(message)
                    sys.__stdout__.write(message)
        self.update_folder_stats()
    
    def select_input(self):
        """Handle input folder selection dialog."""
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.viewmodel.add_input_folder(folder)
            if folder not in self.get_all_tree_items():
                self.insert_folder(folder)
                message = f"Added folder: {folder}\n"
                print(message)
                sys.__stdout__.write(message)
            self.update_folder_stats()
    
    def remove_input(self):
        """Handle removal of selected folders."""
        selected = self.input_tree.selection()
        if not selected:
            message = "No folder selected to remove.\n"
            print(message)
            sys.__stdout__.write(message)
            return
        
        for node in selected:
            if self.input_tree.parent(node) == "":
                self.viewmodel.remove_input_folder(node)
            self.input_tree.delete(node)
            message = f"Removed folder: {node}\n"
            print(message)
            sys.__stdout__.write(message)
        
        self.update_folder_stats()
    
    def select_output(self):
        """Handle output folder selection dialog."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.viewmodel.set_output_folder(folder)
            self.output_entry.config(state="normal")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            self.output_entry.config(state="readonly")
            sys.__stdout__.write(f"User selected {folder} as output folder.\n")
    
    def start_ocr(self):
        """Handle start OCR button click."""
        if not self.viewmodel.is_running():
            success = self.viewmodel.start_ocr()
            if success:
                self.start_button.config(state=DISABLED)
                self.pause_button.config(state=NORMAL)
                self.resume_button.config(state=DISABLED)
    
    def pause_ocr(self):
        """Handle pause OCR button click."""
        self.viewmodel.pause_ocr()
        self.pause_button.config(state=DISABLED)
        self.resume_button.config(state=NORMAL)
    
    def resume_ocr(self):
        """Handle resume OCR button click."""
        self.viewmodel.resume_ocr()
        self.pause_button.config(state=NORMAL)
        self.resume_button.config(state=DISABLED)
    
    # Callbacks invoked by ViewModel
    def update_status(self, completed, current, next_items, current_index, total):
        """Update the status display based on ViewModel data."""
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
        
        # Update Total Completed tab (global processed PDFs)
        self.total_completed_status_label.config(
            text=f"Total number of completed PDFs (all sessions): {len(self.viewmodel.model.global_processed)}"
        )
        for row in self.total_completed_tree.get_children():
            self.total_completed_tree.delete(row)
        for file in self.viewmodel.model.global_processed:
            self.total_completed_tree.insert("", tk.END, text=file)
        
        # Update folder statistics too, for consistency
        self.update_folder_stats()
        
        # Update button states based on processing status
        if not current and self.viewmodel.is_running() == False:
            self.start_button.config(state=NORMAL)
            self.pause_button.config(state=DISABLED)
            self.resume_button.config(state=DISABLED)
    
    def update_progress(self, progress):
        """Update the progress bar based on ViewModel data."""
        self.progress['value'] = progress
    
    def update_time_stats(self, elapsed_time, estimated_time, current_index, to_be_processed):
        """Update the time statistics display."""
        # Format the times into human-readable strings
        elapsed_str = self.viewmodel.format_time(elapsed_time)
        estimated_str = self.viewmodel.format_time(estimated_time)
        
        # Calculate percentage
        percentage = 0.0
        if to_be_processed > 0:
            percentage = (current_index / to_be_processed) * 100
        
        # Update the detailed status label
        self.detailed_status_label.config(
            text=f"{current_index}/{to_be_processed} PDFs processed [{percentage:.1f}%] - {elapsed_str} passed - estimated time until completion: {estimated_str}"
        )
    
    def update_folder_stats(self):
        """Update the folder statistics display."""
        total, to_be_processed = self.viewmodel.update_folder_stats()
        
        # If OCR is running, we should keep the original to_be_processed value
        if self.viewmodel.is_running():
            to_be_processed = self.viewmodel.to_be_processed_count
            
        self.input_status_label.config(text=f"Total PDFs: {total}, To be processed: {to_be_processed}")
    
    # Helper methods
    def get_all_tree_items(self):
        """Get all items in the input tree."""
        return self.input_tree.get_children()
    
    def has_subfolder(self, folder):
        """Check if a folder has subfolders."""
        try:
            for entry in os.listdir(folder):
                full_path = os.path.join(folder, entry)
                if os.path.isdir(full_path):
                    return True
            return False
        except Exception:
            return False
    
    def insert_folder(self, folder):
        """Insert a folder into the input tree."""
        self.input_tree.insert("", "end", iid=folder, text=folder)
        if self.has_subfolder(folder):
            self.input_tree.insert(folder, "end", text="dummy")
    
    def on_treeview_open(self, event):
        """Handle opening a folder in the treeview."""
        item = self.input_tree.focus()
        children = self.input_tree.get_children(item)
        if children:
            first_child = children[0]
            if self.input_tree.item(first_child, "text") == "dummy":
                self.input_tree.delete(first_child)
                self.load_subfolders(item)
    
    def load_subfolders(self, parent):
        """Load subfolders into the treeview."""
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
            
    def on_closing(self):
        """Handle application closing."""
        # Clean up current session data
        self.viewmodel.cleanup_current_session()
        
        # Restore standard output
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
        # Close the application
        self.destroy()