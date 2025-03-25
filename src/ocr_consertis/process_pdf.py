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
        params: Tuple (input_pdf, output_pdf, use_gpu, language, deskew, jobs, 
                overwrite_source, continue_on_error, ocr_mode)
    
    Returns:
        Tuple (input_pdf, success, processing_time)
    """
    import shutil
    import os
    import time
    import ocrmypdf
    
    # Neue Parameter auspacken
    input_pdf, output_pdf, use_gpu, language, deskew, jobs, overwrite_source, continue_on_error, ocr_mode = params
    start_time = time.time()
    
    try:
        # Basis-OCR-Optionen
        ocr_options = {
            "language": language,
            "deskew": deskew,
            "jobs": jobs,
            "continue_on_soft_render_error": continue_on_error
        }
        
        # OCR-Modus-spezifische Optionen
        if ocr_mode == "auto":
            ocr_options["skip_text"] = True
        elif ocr_mode == "force":
            ocr_options["force_ocr"] = True
        elif ocr_mode == "redo":
            ocr_options["redo_ocr"] = True
        
        # GPU-spezifische Optionen, falls notwendig
        if use_gpu:
            # Bei GPU-Nutzung force_ocr immer aktivieren
            if ocr_mode != "redo":  # Redo-Modus mit force_ocr ist inkompatibel
                ocr_options["force_ocr"] = True
        
        # OCR ausführen mit den dynamisch erstellten Optionen
        ocrmypdf.ocr(input_pdf, output_pdf, **ocr_options)
            
        # Wenn Quelldateien überschrieben werden sollen und Ausgabe erfolgreich war
        if overwrite_source and os.path.exists(output_pdf):
            try:
                # Sicherstellen, dass die Quelldatei nicht schreibgeschützt ist
                if os.access(input_pdf, os.W_OK):
                    # Kopieren der verarbeiteten Datei zurück zur Quelldatei
                    shutil.copy2(output_pdf, input_pdf)
                    print(f"✅ Source file overwritten: {input_pdf}")
                    
                    # Temporäre Datei nach dem Kopieren löschen
                    try:
                        os.remove(output_pdf)
                        print(f"✅ Temporary file deleted: {output_pdf}")
                    except Exception as e:
                        print(f"⚠️ Could not delete temporary file {output_pdf}: {e}")
                else:
                    print(f"⚠️ Cannot overwrite source file (no write permission): {input_pdf}")
            except Exception as e:
                print(f"⚠️ Error overwriting source file {input_pdf}: {e}")
        
        print(f"✅ OCR applied ({ocr_mode} mode): {input_pdf} -> {output_pdf}")
        processing_time = time.time() - start_time
        return (input_pdf, True, processing_time)
    except Exception as e:
        print(f"❌ Error processing {input_pdf}: {e}")
        return (input_pdf, False, 0)