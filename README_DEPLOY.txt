Deploy / Merge instructions

Target folder on your machine:
C:\Users\k8roc\Documents\INF6420-FINAL\inf6420-projects\6420-final\

Copy these into that folder:
- 6420final-index.html
- court-documents.html
- casezero-storyboard.html
- timeline-matrix.html
- reform-hub.html
- actions-and-resources.html
- feedback.html
- methods-inf6420.html
- showform.php
- css\6420-final.css
- js\6420-final.js

Video (add later):
- Place your under-1-minute intro video at: media\6420final-intro.mp4
  (The page already references it.)

Report (add when ready):
- Place 6420final-report.docx in the root of the folder.

Court documents workflow (new)
- Place source PDFs in court_docs\
- Run OCR extraction (with progress + quality scores): python ocr_extractor.py --input-dir court_docs --output-dir data\court_docs_text
- Parse text into CSV: python parse_court_docs.py
- Audit parsed docs vs cases: python audit_court_docs.py
- OCR log is written to data\ocr_extractor.log; raw text outputs use the same basename as the PDF
- OCR summary: data\court_docs_ocr_summary.csv; metadata: data\ocr_metadata.json; parsed data: data\court_docs_parsed.csv; audit: data\court_docs_audit.csv
- Dependencies: pip install pytesseract pdf2image pillow tqdm (plus Tesseract + Poppler binaries on PATH)
