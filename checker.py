"""
INF 6080 demo: information-systems style checks on a public
adult-guardianship docket using CSV inputs and simple pattern matching.

This script focuses on "visibility in the public record" for expected
events (e.g., petition, notice of hearing, proof of service, order).
It does not evaluate legal compliance.
"""

import csv
import datetime
from pathlib import Path
from typing import List, Dict, Callable, Any, Optional

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

DATA_DIR = Path("data")
EVENTS_CSV = DATA_DIR / "case_events_casezero.csv"
REQUIREMENTS_CSV = DATA_DIR / "policy_requirements_public.csv"
DEFAULT_CASE_ID = "2025-0000424475-GA"
CHECKER_VERSION = "v0.2.0"
COURT_DOCS_PARSED = DATA_DIR / "court_docs_parsed.csv"

# -------------------------------------------------------------------
# Data loading helpers
# -------------------------------------------------------------------

def load_events(path: Path) -> List[Dict[str, str]]:
    """Load all events into a list of dicts."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        events = list(reader)
    # Normalize dates for sorting
    for ev in events:
        if ev.get("event_date"):
            ev["_event_date_obj"] = datetime.datetime.strptime(
                ev["event_date"], "%Y-%m-%d"
            ).date()
        else:
            ev["_event_date_obj"] = None
        # normalize code field name
        if "code" not in ev and "court_code" in ev:
            ev["code"] = ev.get("court_code")
    return events


def load_requirements(path: Path) -> List[Dict[str, str]]:
    """Load all policy requirements; normalize to requirement_id."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for r in rows:
        if "requirement_id" not in r and "pr_id" in r:
            r["requirement_id"] = r.get("pr_id")
    return rows

# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------

def now_iso() -> str:
    """Return current timestamp in ISO format."""
    return datetime.datetime.now().isoformat(timespec="seconds")


def build_check_id(case_id: str, requirement_id: str) -> str:
    """Create a stable check_id string for a case/requirement pair."""
    return f"{case_id}-{requirement_id}"


def select_case_events(events: List[Dict[str, str]], case_id: str) -> List[Dict[str, str]]:
    """Filter events list down to one case and sort by date and event_id."""
    filtered = [ev for ev in events if ev.get("case_id") == case_id]

    def sort_key(ev: Dict[str, str]):
        date_obj = ev.get("_event_date_obj") or datetime.date.min
        try:
            eid_int = int(ev.get("event_id", 0))
        except ValueError:
            eid_int = 0
        return (date_obj, eid_int)

    return sorted(filtered, key=sort_key)


def extract_event_ids(events: List[Dict[str, str]]) -> List[str]:
    """Return event_id values for a list of events, as strings."""
    return [ev.get("event_id", "") for ev in events if ev.get("event_id") is not None]


def load_parsed_docs(path: Path = COURT_DOCS_PARSED) -> List[Dict[str, str]]:
    """Load parsed court documents if available."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize_case_docs(case_id: str, docs: List[Dict[str, str]]) -> Dict[str, Any]:
    """Return simple counts for parsed docs for a case."""
    filtered = [d for d in docs if (d.get("case_number") or "") == case_id]
    by_type: Dict[str, int] = {}
    for d in filtered:
        dtype = d.get("document_type") or "Unknown"
        by_type[dtype] = by_type.get(dtype, 0) + 1
    return {
        "case_id": case_id,
        "docs_total": len(filtered),
        "docs_by_type": by_type,
    }

# -------------------------------------------------------------------
# Checks
# -------------------------------------------------------------------

def check_PR01(case_id: str,
               requirement: Dict[str, str],
               case_events: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    PR01 – Petition visible in case record (Adult GA).

    Status is "Met" if there is at least one event for the case
    with code == "PGII". Otherwise status is "Not-Visible".
    """
    run_ts = now_iso()
    requirement_id = requirement["requirement_id"]
    check_id = build_check_id(case_id, requirement_id)

    petition_events = [ev for ev in case_events if ev.get("code") == "PGII"]

    if petition_events:
        first_ev = petition_events[0]
        status = "Met"
        first_event_id = first_ev.get("event_id")
        all_event_ids = ";".join(extract_event_ids(petition_events))
        timing_notes = (
            f"Found petition event PGII on {first_ev.get('event_date','unknown date')}."
        )
        evidence_notes = "At least one PGII event is visible."
    else:
        status = "Not-Visible"
        first_event_id = ""
        all_event_ids = ""
        timing_notes = "No PGII petition event visible."
        evidence_notes = "Event list does not include PGII."

    return {
        "case_id": case_id,
        "requirement_id": requirement_id,
        "check_id": check_id,
        "status": status,
        "first_event_id": first_event_id,
        "all_event_ids": all_event_ids,
        "timing_notes": timing_notes,
        "evidence_notes": evidence_notes,
        "run_timestamp": run_ts,
        "checker_version": CHECKER_VERSION,
    }


def check_PR02(case_id: str,
               requirement: Dict[str, str],
               case_events: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    PR02 – Notice and service events visible for initial hearing.

    Status is "Met" if:
      - there is at least one event with code == "NOH", and
      - there is at least one event with code == "POS"
    anywhere in the case timeline.

    Otherwise status is "Not-Visible".
    """
    run_ts = now_iso()
    requirement_id = requirement["requirement_id"]
    check_id = build_check_id(case_id, requirement_id)

    noh_events = [ev for ev in case_events if ev.get("code") == "NOH"]
    pos_events = [ev for ev in case_events if ev.get("code") == "POS"]

    if noh_events and pos_events:
        combined = sorted(noh_events + pos_events, key=lambda ev: ev["_event_date_obj"])
        first_ev = combined[0]
        status = "Met"
        first_event_id = first_ev.get("event_id")
        all_ids = extract_event_ids(noh_events) + extract_event_ids(pos_events)
        all_event_ids = ";".join(all_ids)
        timing_notes = "At least one NOH and POS event appear."
        evidence_notes = f"Found {len(noh_events)} NOH and {len(pos_events)} POS event(s)."
    else:
        status = "Not-Visible"
        first_event_id = ""
        all_event_ids = ""
        timing_notes = "Missing NOH and/or POS events."
        evidence_notes = "Could not find both NOH and POS."

    return {
        "case_id": case_id,
        "requirement_id": requirement_id,
        "check_id": check_id,
        "status": status,
        "first_event_id": first_event_id,
        "all_event_ids": all_event_ids,
        "timing_notes": timing_notes,
        "evidence_notes": evidence_notes,
        "run_timestamp": run_ts,
        "checker_version": CHECKER_VERSION,
    }


def check_PR03(case_id: str,
               requirement: Dict[str, str],
               case_events: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    PR03 – Order entered after hearing.

    Status is "Met" if there is at least one event whose code is
    in {"OAF", "ONG", "DEN"} for the case. Otherwise status is "Not-Visible".
    """
    run_ts = now_iso()
    requirement_id = requirement["requirement_id"]
    check_id = build_check_id(case_id, requirement_id)

    valid_codes = {"OAF", "ONG", "DEN"}
    order_events = [ev for ev in case_events if ev.get("code") in valid_codes]

    if order_events:
        first_ev = order_events[0]
        status = "Met"
        first_event_id = first_ev.get("event_id")
        all_event_ids = ";".join(extract_event_ids(order_events))
        timing_notes = (
            f"Found order event {first_ev.get('code')} on "
            f"{first_ev.get('event_date', 'unknown date')}"
        )
        evidence_notes = (
            f"{len(order_events)} event(s) with code OAF, ONG, or DEN."
        )
    else:
        status = "Not-Visible"
        first_event_id = ""
        all_event_ids = ""
        timing_notes = "No OAF, ONG, or DEN events found."
        evidence_notes = "Expected a court order resolving the petition."

    return {
        "case_id": case_id,
        "requirement_id": requirement_id,
        "check_id": check_id,
        "status": status,
        "first_event_id": first_event_id,
        "all_event_ids": all_event_ids,
        "timing_notes": timing_notes,
        "evidence_notes": evidence_notes,
        "run_timestamp": run_ts,
        "checker_version": CHECKER_VERSION,
    }

# -------------------------------------------------------------------
# Registry & Dispatcher
# -------------------------------------------------------------------

CheckFunc = Callable[[str, Dict[str, str], List[Dict[str, str]]], Dict[str, Any]]

CHECK_REGISTRY: Dict[str, CheckFunc] = {
    "PR01": check_PR01,
    "PR02": check_PR02,
    "PR03": check_PR03,
}


def run_checks_for_case(case_id: str,
                        events: List[Dict[str, str]],
                        requirements: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Run all implemented checks for a single case_id."""
    case_events = select_case_events(events, case_id)
    results: List[Dict[str, Any]] = []

    for req in requirements:
        req_id = req.get("requirement_id")
        if not req_id:
            continue
        check_func = CHECK_REGISTRY.get(req_id)
        if check_func is None:
            continue
        result = check_func(case_id, req, case_events)
        results.append(result)

    return results

# -------------------------------------------------------------------
# Output Writer
# -------------------------------------------------------------------

def write_results_to_csv(results: List[Dict[str, Any]], path: Path) -> None:
    """Write check results to a CSV with the checks_results schema."""
    if not results:
        return

    fieldnames = [
        "case_id",
        "requirement_id",
        "check_id",
        "status",
        "first_event_id",
        "all_event_ids",
        "timing_notes",
        "evidence_notes",
        "run_timestamp",
        "checker_version",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

# -------------------------------------------------------------------
# Main Entry
# -------------------------------------------------------------------

def main(case_id: str = DEFAULT_CASE_ID) -> None:
    events = load_events(EVENTS_CSV)
    requirements = load_requirements(REQUIREMENTS_CSV)
    results = run_checks_for_case(case_id, events, requirements)
    parsed_docs = load_parsed_docs()
    doc_summary = summarize_case_docs(case_id, parsed_docs)

    for r in results:
        print("-----")
        for key, value in r.items():
            print(f"{key}: {value}")

    print("-----")
    print("Court document summary:")
    if parsed_docs:
        print(f"Documents for {case_id}: {doc_summary['docs_total']}")
        if doc_summary["docs_by_type"]:
            print("By type:")
            for dtype, count in doc_summary["docs_by_type"].items():
                print(f"  {dtype}: {count}")
    else:
        print("Parsed court documents not found. Run ocr_extractor.py and parse_court_docs.py.")

    output_csv = DATA_DIR / "checks_results_example.csv"
    write_results_to_csv(results, output_csv)


if __name__ == "__main__":
    main()
