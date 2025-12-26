#!/usr/bin/env python3
"""
Case Zero contract gate (reads contract JSON, no third-party deps).
Enforces artifacts, event counts, required codes, date quality, and duplicate limits.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

DATA_DIR = Path("data")
CONTRACT_FILE = DATA_DIR / "case_zero_contract.json"


def load_contract() -> dict:
    if not CONTRACT_FILE.exists():
        print(f"FAIL: Contract file {CONTRACT_FILE} missing. Run 'python make_contract.py' first.")
        sys.exit(1)
    with CONTRACT_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_date(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    fmts = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%m/%d/%y",
        "%Y/%m/%d",
        "%b %d %Y",
        "%B %d %Y",
    ]
    for f in fmts:
        try:
            datetime.strptime(s, f)
            return True
        except ValueError:
            continue
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            datetime.fromisoformat(s[:10])
            return True
        except ValueError:
            return False
    return False


def find_parsed_file(expected_artifacts: list[str]) -> Path:
    for name in expected_artifacts:
        if "parsed" in name:
            p = DATA_DIR / name
            if p.exists():
                return p
    fallback = DATA_DIR / "court_docs_parsed.csv"
    if fallback.exists():
        return fallback
    raise FileNotFoundError("Parsed CSV not found (looked for *parsed* in expected_artifacts and court_docs_parsed.csv)")


def verify() -> int:
    contract = load_contract()
    expected_artifacts = contract.get("expected_artifacts", [])

    print("Verifying Pipeline Artifacts...")
    missing = [fn for fn in expected_artifacts if not (DATA_DIR / fn).exists()]
    if missing:
        print(f"FAIL: Missing expected artifacts: {', '.join(missing)}")
        return 1
    print("Artifacts present.")

    try:
        data_file = find_parsed_file(expected_artifacts)
        with data_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"FAIL: Unable to read parsed CSV: {e}")
        return 1

    case_id = contract["case_id"]
    min_events = contract["min_events"]
    required_codes = set(contract["required_codes"])
    thresholds = contract.get("quality_thresholds", {})
    date_threshold = thresholds.get("date_validity_percent", 95.0)
    max_dupes = thresholds.get("max_duplicate_rows", 5)

    case_zero_rows = [r for r in rows if r.get("case_number") == case_id]
    count = len(case_zero_rows)
    print(f"Case Zero Events: {count}")
    if count < min_events:
        print(f"FAIL: Found {count} events, expected >= {min_events}")
        return 1

    found_codes = set(r.get("event_type_code") for r in case_zero_rows if r.get("event_type_code"))
    missing_codes = required_codes - found_codes
    if missing_codes:
        print(f"FAIL: Missing required codes: {missing_codes}")
        return 1

    valid_dates = sum(1 for r in case_zero_rows if parse_date(r.get("filed_date", "")))
    date_rate = (valid_dates / len(case_zero_rows)) * 100 if case_zero_rows else 0
    print(f"Date Quality: {date_rate:.1f}% ({valid_dates}/{len(case_zero_rows)})")
    if date_rate < date_threshold:
        print(f"FAIL: Date quality below {date_threshold}%")
        return 1

    signatures = [
        f"{r.get('case_number')}|{r.get('filed_date')}|{r.get('document_type')}|{r.get('event_type_code')}"
        for r in case_zero_rows
    ]
    dupes = [sig for sig, c in Counter(signatures).items() if c > 1]
    if len(dupes) > max_dupes:
        print(f"FAIL: Too many duplicate rows detected ({len(dupes)} > {max_dupes})")
        return 1

    print("SUCCESS: All contract checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(verify())
