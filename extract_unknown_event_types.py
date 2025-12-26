#!/usr/bin/env python3
"""
Generate a backlog of unmapped/unknown event types for Researcher triage.
Picks a parsed CSV under data/ and writes data/unknown_event_types.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path("data")
OUT_PATH = DATA_DIR / "unknown_event_types.csv"


def pick_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def find_parsed_csv() -> Path:
    # Prefer common names; else pick the newest "*parsed*.csv"; else newest csv.
    preferred = [DATA_DIR / "court_docs_parsed.csv", DATA_DIR / "courtdocsparsed.csv"]
    for p in preferred:
        if p.exists():
            return p

    parsed_hits = sorted(DATA_DIR.glob("*parsed*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if parsed_hits:
        return parsed_hits[0]

    hits = sorted(DATA_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if hits:
        return hits[0]

    raise FileNotFoundError("No CSV found under data/ (expected parsed events output).")


def main() -> int:
    csv_path = find_parsed_csv()
    df = pd.read_csv(csv_path)

    desc_col = pick_col(df, ["document_type", "description", "event_description", "doc_description", "text", "title"])
    code_col = pick_col(df, ["event_type_code", "event_code", "code", "jis_code", "type_code"])

    if not desc_col:
        print(f"❌ Cannot find a description column in {csv_path.name}. Columns: {list(df.columns)}")
        return 1

    # If there's no code column, treat everything as "unknown" (still useful)
    if not code_col:
        unknown_df = df[[desc_col]].copy()
        unknown_df["reason"] = "no_code_column"
    else:
        codes = df[code_col].astype(str).str.strip()
        unknown_mask = df[code_col].isna() | (codes == "") | (codes.str.upper().isin({"UNKNOWN", "UNK", "NONE", "NAN"}))
        unknown_df = df.loc[unknown_mask, [desc_col]].copy()
        unknown_df["reason"] = "missing_or_unknown_code"

    # Unique, cleaned
    unknown_df[desc_col] = unknown_df[desc_col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    unknown_df = unknown_df[unknown_df[desc_col] != ""].drop_duplicates(subset=[desc_col]).sort_values(by=desc_col)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    unknown_df.rename(columns={desc_col: "description"}).to_csv(OUT_PATH, index=False)

    print(f"✅ Wrote {len(unknown_df)} unknown descriptions to {OUT_PATH}")
    print(f"   Source parsed CSV: {csv_path}")
    print(f"   Description column: {desc_col}")
    print(f"   Code column: {code_col or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
