import os
import json
import ocrmypdf
import time
import subprocess
import shlex
import tempfile
import sys
import shutil
from typing import List, Callable, Optional, Tuple
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
        
        # GNU Parallel process
        self.parallel_process = None
        self.temp_files = []
        
        # Check if GNU Parallel is installed
        self.has_gnu_parallel = self._check_gnu_parallel()
    
    def _check_gnu_parallel(self) -> bool:
        """Check if GNU Parallel is installed."""
        try:
            result = subprocess.run(
                ["parallel", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=False,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            print("WARNING: GNU Parallel not found. Parallel processing will be disabled.")
            return False
    
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
    
    def _create_output_path(self, input_pdf: str, input_folders: List[str], output_dir: str) -> str:
        """Create the output path for a PDF file, preserving the directory structure."""
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
    
    def _generate_command_file(self, unprocessed_pdfs: List[str], 
                             input_folders: List[str], output_dir: str,
                             use_gpu: bool, language: str, deskew: bool, jobs: int) -> str:
        """
        Generate a file with commands for GNU Parallel to execute.
        Returns the path to the generated command file.
        """
        # Create a temporary file for the commands
        fd, command_file = tempfile.mkstemp(suffix='.txt', prefix='ocr_commands_')
        self.temp_files.append(command_file)
        
        with os.fdopen(fd, 'w') as f:
            for pdf in unprocessed_pdfs:
                # Generate the output path for this PDF
                output_pdf = self._create_output_path(pdf, input_folders, output_dir)
                
                # Build the ocrmypdf command
                cmd = ["ocrmypdf"]
                
                if use_gpu:
                    cmd.extend(["--force-ocr"])
                else:
                    cmd.extend(["--skip-text"])
                
                cmd.extend([f"--language={language}"])
                
                if deskew:
                    cmd.extend(["--deskew"])
                
                cmd.extend([f"--jobs={jobs}", shlex.quote(pdf), shlex.quote(output_pdf)])
                
                # Write the command to the file
                f.write(" ".join(cmd) + "\n")
        
        return command_file
    
    def _monitor_parallel_process(self, status_callback: Optional[Callable], 
                                total_pdfs: int) -> None:
        """Monitor the GNU Parallel process and update status."""
        # Create a temporary directory for tracking processed files
        temp_dir = tempfile.mkdtemp(prefix='ocr_progress_')
        self.temp_files.append(temp_dir)
        
        # Dictionary to track start time of each PDF
        processing_start_times = {}
        
        while self.running and self.parallel_process is not None:
            if self.paused:
                time.sleep(0.5)
                continue
                
            # Check if parallel process is still running
            if self.parallel_process.poll() is not None:
                # Process has finished
                self.running = False
                break
            
            # Get list of processed PDFs by scanning the temp directory
            processed_files = os.listdir(temp_dir)
            newly_processed = []
            
            for filename in processed_files:
                if filename.endswith(".done"):
                    pdf_path = filename[:-5]  # Remove .done suffix
                    if pdf_path not in self.processed_pdfs:
                        newly_processed.append(pdf_path)
                        self.update_status_files(pdf_path)
                        
                        # Calculate processing time
                        if pdf_path in processing_start_times:
                            processing_time = time.time() - processing_start_times[pdf_path]
                            self.processing_times.append(processing_time)
                            del processing_start_times[pdf_path]
            
            # Check the temp directory for .start files to track currently processing PDFs
            in_progress = []
            for filename in os.listdir(temp_dir):
                if filename.endswith(".start") and not os.path.exists(os.path.join(temp_dir, filename[:-6] + ".done")):
                    pdf_path = filename[:-6]  # Remove .start suffix
                    in_progress.append(pdf_path)
                    
                    # Record start time if not already tracked
                    if pdf_path not in processing_start_times:
                        processing_start_times[pdf_path] = time.time()
            
            # Get list of PDFs still to be processed
            next_items = [pdf for pdf in self.all_pdfs 
                         if pdf not in self.global_processed 
                         and pdf not in self.processed_pdfs
                         and pdf not in in_progress]
            
            # Call status callback
            if status_callback:
                status_callback(self.processed_pdfs.copy(), in_progress, next_items, 
                              len(self.processed_pdfs), total_pdfs)
            
            time.sleep(1)  # Check every second
        
        # Final status update
        if status_callback:
            status_callback(self.processed_pdfs.copy(), None, [], 
                          len(self.processed_pdfs), total_pdfs)
        
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
            self.temp_files.remove(temp_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temp directory: {e}")
    
    def start_ocr_process(self, input_folders: List[str], output_dir: str, 
                        use_gpu: bool = False, language: str = "deu+eng", 
                        deskew: bool = True, jobs: int = 4,
                        status_callback: Optional[Callable] = None) -> None:
        """Start the OCR process for all PDFs in the input folders."""
        if not input_folders or not output_dir:
            print("Please select at least one input folder and an output folder.")
            return
        
        if not self.has_gnu_parallel:
            print("GNU Parallel is not installed. Please install it to enable parallel processing.")
            print("Falling back to sequential processing...")
            # Fall back to the original sequential processing method
            self._start_sequential_ocr(input_folders, output_dir, use_gpu, language, deskew, 1, status_callback)
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
        if not unprocessed_pdfs:
            print("All files in the folder are already processed.\n")
            self.running = False
            if status_callback:
                status_callback([], None, [], 0, len(self.all_pdfs))
            return
        
        total = len(self.all_pdfs)
        
        # Create a temporary directory for tracking processed files
        temp_dir = tempfile.mkdtemp(prefix='ocr_progress_')
        self.temp_files.append(temp_dir)
        
        # Generate command file for GNU Parallel
        command_file = self._generate_command_file(
            unprocessed_pdfs, input_folders, output_dir,
            use_gpu, language, deskew, 1  # Use 1 thread per PDF as GNU Parallel handles distribution
        )
        
        # Build GNU Parallel command
        cmd = [
            "parallel", 
            "--tag",  # Prefix output with filename
            f"-j{jobs}",  # Number of parallel jobs
            "--joblog", f"{temp_dir}/parallel.log",  # Log file
            "--tee", f"{temp_dir}/progress.log",  # Log progress
            # Create a .start file when a job starts
            "--tmpdir", temp_dir,
            "--files",  # Create temporary files for each job
            "--eta",  # Show ETA
            # The following ensures we create marker files for tracking progress
            "--before", f"touch {temp_dir}/{{#}}.start", 
            "--after", f"touch {temp_dir}/{{#}}.done", 
            # Read commands from file
            "--arg-file", command_file
        ]
        
        print(f"Starting parallel OCR processing with {jobs} concurrent jobs...")
        print(f"Command: {' '.join(cmd)}")
        
        # Start GNU Parallel process
        try:
            self.parallel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Start a thread to read stdout in real-time
            import threading
            def read_output():
                for line in self.parallel_process.stdout:
                    print(line.strip())
            
            stdout_thread = threading.Thread(target=read_output, daemon=True)
            stdout_thread.start()
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_parallel_process,
                args=(status_callback, total),
                daemon=True
            )
            monitor_thread.start()
            
        except Exception as e:
            print(f"Error starting GNU Parallel process: {e}")
            self.running = False
            if status_callback:
                status_callback([], None, unprocessed_pdfs, 0, total)
                
            # Clean up temp files
            self._cleanup_temp_files()
    
    def _start_sequential_ocr(self, input_folders: List[str], output_dir: str, 
                            use_gpu: bool = False, language: str = "deu+eng", 
                            deskew: bool = True, jobs: int = 1,
                            status_callback: Optional[Callable] = None):
        """Fall back to sequential processing if GNU Parallel is not available."""
        # Original sequential method implementation
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
        
        # Initial status update to show correct "to be processed" count
        if status_callback:
            in_progress = None
            next_items = unprocessed_pdfs
            status_callback(self.processed_pdfs.copy(), in_progress, next_items, len(self.processed_pdfs), total)
        
        # Process each PDF from unprocessed list
        for idx, input_pdf in enumerate(unprocessed_pdfs, start=1):
            if not self.running:
                break
                
            while self.paused:
                time.sleep(0.5)  # Wait while paused
                if not self.running:
                    break
            
            # Skip if already processed in current session
            if input_pdf in self.processed_pdfs:
                continue
            
            # Determine output path using helper method
            output_pdf = self._create_output_path(input_pdf, input_folders, output_dir)
            
            # Prepare status data for callback
            in_progress = input_pdf
            # next_items should exclude ALL previously processed PDFs, not just from current session
            next_items = [pdf for pdf in self.all_pdfs 
                         if pdf not in self.global_processed 
                         and pdf not in self.processed_pdfs
                         and pdf != input_pdf]
            
            # Update status via callback
            if status_callback:
                status_callback(self.processed_pdfs.copy(), in_progress, next_items, len(self.processed_pdfs), total)
            
            # Process current PDF
            success = self.apply_ocr_to_pdf(
                input_pdf, output_pdf, 
                use_gpu=use_gpu, 
                language=language, 
                deskew=deskew, 
                jobs=jobs
            )
            
            if success:
                # Update status files
                self.update_status_files(input_pdf)
        
        # Final update after completion
        self.running = False
        if status_callback:
            status_callback(self.processed_pdfs.copy(), None, [], len(self.processed_pdfs), total)
        
        if len(self.processed_pdfs) == 0:
            print("All files in the folder are already processed.\n")
    
    def pause_processing(self) -> None:
        """Pause the OCR processing."""
        if not self.paused:
            self.paused = True
            self.pause_time = datetime.now()
            print("OCR processing paused.\n")
            
            # If using GNU Parallel, pause the process by sending SIGSTOP
            if self.parallel_process is not None and self.parallel_process.poll() is None:
                if sys.platform != 'win32':  # SIGSTOP not available on Windows
                    try:
                        # Send SIGSTOP to the process group
                        import signal
                        os.killpg(os.getpgid(self.parallel_process.pid), signal.SIGSTOP)
                        print("Sent SIGSTOP to GNU Parallel process.")
                    except Exception as e:
                        print(f"Failed to pause GNU Parallel process: {e}")
                else:
                    print("Process pausing not supported on Windows. Processes will continue running.")
    
    def resume_processing(self) -> None:
        """Resume the OCR processing."""
        if self.paused:
            self.paused = False
            if self.pause_time:
                pause_duration = datetime.now() - self.pause_time
                self.total_pause_time += pause_duration
                self.pause_time = None
            print("OCR processing resumed.\n")
            
            # If using GNU Parallel, resume the process by sending SIGCONT
            if self.parallel_process is not None and self.parallel_process.poll() is None:
                if sys.platform != 'win32':  # SIGCONT not available on Windows
                    try:
                        # Send SIGCONT to the process group
                        import signal
                        os.killpg(os.getpgid(self.parallel_process.pid), signal.SIGCONT)
                        print("Sent SIGCONT to GNU Parallel process.")
                    except Exception as e:
                        print(f"Failed to resume GNU Parallel process: {e}")
    
    def stop_processing(self) -> None:
        """Stop the OCR processing completely."""
        self.running = False
        self.paused = False
        print("OCR processing stopped.\n")
        
        # If using GNU Parallel, terminate the process
        if self.parallel_process is not None and self.parallel_process.poll() is None:
            try:
                self.parallel_process.terminate()
                print("Terminated GNU Parallel process.")
            except Exception as e:
                print(f"Failed to terminate GNU Parallel process: {e}")
        
        # Clean up temp files
        self._cleanup_temp_files()
    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files created for GNU Parallel."""
        for temp_file in self.temp_files:
            try:
                if os.path.isdir(temp_file):
                    shutil.rmtree(temp_file)
                elif os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Warning: Could not clean up temp file {temp_file}: {e}")
        
        self.temp_files = []
        
    def cleanup_current_session(self) -> None:
        """Clean up current session data - should be called when the application exits."""
        print("Cleaning up current session data...")
        # Stop any running processes
        self.stop_processing()
        
        # Clear the current session file
        self.save_status(self.current_status_file, [])
        self.processed_pdfs = []