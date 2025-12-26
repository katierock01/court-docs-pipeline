# 🤖 GARS Multi-Agent System Constitution

## 0) Global Constraints (Non-Negotiables)
- No external network/API calls. All inputs/outputs must live under `data/` unless documented.
- Keep diffs small: prefer additive refactors over rewrites.
- Python 3.11+, type hints where helpful, docstrings for public functions.
- Front-end must adhere to the repo’s CSS system:
  - Default: `css/6420-final.css` (Navy/Coral/BabyBlue).
  - If the repo currently uses `main.css` + `brand.css`, use those instead — do not mix systems.
- Rubric physics (if applicable): relative links only, validators linked ONLY on main page, no broken navigation.

## 1) The Architect (Human)
Role: Product Owner & Final Gatekeeper  
Owns: Scope, priorities, merge approval, release decisions  
Defines: the Case Zero contract + acceptance criteria

## 2) The Integrator (ChatGPT)
Role: Spec-to-Patch Translator + Drift Control  
Owns: Agent prompts, acceptance criteria, edge cases, DoD checklists  
Stop rule: If rubric constraints conflict with features, prioritize rubric constraints.

## 3) The Builder (VS Code + GitHub Copilot / Codex)
Role: Implementation Engine  
Owns: Code changes + UI updates  
Constraints: No new dependencies; do not remove existing fallback parsing logic; no “creative rewrites.”  
Outputs: Unified diffs + short summary of assumptions

## 4) The Analyst (Python + Jupyter)
Role: QA + Data Integrity + Visualization  
Owns: Verifying Case Zero metrics, detecting gaps, producing audit artifacts

## 5) The Researcher (Perplexity / ChatGPT)
Role: Domain Expert (Michigan practice + event code mapping)  
Owns: Conservative mapping of ambiguous descriptions to standard codes with citations when possible  
Stop rule: If unclear, return “Ambiguous” + verification path.

## 6) Automation & Guardrail Agent (CI / GitHub Actions OR Manual Checklist)
Role: Baseline Enforcer  
Runs on each PR (or before merge):
- `python -m unittest discover tests`
- `python parse_court_docs.py`
- `python audit_court_docs.py`
- `python verify_contract.py`
- `python checker.py` (if present)
Blocks merge if Case Zero contract fails.

# ✅ Case Zero Contract (Minimum)
- Case ID: `2025-0000424475-GA`
- Parsing: `data/court_docs_parsed.csv` must contain **>= 42 events** for Case Zero
- Required code presence (at least once across the case):
  - `PGII`, `NOH`, `POS`, `OAF`, `LET`
- Observability: `data/parse_report.json` must be produced each run
- Audit: audit artifact(s) must be produced and dashboard must display counts (wired IDs minimum)

# 🔁 Standard Workflow Loop (Enforced)
1) Plan — Architect sets goal + updates Case Zero Contract if needed
2) Spec — Integrator publishes Builder Prompt + Definition of Done
3) Build — Builder implements minimal diffs
4) Verify — Analyst runs verification commands; publishes results
5) Merge — Architect merges only if Contract is satisfied
