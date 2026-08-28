# modules/calc_engine.md -- Calculations Engine Setup (All Tiers)

**When to read:** Phase 4, right after the Phase 4 formula-complexity audit (WORKBOOK_CONVENTIONS.md Part 1/Part 2 Step 3) has assigned a tier.

**Purpose:** One reusable, project-agnostic implementation for each calc-engine tier, so the choice between them is a project decision, not a from-scratch build every time.

---

## Tier 1 -- Hand-Ported Python

Use when every output the app reads is a simple lookup or average, with no cross-sheet array logic (VLG's Value-Led Growth calculator is the reference implementation of this pattern).

```python
# calculator.py
from pathlib import Path
import openpyxl

MASTER_WORKBOOK = Path(__file__).parent.parent.parent / 'WORKBOOK.xlsx'

# Loaded once, at import time OR via load_reference_data() if this project also
# has modules/workbook_lifecycle.md wired in -- see that module for why the
# callable form matters.
def load_reference_data(workbook_path=MASTER_WORKBOOK):
    wb = openpyxl.load_workbook(workbook_path, data_only=True)
    return {
        'maturity_map': _read_named_range_table(wb, 'MaturityLabels', 'MaturityValues'),
        'capabilities': _read_named_range_list(wb, 'Capabilities'),
        'peer_scores': _read_named_range_list(wb, 'PeerScores'),
        # ... every other reference table/list the model needs
    }

REFERENCE = load_reference_data()

def run_calculation(profile, ratings):
    # Plain Python: dict lookups, list averages, sort/rank -- no workbook I/O per request
    ...
```

**Rules:**
- The master workbook is read only to hydrate `REFERENCE`, never per-request, and never written to.
- If the model's *logic* changes (not just its reference data), the Python port has to be updated by hand -- this tier trades reusability of logic for zero runtime cost.
- Named ranges still drive every reference-data read, so a workbook refresh (see modules/workbook_lifecycle.md) can still swap in new peer benchmarks etc. without a code change, as long as the structure doesn't change.

---

## Tier 2 -- xlcalculator (new default)

Use when the workbook has VLOOKUP/INDEX-MATCH/SUMIFS-level complexity, multi-sheet references, but nothing volatile or array-based.

```bash
pip install xlcalculator
```

```python
# calculator.py
from pathlib import Path
from xlcalculator import ModelCompiler, Evaluator

MASTER_WORKBOOK = Path(__file__).parent.parent.parent / 'WORKBOOK.xlsx'

def _load_model(workbook_path=MASTER_WORKBOOK):
    compiler = ModelCompiler()
    return compiler.read_and_parse_archive(str(workbook_path))

_MODEL = _load_model()

def run_calculation(profile, priorities, assumptions=None):
    evaluator = Evaluator(_MODEL)

    # Write profile inputs via named ranges
    for name, value in _build_profile_map(profile, priorities).items():
        evaluator.set_cell_value(f"'{_sheet_for(name)}'!{_addr_for(name)}", value)

    if assumptions:
        for key, addr in _DISC_MAP.items():
            if key in assumptions:
                evaluator.set_cell_value(f"'Discovery'!{addr}", _coerce(assumptions[key]))

    return {name: evaluator.evaluate(f"'{_sheet_for(name)}'!{_addr_for(name)}")
            for name in OUTPUT_NAMED_RANGES}
```

**Rules:**
- No subprocess, no temp files, no LibreOffice -- runs entirely in the Flask process.
- Master workbook is never modified; `set_cell_value` mutates the in-memory model only.
- If `xlcalculator` can't parse a formula (raises on `read_and_parse_archive` or on `evaluate`), that output cell is Tier 3 -- either reimplement just that value in Python (drop to Tier 1 for it) or move the whole workbook to Tier 3.
- This is the pattern to reuse across projects by default. Prefer it over Tier 3 whenever the workbook allows it -- it is the direct, reusable replacement for the old openpyxl+LibreOffice default.

---

## Tier 3 -- openpyxl + LibreOffice (last resort)

Full pattern and rules are in PLATFORM.md's "Calculations Engine Pattern" section. Use only when Tier 2 genuinely fails on a formula the workbook needs (LAMBDA, dynamic arrays, volatile functions). Requires Cloud Run 2Gi hosting -- never Render free tier (P028).

---

## Choosing between tiers on a real project

1. Run the Phase 4 audit (WORKBOOK_CONVENTIONS.md Part 2, Step 3) and tier every output cell.
2. If everything is Tier 1: hand-port. Simplest, no dependency.
3. If anything is Tier 2 and nothing is Tier 3: use xlcalculator for the whole workbook.
4. If anything is genuinely Tier 3: use LibreOffice for the whole workbook, and size hosting accordingly.
5. Record the decision and the reasoning in CLAUDE.md's Key Decisions Log -- this is exactly the kind of judgment call (VLG's Tier 1 port, born from a resource-constrained one-off) that needs to be visible for the next project, not rediscovered from scratch.
