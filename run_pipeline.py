#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

STEPS = [
    ["python", "parse_court_docs.py"],
    ["python", "audit_court_docs.py"],
    ["python", "verify_contract.py"],
    ["python", "extract_unknown_event_types.py"],
]


def run(cmd: list[str]) -> int:
    print(f"\n▶ {' '.join(cmd)}")
    r = subprocess.run(cmd)
    return r.returncode


def main() -> int:
    for cmd in STEPS:
        rc = run(cmd)
        if rc != 0:
            print(f"\n❌ STOP: command failed: {' '.join(cmd)} (exit {rc})")
            return rc
    print("\n✅ ALL DONE: pipeline + contract + unknown queue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
