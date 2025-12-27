#!/usr/bin/env python3
"""
Publish pipeline artifacts from data/ to docs/data for GitHub Pages.
Standard library only; plain-text logging.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

SOURCE_DIR = Path("data")
DEST_DIR = Path("docs") / "data"
DOCS_ROOT = Path("docs")

# Files that must exist for the site to function
CRITICAL_FILES = [
    "court_docs_parsed.csv",
]

# Files that enhance the site but are optional
OPTIONAL_FILES = [
    "court_docs_audit.csv",
    "audit_results.json",
    "parse_report.json",
    "unknown_event_types.csv",
]

# Pages to copy (source -> destination) to ensure GitHub Pages has the HTML entry points.
PAGES_TO_COPY = [
    (Path("court-documents.html"), DOCS_ROOT / "dashboard.html"),
]


def generate_index_html(target_dir: Path) -> None:
    """Generate a branded landing page for GitHub Pages."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oakland Guardianship Navigator | Pipeline</title>
    <link rel="stylesheet" href="css/6420-final.css">
    <style>
        :root {
          --brand-navy: #003366;
          --brand-coral: #FF7F50;
          --brand-baby-blue: #89CFF0;
          --bg: #f4f4f9;
          --text: #333;
        }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; background: var(--bg); color: var(--text); }
        .navbar { background: var(--brand-navy); color: white; padding: 1.5rem 2rem; border-bottom: 5px solid var(--brand-coral); display: flex; justify-content: space-between; align-items: center; }
        .navbar h1 { margin: 0; font-size: 1.4rem; }
        .navbar .sub-brand { color: var(--brand-baby-blue); font-size: 0.9rem; }
        .navbar a { color: white; text-decoration: none; font-weight: bold; border: 1px solid var(--brand-baby-blue); padding: 6px 10px; border-radius: 4px; }
        .navbar a:hover { background: var(--brand-coral); border-color: var(--brand-coral); }
        .container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; padding: 1.5rem; margin-bottom: 1.5rem; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 5px solid var(--brand-baby-blue); }
        .card h2 { margin-top: 0; color: var(--brand-navy); border-bottom: 1px solid #eee; padding-bottom: 0.5rem; }
        .metric-box { display: flex; justify-content: space-between; margin-bottom: 0.6rem; font-size: 1.05rem; }
        .metric-value { font-weight: bold; color: var(--brand-navy); }
        .btn { display: inline-block; padding: 0.6rem 1.2rem; background: var(--brand-navy); color: white; text-decoration: none; border-radius: 4px; font-weight: 700; }
        .btn:hover { background: var(--brand-coral); }
        ul.clean { list-style: none; padding: 0; }
        ul.clean li { margin: 0.35rem 0; }
    </style>
</head>
<body>
    <div class="navbar">
      <div>
        <h1>Oakland Guardianship Navigator</h1>
        <div class="sub-brand">INF 6420 Final — Katie Rock — fn9575@wayne.edu</div>
      </div>
      <div>
        <a href="https://github.com/katierock01/court-docs-pipeline" target="_blank">View Repo ↗</a>
      </div>
    </div>

    <div class="container">
      <div class="card">
        <h2>Pipeline Status</h2>
        <div id="metrics">Loading metrics...</div>
        <p style="margin-top: 1rem; font-size: 0.85rem; color: #666;">
          Agent: Builder | Last Build: <span id="build-date">Just now</span>
        </p>
      </div>

      <div class="card">
        <h2>Data Artifacts</h2>
        <p>Access the raw data processed by the pipeline:</p>
        <ul class="clean">
          <li><a href="data/court_docs_parsed.csv" class="btn">⬇️ Download Parsed CSV</a></li>
          <li><a href="dashboard.html" class="btn" style="background: var(--brand-coral); border: none;">📊 Open Dashboard</a></li>
          <li><a href="data/parse_report.json">Parse Report (JSON)</a></li>
          <li><a href="data/audit_results.json">Audit Results (JSON)</a></li>
          <li><a href="data/court_docs_audit.csv">Audit Results (CSV)</a></li>
          <li><a href="data/unknown_event_types.csv">Unknown Event Types (CSV)</a></li>
        </ul>
      </div>

      <div class="card">
        <h2>Data Quality Audit</h2>
        <div id="audit-log">Loading audit data...</div>
      </div>
    </div>

    <script>
      async function loadData() {
        try {
          const parseRes = await fetch('data/parse_report.json');
          const parseData = parseRes.ok ? await parseRes.json() : [];

          const auditRes = await fetch('data/audit_results.json');
          const auditData = auditRes.ok ? await auditRes.json() : { issues: [] };

          let totalEvents = 0;
          parseData.forEach(f => totalEvents += (f.events_found || 0));
          const filesProcessed = parseData.length;
          const issueCount = auditData.issues ? auditData.issues.length : 0;

          document.getElementById('metrics').innerHTML = `
            <div class="metric-box">
              <span>Total Events Parsed:</span>
              <span class="metric-value">${totalEvents}</span>
            </div>
            <div class="metric-box">
              <span>Files Processed:</span>
              <span class="metric-value">${filesProcessed}</span>
            </div>
            <div class="metric-box">
              <span>Audit Issues:</span>
              <span class="metric-value" style="color: ${issueCount > 0 ? '#FF7F50' : '#27ae60'}">${issueCount}</span>
            </div>
          `;

          if (issueCount === 0) {
            document.getElementById('audit-log').innerHTML = '<p style="color:green">✅ No data quality issues found.</p>';
          } else {
            let html = '<table><thead><tr><th>Type</th><th>Case ID</th><th>Message</th></tr></thead><tbody>';
            auditData.issues.slice(0, 10).forEach(issue => {
              html += `<tr>
                <td><strong>${issue.type}</strong></td>
                <td>${issue.case_number}</td>
                <td>${issue.message}</td>
              </tr>`;
            });
            html += '</tbody></table>';
            if (auditData.issues.length > 10) {
              html += `<p>...and ${auditData.issues.length - 10} more.</p>`;
            }
            document.getElementById('audit-log').innerHTML = html;
          }

          document.getElementById('build-date').innerText = new Date().toLocaleString();
        } catch (e) {
          console.error(e);
          document.getElementById('metrics').innerHTML = '<p style="color:red">Error loading data. Ensure publish_data.py ran successfully.</p>';
        }
      }
      loadData();
    </script>
</body>
</html>
"""
    target_dir.mkdir(parents=True, exist_ok=True)
    with (target_dir / "index.html").open("w", encoding="utf-8") as f:
        f.write(html_content)
    print("   [OK] Generated default index.html with repo link to katierock01")


def main() -> int:
    if not DEST_DIR.exists():
        try:
            DEST_DIR.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Created directory: {DEST_DIR}")
        except OSError as e:
            print(f"[ERROR] Could not create directory {DEST_DIR}: {e}")
            return 1

    print(f"[INFO] Publishing data from '{SOURCE_DIR}' to '{DEST_DIR}'...")

    # Check critical files
    for filename in CRITICAL_FILES:
        src = SOURCE_DIR / filename
        if not src.exists():
            print(f"[ERROR] CRITICAL: {filename} is missing in source.")
            print("        Run the pipeline (parse_court_docs.py) first.")
            return 1

    all_files = CRITICAL_FILES + OPTIONAL_FILES
    copied_count = 0

    for filename in all_files:
        src = SOURCE_DIR / filename
        dst = DEST_DIR / filename
        if src.exists():
            try:
                shutil.copy2(src, dst)
                print(f"   [OK] Copied {filename}")
                copied_count += 1
            except Exception as e:
                print(f"   [ERROR] Failed to copy {filename}: {e}")
        else:
            if filename in OPTIONAL_FILES:
                print(f"   [WARN] Skipping {filename} (not found)")

    print(f"\n[DONE] {copied_count} files published to {DEST_DIR}.")
    # Copy dashboard HTML into docs/ for GitHub Pages
    for src, dst in PAGES_TO_COPY:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
                print(f"[OK] Copied page {src} -> {dst}")
            except Exception as e:
                print(f"[WARN] Failed to copy page {src}: {e}")
        else:
            print(f"[WARN] Page not found, skipping: {src}")

    # Always (re)generate landing page to keep branding in sync
    generate_index_html(DOCS_ROOT)

    print("Ready to commit and push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
