"""
Modul für die OCR-Verarbeitung von PDFs.
Diese Funktionen werden als separate Prozesse ausgeführt über ProcessPoolExecutor.
"""

import ocrmypdf
import time

def process_pdf(params):
    """
    Verarbeitet ein einzelnes PDF-Dokument mit OCR.
    
    Args:
        params: Tuple (input_pdf, output_pdf, use_gpu, language, deskew, jobs)
    
    Returns:
        Tuple (input_pdf, success, processing_time)
    """
    input_pdf, output_pdf, use_gpu, language, deskew, jobs = params
    start_time = time.time()
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
        processing_time = time.time() - start_time
        return (input_pdf, True, processing_time)
    except Exception as e:
        print(f"❌ Error processing {input_pdf}: {e}")
        return (input_pdf, False, 0)