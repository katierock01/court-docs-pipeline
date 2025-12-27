#!/usr/bin/env python3
"""
Generate a backlog of unmapped/unknown event types for Researcher triage.
Stdlib only (no pandas). Reads data/court_docs_parsed.csv and writes data/unknown_event_types.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path

DATA_DIR = Path("data")
PARSED_PATH = DATA_DIR / "court_docs_parsed.csv"
OUTPUT_PATH = DATA_DIR / "unknown_event_types.csv"


def main() -> int:
    if not PARSED_PATH.exists():
        raise SystemExit(f"Parsed CSV not found: {PARSED_PATH}")

    with PARSED_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    unknown = {}
    for row in rows:
        code = (row.get("event_type_code") or "").strip()
        desc = (row.get("document_type") or "").strip()
        if not code:
            key = desc or "Unknown"
            unknown[key] = unknown.get(key, 0) + 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["description", "count"])
        for desc, count in sorted(unknown.items(), key=lambda x: (-x[1], x[0])):
            writer.writerow([desc, count])

    print(f"Wrote {len(unknown)} unknown descriptions to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
