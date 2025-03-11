# import os
# import time
# from ocr_processing import batch_ocr_pdfs

# if __name__ == "__main__":
#     input_path = r"C:\Users\danie\Desktop\neuocr\Test_ohne_OCR1"   # Directory containing original PDFs
#     output_dir = r"C:\Users\danie\Desktop\neuocr\Test_mit_OCR1"       # Directory for OCR-processed (searchable) PDFs

#     os.makedirs(output_dir, exist_ok=True)
    
#     print("🚀 Starting OCR processing...\n")
#     start_time = time.time()

#     # Apply OCR with pause/resume functionality; parameters are configurable.
#     batch_ocr_pdfs(
#         input_path,
#         output_dir,
#         use_gpu=False,
#         language="deu+eng",
#         deskew=True,
#         jobs=4  # Adjust internal parallelism of ocrmypdf
#     )

#     end_time = time.time()
#     elapsed_time = end_time - start_time
#     print(f"\n✅ OCR-Processing completed in {elapsed_time:.2f} seconds! Searchable PDFs saved.")

from gui import OCRGUI

if __name__ == "__main__":
    app = OCRGUI()
    app.mainloop()
