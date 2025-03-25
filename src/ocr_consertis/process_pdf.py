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
        params: Tuple (input_pdf, output_pdf, use_gpu, language, deskew, jobs, overwrite_source, continue_on_error)
    
    Returns:
        Tuple (input_pdf, success, processing_time)
    """
    import shutil
    import os
    import time
    import ocrmypdf
    
    # Unpack parameters, include new continue_on_error flag
    input_pdf, output_pdf, use_gpu, language, deskew, jobs, overwrite_source, continue_on_error = params
    start_time = time.time()
    
    try:
        if use_gpu:
            ocrmypdf.ocr(
                input_pdf,
                output_pdf,
                language=language,
                force_ocr=True,
                deskew=deskew,
                jobs=jobs,
                continue_on_soft_render_error=continue_on_error
            )
        else:
            ocrmypdf.ocr(
                input_pdf,
                output_pdf,
                language=language,
                skip_text=True,
                deskew=deskew,
                jobs=jobs,
                continue_on_soft_render_error=continue_on_error
            )
            
        # Wenn Quelldateien überschrieben werden sollen und Ausgabe erfolgreich war
        if overwrite_source and os.path.exists(output_pdf):
            try:
                # Sicherstellen, dass die Quelldatei nicht schreibgeschützt ist
                if os.access(input_pdf, os.W_OK):
                    # Kopieren der verarbeiteten Datei zurück zur Quelldatei
                    shutil.copy2(output_pdf, input_pdf)
                    print(f"✅ Source file overwritten: {input_pdf}")
                else:
                    print(f"⚠️ Cannot overwrite source file (no write permission): {input_pdf}")
            except Exception as e:
                print(f"⚠️ Error overwriting source file {input_pdf}: {e}")
        
        print(f"✅ OCR applied: {input_pdf} -> {output_pdf}")
        processing_time = time.time() - start_time
        return (input_pdf, True, processing_time)
    except Exception as e:
        print(f"❌ Error processing {input_pdf}: {e}")
        return (input_pdf, False, 0)