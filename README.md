# Court Document OCR/Parse/Audit Pipeline

## Prereqs
- Python 3.8+
- Tesseract + Poppler on PATH
- pip install pytesseract pdf2image pillow tqdm rapidfuzz

## Run
python ocr_extractor.py --input-dir court_docs --output-dir data\court_docs_text --verbose
python parse_court_docs.py
python audit_court_docs.py
python checker.py

Outputs: data\court_docs_ocr_summary.csv, data\ocr_metadata.json, data\court_docs_parsed.csv, data\court_docs_audit.csv
UI: open court-documents.html (reads CSVs from data\).
