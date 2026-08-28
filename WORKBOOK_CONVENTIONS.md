# WORKBOOK_CONVENTIONS.md -- Excel Workbook Design and Audit Guide

**Three-part reference:**
- **Part 1:** Conventions for workbooks you design from scratch, including the calc-engine tiering decision
- **Part 2:** Audit checklist for workbooks handed to you
- **Part 3:** Lifecycle -- refreshing a live workbook after launch without a code deploy

---

# Part 1: Design Conventions (Workbooks Built from Scratch)

## Sheet Naming

- Use exact, stable names -- they are hardcoded in the Flask app's named range lookups
- No spaces in sheet names (spaces cause lookup failures in some contexts -- see CLAUDE_problems.md P014)
- Required sheets: `Profile` (user inputs), `Discovery` (assumptions), `[Framework]` (calculators), `[Summary]` (outputs), `Data` (lookup matrix)
- Document sheet names in CLAUDE.md at project start -- never rename after the app is built

## Named Range Requirements

Every input the app writes and every output the app reads **must** have a named range. No exceptions.

**Inputs (app writes these):**
- All Profile inputs: company name, revenue, employees, IT headcount, challenge priorities
- All Discovery assumption fields the user can override

**Outputs (app reads these):**
- All KPI values displayed on the Summary page
- All per-benefit callout values (annual, 3-year)
- All tbl_calc cell values (by row and column)
- All FTE savings values
- All CODN values by year

**Naming conventions:**
- Profile inputs: `Rev`, `Employees`, `ITHeadcount`, `Ch1Priority`, etc.
- Benefit callouts: `B{n}_annualCallout`, `B{n}_3yrCallout`
- Calc table cells: `B{n}_{row}{col}` (1-based row, 1-based col)
- CODN by year: `CODN_Y1`, `CODN_Y2`, `CODN_Y3`
- Net benefit by year: `NetBen_Y1`, `NetBen_Y2`, `NetBen_Y3`

**Verify named ranges before building Phase 4:**
```python
from openpyxl import load_workbook
wb = load_workbook('workbook.xlsx')
for name in sorted(wb.defined_names.keys()):
    dest = list(wb.defined_names[name].destinations)
    print(f'{name}: {dest}')
```

## Formula Complexity -- the calc-engine tiering decision

This decision is made once, at the Phase 4 gate (WBS.md 4-01), and determines which pattern in `modules/calc_engine.md` the project uses. Do not default to LibreOffice recalc; tier the workbook first.

| Tier | Formula profile | Engine | Notes |
|------|-----------------|--------|-------|
| 1 | Simple arithmetic, lookups, averages; no cross-sheet array logic | Hand-port to Python (calculator.py constants + functions) | No runtime dependency. Fastest and lightest, but the port must be manually re-verified if the model's *logic* changes, not just its data. This is what VLG did. |
| 2 | VLOOKUP/INDEX-MATCH/SUMIFS-level complexity, multi-sheet references, but nothing volatile or array-based | `xlcalculator`, in-process | New default. No subprocess, no ~300MB LibreOffice footprint. Reuse across projects -- this is the reusable, lighter-weight replacement for the old default. |
| 3 | LAMBDA, dynamic arrays (UNIQUE, FILTER, SORT, XLOOKUP), volatile functions (RAND, NOW, INDIRECT), or anything xlcalculator fails to parse | openpyxl + LibreOffice headless | Last resort only. Requires Cloud Run 2Gi hosting, never Render free tier (P028). |

**How to tier a workbook:** visually inspect the formula bar on every output cell the app reads. If everything is Tier 1, hand-port. If anything is Tier 2, use xlcalculator for the whole workbook (mixing engines per-cell is not worth the complexity). Only drop to Tier 3 if something in the workbook genuinely defeats xlcalculator -- confirm this with a real test (see Part 2, Step 4) before committing to the heavier engine.

## Assumption Overrides

- All user-adjustable assumption fields must be on a dedicated sheet (e.g., `Discovery`)
- Each field needs a named range AND a (row, col) mapping for the `_DISC_MAP` constant in calculator.py
- Percentage fields: store as decimal in the workbook (e.g., 0.12 for 12%); convert in the app when writing
- Document the complete field list in CLAUDE.md under "Assumption Fields"

## Activation Matrix

If benefits are activated by challenge priority:
- Store the binary activation matrix on the `Data` sheet
- Provide named ranges `InclBen01` through `InclBen{n}` (or equivalent) that return 1/0 based on priorities
- The app reads these to determine which benefit slides to include in the report

---

# Part 2: Audit Checklist (Workbooks Handed to You)

Two passes, at two different points in the WBS:

- **Phase 0 -- structural pass (Steps 1-2 only):** lightweight, since the workbook handed off at project start is often not final. The client-facing model-building engagement that produces this workbook happens outside this workflow -- Claude never has a hand in that step; the workbook shows up partially finished and gets completed manually before Phase 4.
- **Phase 4 -- full audit (all steps):** run once the workbook is final, before building the calculations engine. Issues caught here cost 30 minutes to fix; issues caught mid-build cost days.

## Step 1: List All Named Ranges

```python
from openpyxl import load_workbook
wb = load_workbook('workbook.xlsx')
for name in sorted(wb.defined_names.keys()):
    dest = list(wb.defined_names[name].destinations)
    print(f'{name}: {dest}')
```

**Check:** Are named ranges present for every input the app will write and every output the app will read? If not, add them to the workbook now.

## Step 2: Check Sheet Names

```python
wb = load_workbook('workbook.xlsx')
print(wb.sheetnames)
```

**Check:** Do sheet names match expected conventions? Are there spaces in names? Document exact names in CLAUDE.md.

## Step 3: Identify Formula Complexity and Assign a Tier

Visually inspect the formula bar on key output cells. Flag any:
- LAMBDA functions
- Dynamic array functions (UNIQUE, FILTER, SORT, XLOOKUP)
- Complex nested formulas referencing multiple sheets
- Volatile functions (RAND, NOW, INDIRECT)

**For each flagged formula:** note whether it's Tier 1, 2, or 3 per the table in Part 1. The highest tier found across all output cells sets the engine for the whole workbook. Record the tier decision in CLAUDE.md's Key Decisions Log.

## Step 4: Test the Chosen Engine

For Tier 2 (xlcalculator):
```python
from xlcalculator import ModelCompiler, Evaluator
compiler = ModelCompiler()
model = compiler.read_and_parse_archive('workbook.xlsx')
evaluator = Evaluator(model)
val = evaluator.evaluate("Summary!NamedRangeHere")
print(val)
```
Compare against the value Excel shows for the same inputs. If it diverges, either the formula needs reimplementing in Python (drop to Tier 1 for that value) or the workbook needs to move to Tier 3.

For Tier 3 (LibreOffice):
```python
import shutil, subprocess, tempfile, openpyxl
from pathlib import Path

def test_lo_recalc(wb_path, named_range, expected_value):
    tmp = tempfile.mkdtemp()
    tmp_wb = Path(tmp) / 'test.xlsx'
    shutil.copy(wb_path, tmp_wb)
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'xlsx',
                    '--outdir', tmp, tmp_wb.as_uri()], capture_output=True)
    wb2 = openpyxl.load_workbook(tmp_wb, data_only=True)
    dest = list(wb2.defined_names[named_range].destinations)[0]
    val = wb2[dest[0]][dest[1]].value
    print(f'{named_range}: {val} (expected: {expected_value}, match: {val == expected_value})')
    shutil.rmtree(tmp)
```

Run for each KPI output. If values differ from Excel, document the divergence in CLAUDE_problems.md.

## Step 5: Check for Lock Files

If the workbook is open in Excel during development, LibreOffice (Tier 3) will fail to open it. Ensure the workbook is closed before running any server-side calculation.

## Audit Sign-Off Checklist

- [ ] Named ranges: all inputs and outputs covered
- [ ] Sheet names: documented in CLAUDE.md; no spaces; stable
- [ ] Formula complexity: tiered per cell; engine chosen and recorded in CLAUDE.md
- [ ] Chosen engine's outputs match Excel for default inputs
- [ ] Workbook saved as .xlsx (not .xlsm) -- macros stripped; engine-safe

---

# Part 3: Workbook Lifecycle -- Refreshing a Live Workbook

Most client workbooks get updated periodically after launch (new peer benchmarks, new assumption defaults, corrected reference data). The client never has backend access -- they update their own copy of the spreadsheet and send it to Ben, who needs to get it live. Full implementation lives in `modules/workbook_lifecycle.md`; this section covers the workbook-side conventions that make a safe refresh possible.

- The live workbook is stored outside the Docker image and outside git-tracked reference data (a cloud storage bucket, not a file baked into the container). This is what actually enables "no redeploy."
- Reference data extracted from the workbook (Tier 1 hand-ported constants, or the xlcalculator model for Tier 2) must be loaded through a callable that can be re-run on demand, never only at module import time.
- Every refresh re-runs the Part 2, Step 1-3 audit automatically against the new file before it goes live. If the new workbook is missing a named range, has a renamed sheet, or shifts a formula into a higher tier, the refresh is rejected and the app keeps serving the last good version.
- Keep the last several workbook versions in the bucket with a timestamp suffix. Log every reload -- timestamp, filename, who triggered it -- in PROJECT_STATE.md's Authoritative Source Registry, the same place git pushes and deploys are already logged.
