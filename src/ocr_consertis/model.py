import os
import json
import ocrmypdf
import time
import threading
import concurrent.futures
from typing import List, Callable, Optional, Tuple, Set
from datetime import datetime, timedelta

class OCRModel:
    """Model class handling the OCR processing and status management."""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.logs_dir = os.path.join(self.project_root, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.global_status_file = os.path.join(self.logs_dir, "ocr_status.json")
        self.current_status_file = os.path.join(self.logs_dir, "ocr_status_current.json")
        
        # Initialize empty lists for tracking PDFs
        self.all_pdfs = []
        self.running = False
        self.paused = False
        
        # Load global status (all previously processed PDFs)
        self.global_processed = self.load_status(self.global_status_file)
        
        # Initialize empty current session processed PDFs list
        # This should only contain PDFs processed in the current session
        self.processed_pdfs = []
        
        # Clear the current session file on startup
        self.save_status(self.current_status_file, [])
        
        # Time tracking variables
        self.start_time = None
        self.pause_time = None
        self.total_pause_time = timedelta(0)
        self.processing_times = []  # List to store processing time for each PDF
        
        # Initialize lock for thread safety
        self.lock = threading.Lock()
        
        # Set to track currently processing PDFs
        self.currently_processing: Set[str] = set()
    
    def load_status(self, status_file: str) -> List[str]:
        """Load the list of processed PDFs from a JSON status file."""
        if status_file and os.path.exists(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [os.path.normpath(os.path.abspath(p)) for p in data]
            except Exception as e:
                print(f"Error loading status file: {e}")
        return []
    
    def save_status(self, status_file: str, processed: List[str]) -> None:
        """Save the list of processed PDFs to a JSON status file."""
        try:
            if status_file:
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, indent=4)
        except Exception as e:
            print(f"Error saving status file: {e}")
    
    def update_status_files(self, new_pdf: str) -> None:
        """Update both global and current session status files with a new processed PDF."""
        # Add to current session processed list
        if new_pdf not in self.processed_pdfs:
            self.processed_pdfs.append(new_pdf)
        
        # Add to global processed list
        if new_pdf not in self.global_processed:
            self.global_processed.append(new_pdf)
        
        # Save both status files
        self.save_status(self.global_status_file, self.global_processed)
        self.save_status(self.current_status_file, self.processed_pdfs)
    
    def collect_pdfs(self, input_folders: List[str]) -> List[str]:
        """Collect all PDF files from input folders."""
        pdf_files = []
        for input_dir in input_folders:
            for root, _, files in os.walk(input_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        path = os.path.normpath(os.path.abspath(os.path.join(root, file)))
                        pdf_files.append(path)
        return pdf_files
        
    def get_unprocessed_pdfs(self, input_folders: List[str]) -> List[str]:
        """Collect all unprocessed PDF files from input folders."""
        all_pdfs = self.collect_pdfs(input_folders)
        # Filter out PDFs that have already been processed (in global list)
        return [pdf for pdf in all_pdfs if pdf not in self.global_processed]
    
    def apply_ocr_to_pdf(self, input_pdf: str, output_pdf: str, use_gpu: bool = False, 
                         language: str = "deu+eng", deskew: bool = True, jobs: int = 1) -> bool:
        """Apply OCR to a PDF file and return success status."""
        pdf_start_time = time.time()
        try:
            if use_gpu:
                ocrmypdf.ocr(
                    input_pdf,
                    output_pdf,
                    language=language,
                    force_ocr=True,
                    deskew=deskew,
                    jobs=jobs
                )
            else:
                ocrmypdf.ocr(
                    input_pdf,
                    output_pdf,
                    language=language,
                    skip_text=True,
                    deskew=deskew,
                    jobs=jobs
                )
            print(f"✅ OCR applied: {input_pdf} -> {output_pdf}")
            
            # Record processing time for this PDF
            processing_time = time.time() - pdf_start_time
            self.processing_times.append(processing_time)
            
            return True
        except Exception as e:
            print(f"❌ Error processing {input_pdf}: {e}")
            return False
    
    def is_pdf_in_input_folders(self, pdf_path: str, input_folders: List[str]) -> bool:
        """Check if the given PDF is located in one of the input folders."""
        normalized_pdf = os.path.normpath(os.path.abspath(pdf_path))
        for folder in input_folders:
            normalized_folder = os.path.normpath(os.path.abspath(folder))
            try:
                common = os.path.commonpath([normalized_pdf, normalized_folder])
                if common == normalized_folder:
                    return True
            except ValueError:
                continue
        return False
    
    def get_pdf_count_stats(self, input_folders: List[str]) -> Tuple[int, int]:
        """Calculate total PDFs and PDFs to be processed."""
        all_pdfs = self.collect_pdfs(input_folders)
        total = len(all_pdfs)
        
        # Filter to include only PDFs in the current input folders that have been processed
        relevant_processed = [pdf for pdf in self.global_processed 
                             if self.is_pdf_in_input_folders(pdf, input_folders)]
        processed_count = len(relevant_processed)
        
        to_be_processed = total - processed_count
        return total, to_be_processed
    
    def get_time_stats(self) -> Tuple[float, float, float]:
        """
        Get time statistics for OCR processing.
        
        Returns:
            Tuple containing:
            - elapsed_time: Time elapsed since start in seconds
            - avg_time_per_pdf: Average time per PDF in seconds
            - estimated_time_remaining: Estimated time remaining in seconds
        """
        if not self.start_time:
            return 0, 0, 0
        
        # Calculate elapsed time (accounting for pauses)
        if self.paused and self.pause_time:
            current_time = self.pause_time
        else:
            current_time = datetime.now()
        
        elapsed_time = (current_time - self.start_time - self.total_pause_time).total_seconds()
        
        # Calculate average processing time per PDF
        if self.processing_times:
            avg_time_per_pdf = sum(self.processing_times) / len(self.processing_times)
        elif self.processed_pdfs:
            # Fallback if we don't have detailed processing times
            avg_time_per_pdf = elapsed_time / len(self.processed_pdfs)
        else:
            avg_time_per_pdf = 0
        
        # Calculate estimated time remaining
        if avg_time_per_pdf > 0 and len(self.all_pdfs) > len(self.processed_pdfs):
            remaining_pdfs = len(self.all_pdfs) - len(self.processed_pdfs)
            estimated_time_remaining = remaining_pdfs * avg_time_per_pdf
        else:
            estimated_time_remaining = 0
        
        return elapsed_time, avg_time_per_pdf, estimated_time_remaining
    
    def start_ocr_process(self, input_folders: List[str], output_dir: str, 
                        use_gpu: bool = False, language: str = "deu+eng", 
                        deskew: bool = True, jobs: int = 4,
                        status_callback: Optional[Callable] = None) -> None:
        """Start the OCR process for all PDFs in the input folders with parallel processing."""
        if not input_folders or not output_dir:
            print("Please select at least one input folder and an output folder.")
            return
        
        self.running = True
        self.paused = False
        
        # Reset time tracking
        self.start_time = datetime.now()
        self.pause_time = None
        self.total_pause_time = timedelta(0)
        self.processing_times = []
        
        # Collect all PDFs
        self.all_pdfs = self.collect_pdfs(input_folders)
        
        # Get only unprocessed PDFs
        unprocessed_pdfs = self.get_unprocessed_pdfs(input_folders)
        total = len(self.all_pdfs)
        
        # Set to track currently processing PDFs
        self.currently_processing = set()
        
        # Initial status update to show correct "to be processed" count
        if status_callback:
            in_progress = None
            next_items = unprocessed_pdfs
            status_callback(self.processed_pdfs.copy(), in_progress, next_items, len(self.processed_pdfs), total)
        
        # Process PDFs in parallel using a thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            # Dictionary to map futures to their PDFs
            future_to_pdf = {}
            
            # Initially submit up to 'jobs' number of PDFs for processing
            initial_batch = min(jobs, len(unprocessed_pdfs))
            for i in range(initial_batch):
                if i < len(unprocessed_pdfs):
                    pdf = unprocessed_pdfs[i]
                    # Skip if already processed in current session
                    if pdf in self.processed_pdfs:
                        continue
                        
                    with self.lock:
                        self.currently_processing.add(pdf)
                    
                    future = executor.submit(
                        self._process_single_pdf,
                        pdf, input_folders, output_dir, use_gpu, language, deskew, 1, status_callback, total
                    )
                    future_to_pdf[future] = pdf
            
            # Process completed futures and submit new ones as needed
            submitted_pdfs = set(future_to_pdf.values())
            pdf_index = initial_batch  # Start from the next unsubmitted PDF
            
            # While we have futures running and the process hasn't been stopped
            while future_to_pdf and self.running:
                # Wait for the next future to complete (with a timeout to check running state)
                done, not_done = concurrent.futures.wait(
                    future_to_pdf, 
                    timeout=0.5, 
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                if not self.running:
                    # Cancel all pending futures if we're stopping
                    for future in not_done:
                        future.cancel()
                    break
                
                # For each completed PDF
                for future in done:
                    pdf = future_to_pdf.pop(future)
                    with self.lock:
                        if pdf in self.currently_processing:
                            self.currently_processing.remove(pdf)
                    
                    try:
                        # Get the result and check if processing was successful
                        success = future.result()
                        if success:
                            with self.lock:
                                self.update_status_files(pdf)
                                
                        # Submit a new PDF for processing if available
                        while pdf_index < len(unprocessed_pdfs) and self.running:
                            next_pdf = unprocessed_pdfs[pdf_index]
                            pdf_index += 1
                            
                            # Skip if already processed or being processed
                            if next_pdf in self.processed_pdfs or next_pdf in submitted_pdfs:
                                continue
                                
                            # Submit this PDF for processing
                            with self.lock:
                                self.currently_processing.add(next_pdf)
                            
                            future = executor.submit(
                                self._process_single_pdf,
                                next_pdf, input_folders, output_dir, use_gpu, language, deskew, 1, status_callback, total
                            )
                            future_to_pdf[future] = next_pdf
                            submitted_pdfs.add(next_pdf)
                            break
                            
                    except Exception as e:
                        print(f"❌ Error processing {pdf}: {e}")
            
        # Final update after completion
        self.running = False
        if status_callback:
            status_callback(self.processed_pdfs.copy(), None, [], len(self.processed_pdfs), total)
        
        if len(self.processed_pdfs) == 0:
            print("All files in the folder are already processed.\n")
    
    def _process_single_pdf(self, input_pdf: str, input_folders: List[str], output_dir: str,
                          use_gpu: bool, language: str, deskew: bool, jobs: int,
                          status_callback: Optional[Callable], total: int) -> bool:
        """Process a single PDF file in a separate thread."""
        if not self.running:
            return False
            
        # Handle pausing
        while self.paused:
            time.sleep(0.5)  # Wait while paused
            if not self.running:
                return False
        
        # Determine output path, preserving directory structure
        output_pdf = None
        for input_dir in input_folders:
            if self.is_pdf_in_input_folders(input_pdf, [input_dir]):
                # 1. Get the input folder name
                input_folder_name = os.path.basename(os.path.normpath(input_dir))
                
                # 2. Get the relative path from input folder to PDF file
                relative_path = os.path.relpath(os.path.dirname(input_pdf), os.path.abspath(input_dir))
                
                # 3. Create target directory structure
                if relative_path == '.':
                    # PDF is directly in the input folder
                    target_dir = os.path.join(output_dir, input_folder_name)
                else:
                    # PDF is in a subfolder
                    target_dir = os.path.join(output_dir, input_folder_name, relative_path)
                
                # 4. Create the directory and set the output path
                os.makedirs(target_dir, exist_ok=True)
                output_pdf = os.path.join(target_dir, os.path.basename(input_pdf))
                print(f"Processing: {input_pdf}")
                print(f"Output to: {output_pdf}")
                break
        
        # Use flat structure as fallback if no matching input folder found
        if output_pdf is None:
            output_pdf = os.path.join(output_dir, os.path.basename(input_pdf))
            os.makedirs(output_dir, exist_ok=True)
        
        # Update status via callback
        if status_callback:
            with self.lock:
                in_progress = list(self.currently_processing)
                next_items = [pdf for pdf in self.all_pdfs 
                             if pdf not in self.global_processed 
                             and pdf not in self.processed_pdfs
                             and pdf not in self.currently_processing]
                status_callback(self.processed_pdfs.copy(), in_progress, next_items, len(self.processed_pdfs), total)
        
        # Process current PDF
        success = self.apply_ocr_to_pdf(
            input_pdf, output_pdf, 
            use_gpu=use_gpu, 
            language=language, 
            deskew=deskew, 
            jobs=jobs  # This now refers to the number of threads within a single OCR process
        )
        
        return success
    
    def pause_processing(self) -> None:
        """Pause the OCR processing."""
        if not self.paused:
            self.paused = True
            self.pause_time = datetime.now()
            print("OCR processing paused.\n")
    
    def resume_processing(self) -> None:
        """Resume the OCR processing."""
        if self.paused:
            self.paused = False
            if self.pause_time:
                pause_duration = datetime.now() - self.pause_time
                self.total_pause_time += pause_duration
                self.pause_time = None
            print("OCR processing resumed.\n")
    
    def stop_processing(self) -> None:
        """Stop the OCR processing completely."""
        self.running = False
        self.paused = False
        print("OCR processing stopped.\n")
        
    def cleanup_current_session(self) -> None:
        """Clean up current session data - should be called when the application exits."""
        print("Cleaning up current session data...")
        # Clear the current session file
        self.save_status(self.current_status_file, [])
        self.processed_pdfs = []