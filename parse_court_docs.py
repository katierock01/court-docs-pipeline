"""
Phase 2: Parse OCR'd court documents into structured CSV.

Inputs:
- Raw text files from ocr_extractor.py (default: data/court_docs_text/*.txt)
- OCR summary CSV for confidence flags (default: data/court_docs_ocr_summary.csv)
- Event vocabulary (default: data/events.csv)

Outputs:
- data/court_docs_parsed.csv

Fields:
file_name, event_id, document_id, source_view, case_number, filed_date,
document_type, party_petitioner, party_respondent, party_guardian,
event_type_code, event_type_label, judge, low_confidence, notes
"""

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RAW_TEXT_DIR = Path("data") / "court_docs_text"
OUTPUT_CSV = Path("data") / "court_docs_parsed.csv"
OCR_SUMMARY_CSV = Path("data") / "court_docs_ocr_summary.csv"
EVENTS_CSV = Path("data") / "events.csv"
EVENT_TYPE_MAP_JSON = Path("data") / "event_type_map.json"

# Patterns
CASE_PATTERNS = [
    re.compile(r"\d{2}-[A-Z]{2}-\d{4}"),         # 22-GA-1234
    re.compile(r"\d{4}-\d{6,}-[A-Z]{2}"),       # 2025-000042- GA
    re.compile(r"\d{4}-\d{6,}-\s*[A-Z]{2}"),    # allow space before suffix
    re.compile(r"DEMO-\d{4}-\d{4}"),            # DEMO-2025-0001
]

DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),     # 2025-02-14
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),  # 2/14/2025
    re.compile(r"\b([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\b"),  # Feb 14, 2025
    re.compile(r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b"),   # 14 Feb 2025
]


def extract_case_from_table_header(text: str) -> str:
    """Court Explorer tables often put case number near the top; scan header chunk."""
    header = text[:500]
    match = first_match(CASE_PATTERNS, header)
    if match:
        return match
    label_pattern = re.compile(r"Case ID\s+(\d{4}-\d{6,}-[A-Z]{2})", re.I)
    m = label_pattern.search(header)
    return m.group(1) if m else ""


DOC_TYPE_KEYWORDS = {
    "petition": "Petition",
    "order appoint": "Order appointing fiduciary",
    "letters": "Letters of authority",
    "hearing notice": "Hearing Notice",
    "notice of hearing": "Hearing Notice",
    "proof of service": "Proof of service",
    "affidavit": "Affidavit",
    "objection": "Objection",
    "bond": "Bond",
    "evaluation": "Evaluation",
}

EVENT_MAP = {
    "Petition": "PGII",
    "Hearing Notice": "NOH",
    # Standardize service proofs to POS (events.csv also has PPS if you split types later).
    "Proof of service": "POS",
    "Objection": "OBJ",
    "Order appointing fiduciary": "OAF",
    "Letters of authority": "LET",
    "Affidavit": "AFF",
    "Bond": "BND",
    "Evaluation": "EVAL",
}


@dataclass
class ParsedDoc:
    file_name: str
    event_id: str
    document_id: str
    source_view: str
    case_number: str
    filed_date: str
    document_type: str
    party_petitioner: str
    party_respondent: str
    party_guardian: str
    event_type_code: str
    event_type_label: str
    judge: str
    low_confidence: str
    notes: str


def load_event_vocab(path: Path) -> Dict[str, str]:
    """Return map of code -> label from events.csv."""
    vocab: Dict[str, str] = {}
    if not path.exists():
        return vocab
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("code") or "").strip()
            label = (row.get("label") or "").strip()
            if code:
                vocab[code] = label
    return vocab


def load_ocr_summary(path: Path) -> Dict[str, Dict[str, str]]:
    """Return mapping of pdf base name -> summary values."""
    summary: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return summary
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("pdf_name") or "").strip()
            if name:
                summary[name] = row
    return summary


def load_event_type_map(path: Path) -> Dict[str, str]:
    """Optional description->code map stored in JSON to avoid hard-coding mappings."""
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        # Normalize keys to upper for matching
        return {str(k).upper(): str(v).upper() for k, v in data.items() if k and v}
    except Exception:
        return {}


def first_match(patterns: List[re.Pattern], text: str) -> str:
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(0)
    return ""


def detect_document_type(text: str) -> str:
    low = text.lower()
    for key, label in DOC_TYPE_KEYWORDS.items():
        if key in low:
            return label
    return ""


def detect_party(text: str, label: str) -> str:
    pattern = re.compile(label + r"[:\-]\s*([A-Z][A-Za-z.,\s]+)", re.I)
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def detect_judge(text: str) -> str:
    pattern = re.compile(r"judge[:\s]+([A-Z][A-Za-z.\s]+)", re.I)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    pattern2 = re.compile(r"magistrate[:\s]+([A-Z][A-Za-z.\s]+)", re.I)
    m2 = pattern2.search(text)
    return m2.group(1).strip() if m2 else ""


def select_event_code(doc_type: str) -> str:
    return EVENT_MAP.get(doc_type, "")


def map_desc_to_code(desc: str, dynamic_map: Optional[Dict[str, str]] = None) -> str:
    """Keyword-to-code mapping for event table descriptions."""
    up = desc.upper()
    if dynamic_map:
        # direct match on keyword tokens from JSON
        for key, val in dynamic_map.items():
            if key in up:
                return val
    if "PETITION" in up:
        return "PGII"
    if "NOTICE" in up:
        return "NOH"
    if "PROOF" in up:
        return "POS"
    if "ORDER" in up:
        return "OAF"
    if "LETTER" in up:
        return "LET"
    if "OBJECTION" in up:
        return "OBJ"
    return ""


def parse_events_table(
    content: str,
    base_case: str,
    vocab: Dict[str, str],
    summary_row: Dict[str, str],
    file_name: str,
    desc_map: Optional[Dict[str, str]] = None,
) -> List[ParsedDoc]:
    """Parse MiCourt/CourtExplorer event list tables into per-event rows.

    Strategy:
    1) Row regex (date + description + event number on one line).
    2) Streaming block parse that walks Event Date / Description / Event No. sections,
       supporting multiple descriptions under the same date.
    """

    def next_nonempty(start: int, arr: List[str]) -> Tuple[int, str]:
        j = start
        while j < len(arr) and not arr[j].strip():
            j += 1
        return j, arr[j].strip() if j < len(arr) else ""

    lines = [ln.rstrip() for ln in content.splitlines()]
    parsed: List[ParsedDoc] = []
    low_conf_summary = (summary_row.get("low_confidence") or "").lower() == "yes"

    # Strategy A: row-based regex (date + description + event number)
    row_pattern = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+)\s*$")
    for line in lines:
        m = row_pattern.match(line)
        if not m:
            continue
        filed_date, desc, event_no = m.groups()
        document_type = desc.strip() or "Unknown"
        event_code = select_event_code(document_type) or map_desc_to_code(document_type, desc_map)
        event_label = vocab.get(event_code, document_type)

        text_is_short = len(document_type) < 3
        low_conf = "yes" if low_conf_summary or text_is_short else "no"
        notes: List[str] = ["parsed from events table (row)"]
        if text_is_short:
            notes.append("description short")

        parsed.append(
            ParsedDoc(
                file_name=file_name,
                event_id=event_no or f"{base_case}-{filed_date}-{len(parsed)+1:02d}",
                document_id=f"{Path(file_name).stem}.pdf",
                source_view="MiCourt_EventList",
                case_number=base_case,
                filed_date=filed_date,
                document_type=document_type,
                party_petitioner="",
                party_respondent="",
                party_guardian="",
                event_type_code=event_code,
                event_type_label=event_label,
                judge="",
                low_confidence=low_conf,
                notes="; ".join(notes),
            )
        )

    # Strategy B: streaming block parse if row-based did not find enough
    if len(parsed) < 30:
        label_stops = (
            "event date",
            "description",
            "party/count",
            "event no",
            "event no.",
            "comment",
            "judge",
            "attorney",
            "next hearing",
            "program/results",
            "amount",
            "disposition",
            "category action",
            "party action",
        )
        current_date = ""
        pending: List[Tuple[str, str]] = []  # (date, description)
        seq = len(parsed) + 1

        def emit_event(desc_text: str, event_no_text: str, filed_date_text: str) -> None:
            nonlocal seq
            if not filed_date_text:
                return
            desc_clean = desc_text.strip() or "Unknown"
            event_no_clean = re.sub(r"[^0-9]", "", event_no_text) or f"{seq:02d}"
            event_code = select_event_code(desc_clean) or map_desc_to_code(desc_clean, desc_map)
            event_label = vocab.get(event_code, desc_clean)
            text_is_short = len(desc_clean) < 3
            low_conf = "yes" if low_conf_summary or text_is_short else "no"
            notes: List[str] = ["parsed from events table (block)"]
            if text_is_short:
                notes.append("description short")

            parsed.append(
                ParsedDoc(
                    file_name=file_name,
                    event_id=f"{base_case}-{filed_date_text}-{event_no_clean}",
                    document_id=f"{Path(file_name).stem}.pdf",
                    source_view="MiCourt_EventList",
                    case_number=base_case,
                    filed_date=filed_date_text,
                    document_type=desc_clean,
                    party_petitioner="",
                    party_respondent="",
                    party_guardian="",
                    event_type_code=event_code,
                    event_type_label=event_label,
                    judge="",
                    low_confidence=low_conf,
                    notes="; ".join(notes),
                )
            )
            seq += 1

        i = 0
        while i < len(lines):
            raw = lines[i]
            line = raw.strip()
            low = line.lower()
            if not line:
                i += 1
                continue

            if low.startswith("event date"):
                _, val = next_nonempty(i + 1, lines)
                date_val = first_match(DATE_PATTERNS, val) or first_match(DATE_PATTERNS, line)
                if date_val:
                    current_date = date_val
                i += 1
                continue

            # Dates that appear without the "Event Date" label (rare)
            if not current_date:
                date_val = first_match(DATE_PATTERNS, line)
                if date_val:
                    current_date = date_val
                    i += 1
                    continue

            if low.startswith("description"):
                desc_parts: List[str] = []
                j = i + 1
                while j < len(lines):
                    nxt = lines[j].strip()
                    nxt_low = nxt.lower()
                    if not nxt or nxt_low.startswith(label_stops) or first_match(DATE_PATTERNS, nxt):
                        break
                    desc_parts.append(nxt)
                    j += 1
                current_desc = " ".join(desc_parts).strip()
                if current_desc:
                    pending.append((current_date, current_desc))
                i = j
                continue

            if "event no" in low:
                _, val = next_nonempty(i + 1, lines)
                current_no = val.strip()
                if pending:
                    date_for_desc, desc_for_event = pending.pop(0)
                else:
                    date_for_desc, desc_for_event = current_date, current_desc
                emit_event(desc_for_event, current_no, date_for_desc or current_date)
                current_desc = ""
                i += 1
                continue

            i += 1

    return parsed


def parse_file(
    path: Path,
    vocab: Dict[str, str],
    ocr_summary: Dict[str, Dict[str, str]],
    desc_map: Optional[Dict[str, str]] = None,
) -> List[ParsedDoc]:
    """Backward-compatible entrypoint that returns only rows."""
    rows, _ = parse_file_with_report(path, vocab, ocr_summary, desc_map)
    return rows


def parse_file_with_report(
    path: Path,
    vocab: Dict[str, str],
    ocr_summary: Dict[str, Dict[str, str]],
    desc_map: Optional[Dict[str, str]] = None,
) -> Tuple[List[ParsedDoc], Dict[str, object]]:
    content = path.read_text(encoding="utf-8", errors="ignore")

    case_number = first_match(CASE_PATTERNS, content)
    if not case_number:
        case_number = extract_case_from_table_header(content)
    case_number = case_number.replace(" ", "")

    summary_row = ocr_summary.get(f"{path.stem}.pdf", {})
    warnings: List[str] = []
    strategy_used = "fallback"

    if "events" in content.lower():
        table_rows = parse_events_table(content, case_number, vocab, summary_row, path.name, desc_map)
        if len(table_rows) >= 10:
            strategy_used = "table"
            return table_rows, {
                "filename": path.name,
                "strategy_used": strategy_used,
                "events_found": len(table_rows),
                "warnings": warnings,
            }
        warnings.append(f"table strategy only found {len(table_rows)} events; using fallback")

    filed_date = first_match(DATE_PATTERNS, content)
    document_type = detect_document_type(content)
    petitioner = detect_party(content, "Petitioner")
    respondent = detect_party(content, "Respondent")
    guardian = detect_party(content, "Guardian")
    judge = detect_judge(content)

    event_code = select_event_code(document_type) or map_desc_to_code(document_type, desc_map)
    event_label = vocab.get(event_code, "")

    low_conf_summary = (summary_row.get("low_confidence") or "").lower() == "yes"
    text_is_short = len(content.strip()) < 80
    low_conf = "yes" if low_conf_summary or text_is_short else "no"

    notes: List[str] = []
    if not case_number:
        notes.append("case number not found")
    if text_is_short:
        notes.append("very short text; manual check")
    if low_conf_summary:
        notes.append("OCR low confidence")

    rows = [
        ParsedDoc(
            file_name=path.name,
            event_id="",
            document_id=f"{path.stem}.pdf",
            source_view="ocr_pipeline",
            case_number=case_number,
            filed_date=filed_date,
            document_type=document_type,
            party_petitioner=petitioner,
            party_respondent=respondent,
            party_guardian=guardian,
            event_type_code=event_code,
            event_type_label=event_label,
            judge=judge,
            low_confidence=low_conf,
            notes="; ".join(notes),
        )
    ]

    return rows, {
        "filename": path.name,
        "strategy_used": strategy_used,
        "events_found": len(rows),
        "warnings": warnings,
    }


def parse_all(raw_dir: Path, output_csv: Path) -> None:
    vocab = load_event_vocab(EVENTS_CSV)
    desc_map = load_event_type_map(EVENT_TYPE_MAP_JSON)
    ocr_summary = load_ocr_summary(OCR_SUMMARY_CSV)

    text_files = sorted(raw_dir.glob("*.txt"))
    if not text_files:
        raise SystemExit(f"No text files found in {raw_dir}. Run ocr_extractor.py first.")

    rows: List[ParsedDoc] = []
    report: List[Dict[str, object]] = []
    for path in text_files:
        parsed_rows, report_entry = parse_file_with_report(path, vocab, ocr_summary, desc_map)
        rows.extend(parsed_rows)
        report.append(report_entry)

    fieldnames = [f.name for f in ParsedDoc.__dataclass_fields__.values()]  # type: ignore
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)

    # Observability: write parse_report.json
    report_path = output_csv.parent / "parse_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse OCR text files into structured CSV.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_TEXT_DIR, help="Directory of OCR text files.")
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV, help="Output CSV path.")
    args = parser.parse_args()

    parse_all(args.raw_dir, args.output)
    print(f"Wrote parsed data to {args.output}")


if __name__ == "__main__":
    main()
