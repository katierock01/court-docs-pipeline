"""
Phase 2: Parse OCR'd court documents into structured CSV.

Inputs:
- Raw text files from ocr_extractor.py (default: data/court_docs_text/*.txt)
- OCR summary CSV for confidence flags (default: data/court_docs_ocr_summary.csv)
- Event vocabulary (default: data/events.csv)

Outputs:
- data/court_docs_parsed.csv

Fields:
file_name, case_number, filed_date, document_type, party_petitioner,
party_respondent, party_guardian, event_type_code, event_type_label,
judge, low_confidence, notes
"""

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RAW_TEXT_DIR = Path("data") / "court_docs_text"
OUTPUT_CSV = Path("data") / "court_docs_parsed.csv"
OCR_SUMMARY_CSV = Path("data") / "court_docs_ocr_summary.csv"
EVENTS_CSV = Path("data") / "events.csv"

# Patterns
CASE_PATTERNS = [
    re.compile(r"\d{2}-[A-Z]{2}-\d{4}"),         # 22-GA-1234
    re.compile(r"\d{4}-\d{6,}-[A-Z]{2}"),       # 2025-000042- GA
    re.compile(r"DEMO-\d{4}-\d{4}"),            # DEMO-2025-0001
]

DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),     # 2025-02-14
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),  # 2/14/2025
]

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
    "Proof of service": "PPS",
    "Objection": "OBJ",
    "Order appointing fiduciary": "OAF",
    "Letters of authority": "LET",
}


@dataclass
class ParsedDoc:
    file_name: str
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
    # Simple heuristic: look for "Petitioner: Name"
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


def parse_file(
    path: Path,
    vocab: Dict[str, str],
    ocr_summary: Dict[str, Dict[str, str]],
) -> ParsedDoc:
    content = path.read_text(encoding="utf-8", errors="ignore")

    case_number = first_match(CASE_PATTERNS, content)
    filed_date = first_match(DATE_PATTERNS, content)
    document_type = detect_document_type(content)
    petitioner = detect_party(content, "Petitioner")
    respondent = detect_party(content, "Respondent")
    guardian = detect_party(content, "Guardian")
    judge = detect_judge(content)

    event_code = select_event_code(document_type)
    event_label = vocab.get(event_code, "")

    summary_row = ocr_summary.get(f"{path.stem}.pdf", {})
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

    return ParsedDoc(
        file_name=path.name,
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


def parse_all(raw_dir: Path, output_csv: Path) -> None:
    vocab = load_event_vocab(EVENTS_CSV)
    ocr_summary = load_ocr_summary(OCR_SUMMARY_CSV)

    text_files = sorted(raw_dir.glob("*.txt"))
    if not text_files:
        raise SystemExit(f"No text files found in {raw_dir}. Run ocr_extractor.py first.")

    rows = [parse_file(path, vocab, ocr_summary) for path in text_files]

    fieldnames = [f.name for f in ParsedDoc.__dataclass_fields__.values()]  # type: ignore
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse OCR text files into structured CSV.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_TEXT_DIR, help="Directory of OCR text files.")
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV, help="Output CSV path.")
    args = parser.parse_args()

    parse_all(args.raw_dir, args.output)
    print(f"Wrote parsed data to {args.output}")


if __name__ == "__main__":
    main()
