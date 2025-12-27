# Ship V1 Workflow

## Prerequisites
- Python 3.11 installed
- All OCR PDFs in `court_docs/` (or OCR text already in `data/court_docs_text/`)
- `data/cases.csv` populated

## One-Command Release
```bash
# Step 1: Parse OCR text (if not already done)
python parse_court_docs.py
# Step 2: Audit parsed documents
python audit_court_docs.py
# Step 3: Verify Case Zero contract
python verify_contract.py
# Expected output: "PASS: Case Zero contract verified"
# Step 4: Publish to GitHub Pages
python publish_data.py
# Expected output: "[DONE] N files published to docs/data/"
```

## If all steps exit 0:
```bash
# Commit with single message
git add -A
git commit -m "V1: Case Zero contract verified + docs published"
# Push to trigger GitHub Pages rebuild
git push origin main
```

## Validation
After push, verify:
1. GitHub Actions CI workflow passes (check Actions tab)
2. GitHub Pages site builds (Settings → Pages → shows deployment status)
3. Open https://yourrepo.github.io/docs/ → dashboard loads
4. Dashboard table shows ≥42 rows for 2025-0000424475-GA

## If verify_contract.py fails
Stop and check output. Common causes:
- Missing event code (check `data/court_docs_parsed.csv` for PGII/NOH/POS/OAF/LET)
- Event count < 42 (check row count in parsed CSV)
- Date parsing errors (check `parsed_date_validity_pct` in verify output)
- Duplicate rows > 5 (check audit CSV for exact duplicates)

Fix the issue, re-run step 3, and only proceed to step 4 when `verify_contract.py` exits 0.
