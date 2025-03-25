import threading
from typing import List, Callable, Optional, Tuple
from model import OCRModel
import time
import os

class OCRViewModel:
    """Singleton ViewModel that mediates between View and Model for the OCR application."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCRViewModel, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if OCRViewModel._initialized:
            return
            
        self.model = OCRModel()
        self.input_folders = []
        self.output_folder = ""
        self.use_gpu = False
        self.language = "deu+eng"
        self.deskew = True
        self.jobs = 4
        self.max_workers = 2  # Default parallel workers
        self.overwrite_source = False  # Neues Flag für Quellüberschreibung
        
        # Thread for OCR processing
        self.ocr_thread = None
        
        # Status subscribers (callbacks from view)
        self.status_subscribers = []
        self.progress_subscribers = []
        self.time_subscribers = []
        
        # Timer thread for updating time display
        self.timer_thread = None
        self.timer_running = False
        
        # Static count of PDFs to be processed (set when OCR starts)
        self.to_be_processed_count = 0
        
        OCRViewModel._initialized = True

    def set_overwrite_source(self, overwrite: bool) -> None:
        """Set whether to overwrite source files."""
        self.overwrite_source = overwrite
        self.model.overwrite_source = overwrite
        if overwrite:
            print("Source file overwrite mode enabled. Original PDFs will be replaced.")
        else:
            print("Source file overwrite mode disabled. PDFs will be saved to output folder.")
    
    def add_status_subscriber(self, callback: Callable) -> None:
        """Register a callback function to receive status updates."""
        if callback not in self.status_subscribers:
            self.status_subscribers.append(callback)
    
    def add_progress_subscriber(self, callback: Callable) -> None:
        """Register a callback function to receive progress updates."""
        if callback not in self.progress_subscribers:
            self.progress_subscribers.append(callback)
    
    def add_time_subscriber(self, callback: Callable) -> None:
        """Register a callback function to receive time updates."""
        if callback not in self.time_subscribers:
            self.time_subscribers.append(callback)
    
    def remove_subscriber(self, callback: Callable) -> None:
        """Remove a registered callback."""
        if callback in self.status_subscribers:
            self.status_subscribers.remove(callback)
        if callback in self.progress_subscribers:
            self.progress_subscribers.remove(callback)
        if callback in self.time_subscribers:
            self.time_subscribers.remove(callback)
    
    def notify_status_update(self, completed: List[str], current: List[str], 
                            next_items: List[str], current_index: int, total: int) -> None:
        """Notify all subscribers about a status update."""
        for callback in self.status_subscribers:
            callback(completed, current, next_items, current_index, total)
    
    def notify_progress_update(self, progress: float) -> None:
        """Notify all subscribers about a progress update."""
        for callback in self.progress_subscribers:
            callback(progress)
    
    def notify_time_update(self, elapsed_time: float, 
                          estimated_time: float, 
                          current_index: int, 
                          total: int) -> None:
        """Notify all subscribers about a time update."""
        for callback in self.time_subscribers:
            callback(elapsed_time, estimated_time, current_index, self.to_be_processed_count)
    
    def format_time(self, seconds: float) -> str:
        """Format seconds into a human-readable time string (HH:MM:SS)."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def add_input_folder(self, folder: str) -> None:
        """Add a folder to the list of input folders."""
        if folder and folder not in self.input_folders:
            self.input_folders.append(folder)
            # Update folder statistics
            self.update_folder_stats()
    
    def remove_input_folder(self, folder: str) -> None:
        """Remove a folder from the list of input folders."""
        if folder and folder in self.input_folders:
            self.input_folders.remove(folder)
            # Update folder statistics
            self.update_folder_stats()
    
    def set_output_folder(self, folder: str) -> None:
        """Set the output folder."""
        if folder:
            self.output_folder = folder
    
    def update_folder_stats(self) -> Tuple[int, int]:
        """Update and return statistics for the input folders."""
        total, to_be_processed = self.model.get_pdf_count_stats(self.input_folders)
        return total, to_be_processed
    
    def is_pdf_in_input_folders(self, pdf_path: str) -> bool:
        """Check if a PDF is in one of the input folders."""
        return self.model.is_pdf_in_input_folders(pdf_path, self.input_folders)
    
    def start_ocr(self) -> bool:
        """Start the OCR process."""
        if not self.input_folders:
            print("Please select at least one input folder.")
            return False
            
        # Bei aktivierter Quellüberschreibung ist kein Output-Ordner erforderlich
        if not self.overwrite_source and not self.output_folder:
            print("Please select an output folder or enable 'Overwrite source files'.")
            return False
        
        if self.ocr_thread and self.ocr_thread.is_alive():
            print("OCR process is already running.")
            return False
            
        # Store the initial "to be processed" count
        total, to_be_processed = self.update_folder_stats()
        self.to_be_processed_count = to_be_processed
        
        print(f"Starting OCR process: {to_be_processed} files to process out of {total} total files")
        print(f"Using {self.max_workers} parallel workers")
        
        # Start OCR in a separate thread
        self.ocr_thread = threading.Thread(
            target=self._run_ocr_process,
            daemon=True
        )
        self.ocr_thread.start()
        
        # Start the timer thread for updating time information
        self.timer_running = True
        self.timer_thread = threading.Thread(
            target=self._run_timer,
            daemon=True
        )
        self.timer_thread.start()
        
        return True
    
    def _run_timer(self) -> None:
        """Run a timer to update time information periodically."""
        while self.timer_running and self.model.running:
            # Get time statistics from the model
            elapsed_time, _, estimated_time = self.model.get_time_stats()
            
            # Notify subscribers with time information
            self.notify_time_update(
                elapsed_time,
                estimated_time,
                len(self.model.processed_pdfs),
                self.to_be_processed_count  # Use the static count
            )
            
            # Sleep for a short period before updating again
            time.sleep(1)
    
    def _run_ocr_process(self) -> None:
        """Run the OCR process in a thread."""
        def status_callback(completed, current, next_items, current_index, total):
            # Calculate progress percentage (current_index now includes failed PDFs)
            progress = (current_index / total * 100) if total > 0 else 0
            # Notify about status update
            self.notify_status_update(completed, current, next_items, current_index, total)
            # Notify about progress update
            self.notify_progress_update(progress)
            
            # Get time statistics and notify
            elapsed_time, _, estimated_time = self.model.get_time_stats()
            self.notify_time_update(elapsed_time, estimated_time, current_index, total)
        
        self.model.start_ocr_process(
            input_folders=self.input_folders,
            output_dir=self.output_folder,
            use_gpu=self.use_gpu,
            language=self.language,
            deskew=self.deskew,
            jobs=self.jobs,
            max_workers=self.max_workers,  # Pass the parallelism parameter
            status_callback=status_callback
        )
        
        # Stop the timer when OCR processing is done
        self.timer_running = False
    
    def pause_ocr(self) -> None:
        """Pause the OCR process."""
        self.model.pause_processing()
    
    def resume_ocr(self) -> None:
        """Resume the OCR process."""
        self.model.resume_processing()
    
    def stop_ocr(self) -> None:
        """Stop the OCR process."""
        self.model.stop_processing()
        self.timer_running = False
    
    def is_running(self) -> bool:
        """Check if OCR processing is running."""
        return self.model.running
    
    def is_paused(self) -> bool:
        """Check if OCR processing is paused."""
        return self.model.paused
        
    def cleanup_current_session(self) -> None:
        """Clean up current session data."""
        self.timer_running = False
        self.model.cleanup_current_session()