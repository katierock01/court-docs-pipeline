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
    print("Ready to commit and push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
