"""
Phase 3: Validate parsed court documents against case data.

Checks:
- Missing documents: cases with no parsed documents.
- Orphaned documents: parsed docs whose case_number is not in cases.csv.
- Date inconsistencies: filed dates before case opened or after closed.
- Duplicate filings: same case_number + document_type + filed_date.

Outputs:
- data/court_docs_audit.csv
- data/audit_history/audit_<timestamp>.csv (archived copies; opt-out with --no-archive)
"""

import argparse
import csv
import datetime as dt
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

PARSED_CSV = Path("data") / "court_docs_parsed.csv"
CASES_CSV = Path("data") / "cases.csv"
OUTPUT_CSV = Path("data") / "court_docs_audit.csv"
TIMESTAMPED_OUTPUT = Path("data") / "audit_history"


def load_cases(path: Path) -> Dict[str, Dict[str, str]]:
    cases: Dict[str, Dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = (row.get("case_id") or "").strip()
            if cid:
                cases[cid] = row
    return cases


def parse_date(value: str) -> dt.date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def load_parsed(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def audit(parsed: List[Dict[str, str]], cases: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    case_to_docs: defaultdict[str, List[Dict[str, str]]] = defaultdict(list)

    for doc in parsed:
        cid = (doc.get("case_number") or "").strip()
        case_to_docs[cid].append(doc)

    # Missing documents
    for cid in cases:
        if not case_to_docs.get(cid):
            issues.append(
                {
                    "issue_type": "missing_documents",
                    "case_id": cid,
                    "file_name": "",
                    "filed_date": "",
                    "detail": "No parsed documents for case",
                }
            )

    # Orphaned documents
    for doc in parsed:
        cid = (doc.get("case_number") or "").strip()
        if cid and cid not in cases:
            issues.append(
                {
                    "issue_type": "orphan_document",
                    "case_id": cid,
                    "file_name": doc.get("file_name", ""),
                    "filed_date": doc.get("filed_date", ""),
                    "detail": "Case not found in cases.csv",
                }
            )

    # Date inconsistencies
    for doc in parsed:
        cid = (doc.get("case_number") or "").strip()
        filed = parse_date(doc.get("filed_date", ""))
        case_row = cases.get(cid) if cid else None
        if not case_row or not filed:
            continue
        opened = parse_date(case_row.get("opened_date", ""))
        closed = parse_date(case_row.get("closed_date", ""))
        if opened and filed < opened:
            issues.append(
                {
                    "issue_type": "date_inconsistent",
                    "case_id": cid,
                    "file_name": doc.get("file_name", ""),
                    "filed_date": doc.get("filed_date", ""),
                    "detail": "Filed before case opened",
                }
            )
        if closed and filed > closed:
            issues.append(
                {
                    "issue_type": "date_inconsistent",
                    "case_id": cid,
                    "file_name": doc.get("file_name", ""),
                    "filed_date": doc.get("filed_date", ""),
                    "detail": "Filed after case closed",
                }
            )

    # Duplicate filings
    combo_counter = Counter()
    for doc in parsed:
        combo = (
            (doc.get("case_number") or "").strip(),
            (doc.get("document_type") or "").strip(),
            (doc.get("filed_date") or "").strip(),
        )
        combo_counter[combo] += 1

    for combo, count in combo_counter.items():
        if count > 1:
            cid, dtype, fdate = combo
            issues.append(
                {
                    "issue_type": "duplicate_filing",
                    "case_id": cid,
                    "file_name": "",
                    "filed_date": fdate,
                    "detail": f"{count} documents with type/date combination ({dtype} {fdate})",
                }
            )

    return issues


def write_issues(issues: List[Dict[str, str]], output: Path, timestamp: bool = True) -> None:
    fieldnames = ["issue_type", "case_id", "file_name", "filed_date", "detail"]
    output.parent.mkdir(parents=True, exist_ok=True)

    # Write current audit results
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in issues:
            writer.writerow(row)

    # Optionally archive a timestamped copy for history
    if timestamp:
        TIMESTAMPED_OUTPUT.mkdir(parents=True, exist_ok=True)
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = TIMESTAMPED_OUTPUT / f"audit_{ts}.csv"
        shutil.copy2(output, archive_path)
        print(f"Archived audit to {archive_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit parsed court documents.")
    parser.add_argument("--parsed", type=Path, default=PARSED_CSV, help="Parsed documents CSV.")
    parser.add_argument("--cases", type=Path, default=CASES_CSV, help="Cases CSV.")
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV, help="Audit output CSV.")
    parser.add_argument("--no-archive", action="store_true", help="Skip timestamped archive copy.")
    args = parser.parse_args()

    if not args.parsed.exists():
        raise SystemExit(f"Parsed CSV not found: {args.parsed}")
    if not args.cases.exists():
        raise SystemExit(f"Cases CSV not found: {args.cases}")

    parsed = load_parsed(args.parsed)
    cases = load_cases(args.cases)
    issues = audit(parsed, cases)
    write_issues(issues, args.output, timestamp=not args.no_archive)
    print(f"Wrote audit issues to {args.output} ({len(issues)} rows)")


if __name__ == "__main__":
    main()
