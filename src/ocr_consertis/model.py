import os
import json
import ocrmypdf
import time
import threading
import concurrent.futures
from typing import List, Callable, Optional, Tuple, Dict
from datetime import datetime, timedelta

# Importiere die Prozess-Funktion aus separatem Modul
from process_pdf import process_pdf

class OCRModel:
    """Model class handling the OCR processing and status management."""
    
    def __init__(self):
    # Existing code...
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.logs_dir = os.path.join(self.project_root, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.global_status_file = os.path.join(self.logs_dir, "ocr_status.json")
        self.current_status_file = os.path.join(self.logs_dir, "ocr_status_current.json")
        self.failed_status_file = os.path.join(self.logs_dir, "ocr_failed.json")  # New file for failed PDFs
        
        # Neues Flag für Quellüberschreibung
        self.overwrite_source = False
        
        # Initialize empty lists for tracking PDFs
        self.all_pdfs = []
        self.running = False
        self.paused = False
        
        # Load global status (all previously processed PDFs)
        self.global_processed = self.load_status(self.global_status_file)
        
        # Initialize empty current session processed PDFs list
        # This should only contain PDFs processed in the current session
        self.processed_pdfs = []
        
        # Initialize list for failed PDFs
        self.failed_pdfs = self.load_status(self.failed_status_file) or []
        self.current_failed_pdfs = []  # Failed in current session
        
        # Clear the current session file on startup
        self.save_status(self.current_status_file, [])
            
        # Time tracking variables
        self.start_time = None
        self.pause_time = None
        self.total_pause_time = timedelta(0)
        self.processing_times = []  # List to store processing time for each PDF
        
        # Parallel processing variables
        self.in_progress_pdfs = []
        self.processing_lock = threading.Lock()  # Lock for thread-safe operations
    
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
        with self.processing_lock:
            # Add to current session processed list
            if new_pdf not in self.processed_pdfs:
                self.processed_pdfs.append(new_pdf)
            
            # Add to global processed list
            if new_pdf not in self.global_processed:
                self.global_processed.append(new_pdf)
            
            # Save both status files
            self.save_status(self.global_status_file, self.global_processed)
            self.save_status(self.current_status_file, self.processed_pdfs)

    def update_failed_status(self, failed_pdf: str) -> None:
        """Update the failed PDFs list with a new failed PDF."""
        with self.processing_lock:
            # Add to current session failed list
            if failed_pdf not in self.current_failed_pdfs:
                self.current_failed_pdfs.append(failed_pdf)
            
            # Add to global failed list
            if failed_pdf not in self.failed_pdfs:
                self.failed_pdfs.append(failed_pdf)
            
            # Save failed status file
            self.save_status(self.failed_status_file, self.failed_pdfs)
        
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
        # Filter out PDFs that have already been processed or failed (in global lists)
        return [pdf for pdf in all_pdfs if pdf not in self.global_processed and pdf not in self.failed_pdfs]
    
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
            with self.processing_lock:
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
        relevant_failed = [pdf for pdf in self.failed_pdfs
                        if self.is_pdf_in_input_folders(pdf, input_folders)]
        
        processed_count = len(relevant_processed) + len(relevant_failed)
        
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
        with self.processing_lock:
            if self.processing_times:
                avg_time_per_pdf = sum(self.processing_times) / len(self.processing_times)
            elif self.processed_pdfs:
                # Fallback if we don't have detailed processing times
                avg_time_per_pdf = elapsed_time / len(self.processed_pdfs)
            else:
                avg_time_per_pdf = 0
        
        # Calculate estimated time remaining based on remaining PDFs and average time
        # But adjust for parallel processing by dividing by max_workers
        with self.processing_lock:
            remaining_pdfs = len(self.all_pdfs) - len(self.processed_pdfs) - len(self.in_progress_pdfs)
            max_workers = max(len(self.in_progress_pdfs) if self.in_progress_pdfs else 1, 1)
            
        if avg_time_per_pdf > 0 and remaining_pdfs > 0:
            estimated_time_remaining = (remaining_pdfs * avg_time_per_pdf) / max_workers
        else:
            estimated_time_remaining = 0
        
        return elapsed_time, avg_time_per_pdf, estimated_time_remaining
    
    def start_ocr_process(self, input_folders: List[str], output_dir: str, 
                    use_gpu: bool = False, language: str = "deu+eng", 
                    deskew: bool = True, jobs: int = 1,
                    max_workers: int = 2,  # New parameter for parallel processing
                    status_callback: Optional[Callable] = None) -> None:
        """Start the OCR process for all PDFs in the input folders with parallel processing."""
        # Geänderte Prüfung, die overwrite_source berücksichtigt
        if not input_folders:
            print("Please select at least one input folder.")
            return
            
        if not self.overwrite_source and not output_dir:
            print("Please select an output folder or enable 'Overwrite source files'.")
            return
        
        self.running = True
        self.paused = False
        
        # Reset time tracking
        self.start_time = datetime.now()
        self.pause_time = None
        self.total_pause_time = timedelta(0)
        self.processing_times = []
        
        # Reset parallel processing variables
        with self.processing_lock:
            self.in_progress_pdfs = []
        
        # Collect all PDFs
        self.all_pdfs = self.collect_pdfs(input_folders)
        
        # Get only unprocessed PDFs
        unprocessed_pdfs = self.get_unprocessed_pdfs(input_folders)
        total = len(self.all_pdfs)
        
        # Initial status update to show correct "to be processed" count
        if status_callback:
            in_progress_copy = []
            with self.processing_lock:
                in_progress_copy = self.in_progress_pdfs.copy()
            status_callback(self.processed_pdfs.copy(), in_progress_copy, 
                        unprocessed_pdfs, len(self.processed_pdfs), total)
        
        # If no PDFs to process
        if not unprocessed_pdfs:
            print("All files in the folder are already processed.\n")
            self.running = False
            if status_callback:
                status_callback(self.processed_pdfs.copy(), [], [], len(self.processed_pdfs), total)
            return
        
        # Create a thread for parallel processing
        processing_thread = threading.Thread(
            target=self._process_pdfs_parallel,
            args=(unprocessed_pdfs, input_folders, output_dir, use_gpu, language, 
                deskew, jobs, max_workers, status_callback, total)
        )
        processing_thread.daemon = True
        processing_thread.start()
    
    def _determine_output_path(self, input_pdf: str, input_folders: List[str], output_dir: str) -> str:
        """Determine the output path for a PDF."""
        # Wenn Quelldateien überschrieben werden sollen, temporären Pfad erzeugen
        if self.overwrite_source:
            import tempfile
            temp_dir = tempfile.gettempdir()
            return os.path.join(temp_dir, f"temp_{os.path.basename(input_pdf)}")
        
        # Bestehende Logik für normalen Output-Pfad...
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
                break
        
        # Use flat structure as fallback if no matching input folder found
        if output_pdf is None:
            output_pdf = os.path.join(output_dir, os.path.basename(input_pdf))
            os.makedirs(output_dir, exist_ok=True)
        
        return output_pdf
    
    def _process_pdfs_parallel(self, unprocessed_pdfs: List[str], input_folders: List[str], 
                     output_dir: str, use_gpu: bool, language: str, deskew: bool, 
                     jobs: int, max_workers: int, status_callback: Optional[Callable], 
                     total: int) -> None:
        """Process PDFs in parallel using ProcessPoolExecutor."""
        print(f"Starting parallel processing with {max_workers} workers")
        
        # Update max_workers to not exceed available PDFs
        effective_max_workers = min(max_workers, len(unprocessed_pdfs))
        print(f"Effective workers: {effective_max_workers}")
        
        # Erstelle ein Mapping für alle zu verarbeitenden PDFs
        pdf_to_output = {}
        job_params = []
        for input_pdf in unprocessed_pdfs:
            # Skip if already processed
            if input_pdf in self.processed_pdfs or input_pdf in self.global_processed:
                continue
                
            # Determine output path
            output_pdf = self._determine_output_path(input_pdf, input_folders, output_dir)
            pdf_to_output[input_pdf] = output_pdf
            
            # Erstelle Parameter für den Job - füge overwrite_source Flag hinzu
            job_params.append((input_pdf, output_pdf, use_gpu, language, deskew, jobs, self.overwrite_source))
        
        # Erstelle Futures-Dictionary zur Verfolgung der Aufträge
        futures_dict = {}
        
        # Verarbeite mit ProcessPoolExecutor statt ThreadPoolExecutor, 
        # da OCR CPU-intensiv ist und vom GIL beeinträchtigt werden würde
        with concurrent.futures.ProcessPoolExecutor(max_workers=effective_max_workers) as executor:
            
            # Initialisiere futures_dict mit den ersten Aufträgen
            for i in range(min(effective_max_workers, len(job_params))):
                if i < len(job_params):
                    # Verwende die importierte Funktion aus dem separaten Modul
                    future = executor.submit(process_pdf, job_params[i])
                    futures_dict[future] = job_params[i][0]  # input_pdf
                    with self.processing_lock:
                        self.in_progress_pdfs.append(job_params[i][0])
            
            # Verfolge den aktuellen Index für den nächsten zu verarbeitenden Auftrag
            next_job_idx = min(effective_max_workers, len(job_params))
            
            # Melde den initialen Status
            if status_callback:
                with self.processing_lock:
                    in_progress_copy = self.in_progress_pdfs.copy()
                remaining = [p[0] for p in job_params[next_job_idx:]]
                status_callback(
                    self.processed_pdfs.copy(),
                    in_progress_copy,
                    remaining,
                    len(self.processed_pdfs),
                    total
                )
            
            # Hauptschleife: Warte auf Fertigstellung und starte neue Aufträge
            while futures_dict and self.running:
                # Überprüfe, ob Pause aktiv ist
                if self.paused:
                    time.sleep(0.5)
                    continue
                
                # Warte auf Fertigstellung eines Auftrags (nicht aller Aufträge)
                done, not_done = concurrent.futures.wait(
                    futures_dict.keys(), 
                    timeout=0.5,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                # Verarbeite fertige Aufträge
                for future in done:
                    input_pdf, success, processing_time = future.result()
                    
                    # Entferne aus in_progress_pdfs
                    with self.processing_lock:
                        if input_pdf in self.in_progress_pdfs:
                            self.in_progress_pdfs.remove(input_pdf)
                    
                    if success:
                        # Bei Erfolg Datei als verarbeitet markieren
                        self.update_status_files(input_pdf)
                        with self.processing_lock:
                            self.processing_times.append(processing_time)
                    else:
                        # Bei Fehler zur Liste fehlgeschlagener PDFs hinzufügen
                        self.update_failed_status(input_pdf)
                        # Optional: Auch bei Fehlern Verarbeitungszeit speichern, da es Zeit verbraucht hat
                        if processing_time > 0:
                            with self.processing_lock:
                                self.processing_times.append(processing_time)
                    
                    # Entferne aus futures_dict
                    del futures_dict[future]
                    
                    # Starte neuen Auftrag, wenn verfügbar
                    if next_job_idx < len(job_params) and self.running and not self.paused:
                        future = executor.submit(process_pdf, job_params[next_job_idx])
                        futures_dict[future] = job_params[next_job_idx][0]  # input_pdf
                        with self.processing_lock:
                            self.in_progress_pdfs.append(job_params[next_job_idx][0])
                        next_job_idx += 1
                
                # Aktualisiere den Status
                if status_callback and not self.paused:
                    with self.processing_lock:
                        in_progress_copy = self.in_progress_pdfs.copy()
                        failed_copy = self.current_failed_pdfs.copy()
                    remaining = [p[0] for p in job_params[next_job_idx:]]
                    status_callback(
                        self.processed_pdfs.copy(),
                        in_progress_copy,
                        remaining,
                        len(self.processed_pdfs) + len(self.current_failed_pdfs),  # Count both success and failed
                        total
                    )
        
        # Verarbeitung abgeschlossen
        self.running = False
        
        # Letztes Status-Update
        if status_callback:
            status_callback(
                self.processed_pdfs.copy(),
                [],
                [],
                len(self.processed_pdfs),
                total
            )
    
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
        self.current_failed_pdfs = []  # Reset current session failed PDFs
