import sys
import os
import tkinter as tk
from tkinter import filedialog

def select_input(controller):
    folder = filedialog.askdirectory(title="Select Input Folder")
    if folder:
        if folder not in controller.input_folders:
            controller.input_folders.append(folder)
            # Insert the root folder into the tree view
            controller.input_tree.insert("", "end", iid=folder, text=folder)
            # Recursively load and display all subfolders
            load_all_subfolders(controller, folder, folder)
            message = f"Added folder: {folder}\n"
            print(message)
            sys.__stdout__.write(message)
        update_input_folder_status(controller)

def remove_input(controller):
    selected = controller.input_tree.selection()
    if not selected:
        message = "No folder selected to remove.\n"
        print(message)
        sys.__stdout__.write(message)
        return

    for node in selected:
        # Remove only top-level nodes
        if controller.input_tree.parent(node) == "":
            if node in controller.input_folders:
                controller.input_folders.remove(node)
        controller.input_tree.delete(node)
        message = f"Removed folder: {node}\n"
        print(message)
        sys.__stdout__.write(message)

    update_input_folder_status(controller)

def select_output(controller):
    folder = filedialog.askdirectory(title="Select Output Folder")
    if folder:
        controller.output_folder = folder
        controller.output_entry.config(state="normal")
        controller.output_entry.delete(0, tk.END)
        controller.output_entry.insert(0, folder)
        controller.output_entry.config(state="readonly")
        sys.__stdout__.write(f"User selected {folder} as output folder.\n")

def update_input_folder_status(controller):
    """
    Recursively count all PDFs in the added folders (including subfolders)
    and update the singleton's variables as well as the GUI label.
    """
    total = 0
    for folder in controller.input_folders:
        for root, dirs, files in os.walk(folder):
            total += sum(1 for file in files if file.lower().endswith('.pdf'))
    from viewmodel import PdfTrackerSingleton
    tracker = PdfTrackerSingleton()
    tracker.totalPdfs = total
    tracker.pdfsTobeProcessed = total  # (Assuming all PDFs are pending processing.)
    controller.input_status_label.config(text=f"Total PDFs: {total}, To be processed: {total}")

def load_all_subfolders(controller, parent, folder):
    """
    Recursively insert all subfolders of 'folder' under the tree node 'parent'.
    """
    try:
        entries = sorted(os.listdir(folder))
        for entry in entries:
            full_path = os.path.join(folder, entry)
            if os.path.isdir(full_path):
                # Insert subfolder under the current parent node
                controller.input_tree.insert(parent, "end", iid=full_path, text=full_path)
                # Recursively load subfolders of this directory
                load_all_subfolders(controller, full_path, full_path)
    except Exception as e:
        message = f"Error loading subfolders for {folder}: {e}\n"
        print(message)
        sys.__stdout__.write(message)

######################################
# Internal helper functions (unchanged)
######################################
def is_pdf_in_input_folders(controller, pdf_path):
    normalized_pdf = os.path.normpath(os.path.abspath(pdf_path))
    for folder in controller.input_folders:
        normalized_folder = os.path.normpath(os.path.abspath(folder))
        try:
            common = os.path.commonpath([normalized_pdf, normalized_folder])
            if common == normalized_folder:
                return True
        except ValueError:
            continue
    return False

def update_status_table(controller, completed, current, next_items, current_index, total):
    controller.current_label.config(text="Currently Processing: " + (current if current else "None"))
    controller.notebook_section.next_status_label.config(text=f"Number of PDFs to be processed: {len(next_items)}")
    for row in controller.notebook_section.next_tree.get_children():
        controller.notebook_section.next_tree.delete(row)
    for file in next_items:
        controller.notebook_section.next_tree.insert("", tk.END, text=file)
    controller.notebook_section.completed_status_label.config(text=f"Number of completed PDFs: {len(completed)}")
    for row in controller.notebook_section.completed_tree.get_children():
        controller.notebook_section.completed_tree.delete(row)
    for file in completed:
        controller.notebook_section.completed_tree.insert("", tk.END, text=file)

def schedule_update_status(controller, completed, current, next_items, current_index, total):
    controller.after(0, lambda: update_status_table(controller, completed, current, next_items, current_index, total))
