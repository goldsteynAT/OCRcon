<h1 align="center">OCRcon</h1>
<p align="center"><em>Connect. Control. Convert.</em></p>

---

## Overview

**OCRcon** is a Python-based utility that converts scanned PDFs into searchable documents **while preserving layout and formatting**.

Designed for efficiency and ease of use, OCRcon offers:

- Drag-and-drop interface  
- Parallel processing  
- Real-time progress tracking  

It's ideal for teams and organizations managing large sets of documents. 
The tool maintains folder structures and provides detailed statistics to optimize your document workflows.

---

## Features

- Multi-folder batch processing (structure preserved)  
- Parallel execution for faster results  
- Real-time progress monitoring with time estimates  
- Pause and resume long-running jobs  
- Option to overwrite source files  
- Logging and status tracking across sessions  
- Multilingual OCR (default: **German** & **English**)  
- CPU & GPU processing support  

---

## User Interface Preview

Here's a quick look at the OCRcon GUI in action:

<p align="center">
  <img src="https://github.com/goldsteynAT/OCRcon/blob/dev/logs/OCRcon_preview_schlagschatten_ws.png" alt="OCRcon GUI Preview" width="500">
</p>

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/goldsteynAT/OCRcon.git
   cd OCRcon
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Add Python Scripts folder to your system PATH:
   ```text
   # Replace USERNAME with your Windows username
   C:\Users\USERNAME\AppData\Roaming\Python\Python312\Scripts
   ```

4. Install Tesseract OCR:
   ```text
   # Download from:
   # https://github.com/UB-Mannheim/tesseract/wiki
   ```

5. Install Ghostscript:
   ```text
   # Download from:
   # https://www.ghostscript.com/releases/gsdnld.html
   # Then add to PATH:
   C:\Program Files\gs\gs10.05.0\bin
   ```
