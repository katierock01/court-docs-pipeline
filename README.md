# Court Document OCR/Parse/Audit Pipeline

## Prereqs
- Python 3.8+
- Tesseract + Poppler on PATH (see Windows notes below)
- pip install pytesseract pdf2image pillow tqdm rapidfuzz

## Run
python ocr_extractor.py --input-dir court_docs --output-dir data\court_docs_text --verbose
python parse_court_docs.py
python audit_court_docs.py
python checker.py

Outputs: data\court_docs_ocr_summary.csv, data\ocr_metadata.json, data\court_docs_parsed.csv, data\court_docs_audit.csv
UI: open court-documents.html (reads CSVs from data\).

Audit history: by default, audit_court_docs.py also saves timestamped copies to data\audit_history\; use --no-archive to skip.

Parsed CSV fields now include event_id, document_id (PDF basename), source_view, case_number, filed_date, document_type, parties, event codes/labels, judge, low_confidence, notes. Service proofs map to POS to match events.csv.

## Windows install quick-start
1) Python 3.8+: `python --version`

2) Tesseract OCR  
   - Download: https://github.com/UB-Mannheim/tesseract/wiki  
   - Install to: `C:\Program Files\Tesseract-OCR\` and add to PATH (or pass `--tesseract-cmd` to ocr_extractor.py).

3) Poppler PDF utilities  
   - Download: https://github.com/oschwartz10612/poppler-windows/releases/  
   - Extract to: `C:\Program Files\poppler-24.08.0\`  
   - Add `C:\Program Files\poppler-24.08.0\Library\bin` to PATH, or run OCR with `--poppler-path "C:\Program Files\poppler-24.08.0\Library\bin"`.
   - Example user-local path (already extracted here): `--poppler-path "C:\Users\k8roc\poppler\poppler-24.08.0\Library\bin"`

4) Python packages  
   `pip install pytesseract pdf2image pillow tqdm rapidfuzz`

Verify install: `tesseract --version` and `pdftoppm -v`.
