"""
Sync case_events_casezero.csv with newly parsed events.
Use this to expand your ground truth dataset.
"""

import csv
from pathlib import Path
from typing import List

PARSED_CSV = Path("data/court_docs_parsed.csv")
KNOWN_CSV = Path("data/case_events_casezero.csv")


def _load_existing(path: Path) -> tuple[List[dict], List[str]]:
    """Load existing known events and capture fieldnames (if any)."""
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    return rows, fieldnames


def sync_known_events(case_id: str) -> None:
    """Add parsed events for a case to the known events file."""
    if not PARSED_CSV.exists():
        print(f"Parsed CSV not found: {PARSED_CSV}")
        return

    with PARSED_CSV.open(newline="", encoding="utf-8") as f:
        parsed = [r for r in csv.DictReader(f) if r.get("case_number") == case_id]

    existing, existing_fields = _load_existing(KNOWN_CSV)
    existing_ids = {e.get("event_id") for e in existing if (e.get("case_id") or "") == case_id}

    new_events = []
    for p in parsed:
        if not p.get("event_id") or p["event_id"] in existing_ids:
            continue
        new_events.append(
            {
                "event_id": p.get("event_id", ""),
                "case_id": p.get("case_number", ""),
                "event_date": p.get("filed_date", ""),
                "code": p.get("event_type_code", ""),
                "description": p.get("event_type_label") or p.get("document_type", ""),
                "judge": p.get("judge", ""),
                "source_view": p.get("source_view", ""),
                "document_id": p.get("document_id", ""),
            }
        )

    all_events = existing + new_events

    # Preserve existing columns; ensure required columns are present.
    required = [
        "event_id",
        "case_id",
        "event_date",
        "code",
        "description",
        "judge",
        "source_view",
        "document_id",
    ]
    fieldnames = existing_fields[:] if existing_fields else required[:]
    for col in required:
        if col not in fieldnames:
            fieldnames.append(col)

    # Normalize rows to fieldnames, dropping any unknown keys.
    normalized = []
    for row in all_events:
        norm = {fn: row.get(fn, "") for fn in fieldnames}
        normalized.append(norm)

    with KNOWN_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized)

    print(f"Added {len(new_events)} new events to {KNOWN_CSV}")
    print(f"Total events for {case_id}: {len([e for e in normalized if e.get('case_id') == case_id])}")


if __name__ == "__main__":
    sync_known_events("2025-0000424475-GA")
