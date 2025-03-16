import os
import ocrmypdf

def apply_ocr_to_pdf(input_pdf: str, output_pdf: str, use_gpu: bool = False, language: str = "deu+eng", deskew: bool = True, jobs: int = 1) -> None:
    """
    Applies OCR to a PDF file using ocrmypdf and generates a searchable PDF.
    """
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
    except Exception as e:
        print(f"❌ Error processing {input_pdf}: {e}")

def batch_ocr_pdfs(input_dir: str, output_dir: str, use_gpu: bool = False, language: str = "deu+eng", deskew: bool = True, jobs: int = 1, status_file: str = None, pause_event=None, update_status_callback=None) -> None:
    """
    Processes all PDFs in the input_dir, applies OCR, and saves them in the output_dir.
    The directory structure is preserved.
    """
    from status_manager import load_status, save_status
    from progress_display import display_progress

    if status_file is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logs_dir = os.path.join(project_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        status_file = os.path.join(logs_dir, "ocr_status.json")

    processed = load_status(status_file)
    initial_processed_count = len(processed)

    pdf_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                path = os.path.normpath(os.path.abspath(os.path.join(root, file)))
                pdf_files.append(path)
    total = len(pdf_files)

    try:
        for idx, input_pdf in enumerate(pdf_files, start=1):
            # Blockiere hier, falls pausiert
            if pause_event:
                pause_event.wait()

            if input_pdf in processed:
                continue

            # Bestimme den Zielpfad, erstelle nötige Ordner etc.
            relative_dir = os.path.relpath(os.path.dirname(input_pdf), os.path.abspath(input_dir))
            target_dir = os.path.join(output_dir, relative_dir)
            os.makedirs(target_dir, exist_ok=True)
            output_pdf = os.path.join(target_dir, os.path.basename(input_pdf))

            in_progress = input_pdf
            next_items = [pdf for pdf in pdf_files if pdf not in processed and pdf != input_pdf]

            # Aktualisiere den Status über den Callback (GUI-Update)
            if update_status_callback:
                update_status_callback(processed, in_progress, next_items, len(processed), total)
            else:
                display_progress(processed, in_progress, next_items, len(processed), total)

            apply_ocr_to_pdf(input_pdf, output_pdf, use_gpu=use_gpu, language=language, deskew=deskew, jobs=jobs)

            processed.append(input_pdf)
            save_status(status_file, processed)

        if len(processed) == initial_processed_count:
            print("All files in the folder are already processed.\n")

    except KeyboardInterrupt:
        print("\n⏸ Process interrupted. Saving current status...")
        save_status(status_file, processed)
        print("Status saved. You can resume processing later.")
