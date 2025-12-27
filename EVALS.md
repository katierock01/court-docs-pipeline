# Case Zero V1 Evaluation Checklist

## ✅ Contract Verification (Must Pass Before Merge)
### Pipeline Artifacts
- [ ] `data/court_docs_parsed.csv` exists and contains ≥42 events for case `2025-0000424475-GA`
- [ ] `data/court_docs_audit.csv` exists
- [ ] `data/parse_report.json` valid JSON format

### Event Code Coverage (Required)
Case Zero (`2025-0000424475-GA`) must include at least one occurrence of each:
- [ ] `PGII` — Petition filed
- [ ] `NOH` — Notice of hearing
- [ ] `POS` — Proof of service
- [ ] `OAF` — Order appointing fiduciary
- [ ] `LET` — Letters of authority

### Data Quality (verify_contract gates)
- [ ] Date validity: ≥95% of filed_date values parse successfully
- [ ] Duplicate rows: ≤5 rows with identical (case_number, document_type, filed_date)
- [ ] Case Zero events: ≥42 rows in parsed CSV

### Execution Proof (CI)
- [ ] `python parse_court_docs.py` exits 0
- [ ] `python audit_court_docs.py` exits 0
- [ ] `python verify_contract.py` exits 0 ("PASS: Case Zero contract verified")

---

## 🎨 UI/UX Alignment (Publish Requirements)
### docs/index.html
- [ ] Skip link present (`<a href="#main" class="skip-link">`)
- [ ] Script tag: `<script src="js/6420-final.js" defer></script>`
- [ ] Header branding matches dashboard:
  - Title: "Oakland Guardianship Navigator"
  - Subtitle: "INF 6420 Final — Katie Rock — fn9575@wayne.edu"
  - Badge: "Automated Parse → Audit → Verify"
- [ ] Nav has `aria-label="Site navigation"`
- [ ] Main has `aria-labelledby="page-title"` + h2 `id="page-title"`
- [ ] aria-current="page" on Home link

### docs/dashboard.html
- [ ] All filters load without console errors
- [ ] Parsed documents table renders if data/court_docs_parsed.csv present
- [ ] Audit list renders if data/court_docs_audit.csv present
- [ ] Parser health section loads parse_report.json stats

### docs/ Assets
- [ ] `docs/css/6420-final.css` synced from repo root
- [ ] `docs/js/6420-final.js` synced from repo root
- [ ] `docs/data/court_docs_parsed.csv` published by publish_data.py
- [ ] `docs/data/court_docs_audit.csv` published by publish_data.py
- [ ] `docs/data/parse_report.json` published by publish_data.py

---

## 📊 Manual Spot Checks (Before Release)
1. **Local pipeline run:**
   ```bash
   python parse_court_docs.py
   python audit_court_docs.py
   python verify_contract.py
   python publish_data.py
   ```
   Verify:
   - No errors in stdout/stderr
   - All 3 artifacts appear in `docs/data/`
2. **Dashboard navigation:**
   - Click Home → Menu toggle closes
   - Click Dashboard → Menu toggle closes
   - No 404s for CSS/JS in browser console
3. **Data integrity:**
   - Open `docs/data/court_docs_parsed.csv` in text editor
   - Search for `2025-0000424475-GA`: should find ≥42 rows
   - Search for `PGII,NOH,POS,OAF,LET`: all 5 codes present
4. **Audit quality:**
   - Open `docs/data/court_docs_audit.csv`
   - If no issues: file is valid, just empty or minimal
   - If issues: all rows have type, case_id, detail

---

## 🚀 Release Gate
**Approval criteria:**
- ✅ All boxes above checked
- ✅ verify_contract.py exit 0
- ✅ No broken links in docs/
- ✅ GitHub Pages renders without errors

**Blockers:**
- ❌ verify_contract.py exit ≠ 0
- ❌ Missing required event codes
- ❌ Event count < 42
- ❌ Audit artifact missing
- ❌ docs/index.html or docs/dashboard.html broken navigation
