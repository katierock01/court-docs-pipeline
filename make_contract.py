#!/usr/bin/env python3
"""
Define and persist the Case Zero contract and event type map.
Writes data/case_zero_contract.json and data/event_type_map.json so other tools (verifier/CI) can read them.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path("data")
CONTRACT_PATH = DATA_DIR / "case_zero_contract.json"
EVENT_MAP_PATH = DATA_DIR / "event_type_map.json"

# 1. Event Type Mappings (shared across parser + verifier)
EVENT_TYPE_MAP = {
    "PETITION": "PGII",
    "NOTICE": "NOH",
    "PROOF": "POS",
    "ORDER": "OAF",
    "LETTER": "LET",
    "OBJECTION": "OBJ",
    "REPORT": "GAR",
    "MOTION": "MOT",
    "INVENTORY": "INV",
    "ACCOUNT": "ACC",
    "WAIVER": "WAV",
    "CONSENT": "CON",
    "APPEARANCE": "APP",
    "WILL": "WIL",
    "TESTIMONY": "TST",
}

# 2. Case Zero Contract (The "Pass/Fail" Criteria for the Analyst)
# Defines the thresholds for the CI/CD pipeline.
CASE_ZERO_CONTRACT = {
    "case_id": "2025-0000424475-GA",
    "min_events": 42,
    "required_codes": ["PGII", "NOH", "POS", "OAF", "LET"],
    "quality_thresholds": {
        "date_validity_percent": 95.0,
        "max_duplicate_rows": 5,
    },
    "expected_artifacts": [
        "court_docs_parsed.csv",
        "court_docs_audit.csv",
        "parse_report.json",
        "unknown_event_types.csv",
    ],
}


def write_json(filename: Path, data: dict) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> int:
    write_json(EVENT_MAP_PATH, EVENT_TYPE_MAP)
    write_json(CONTRACT_PATH, CASE_ZERO_CONTRACT)
    print(f"Wrote Case Zero contract to {CONTRACT_PATH}")
    print(f"Wrote event type map to {EVENT_MAP_PATH}")
    # Optionally run verifier if present
    verifier = Path("verify_contract.py")
    if verifier.exists():
        import subprocess
        print("Running verify_contract.py ...")
        subprocess.call(["python", "verify_contract.py"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
