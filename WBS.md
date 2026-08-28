# WBS.md -- Web Project Work Breakdown Structure

**Template version:** 2.0 (restructured 2026-08-14 -- design moved to the front, tiered calc engine, workbook lifecycle phase added; derived from v1.0/ITSMweb, 2026-06-18)
**Usage:** Copy to new project folder. Add project-specific tasks to each phase. Check off tasks as completed. Respect gate order.

---

## Gate Notation

- **GATE: [condition]** -- next phase cannot begin until condition is confirmed
- Gates are hard stops. Do not proceed past a gate without explicit confirmation from Ben.

---

## What changed in v2.0

- Design work (formerly Phase 8a/8b, gated behind hosting and auth) now happens at Phase 1, immediately after the workbook and requirements arrive. Clients want a look-and-feel wireframe fast, before any backend exists.
- Because design is locked at Phase 1, there is no separate "rebuild with confirmed design" phase anymore -- production templates are built once, against the approved design, at Phase 3.
- The calculations engine (Phase 4) now opens with an explicit formula-complexity tiering step instead of defaulting straight to openpyxl + LibreOffice. See `modules/calc_engine.md`.
- New Phase 11, Workbook Lifecycle Setup: most client workbooks get refreshed periodically after launch, and the client never has backend access, so the app needs a way to go live on a new workbook version without a code deploy. See `modules/workbook_lifecycle.md`.
- The Phase 0 workbook audit is now a lightweight structural pass only -- workbooks frequently arrive from the client-facing model-building engagement still partially finished. Full named-range completeness is confirmed at the Phase 4 gate instead.

---

## Phase 0: Pre-Project Setup

| ID | Task | Notes |
|----|------|-------|
| 0-01 | Clone starter repo | `git clone https://github.com/bspinsky-sketch/web-project-starter [project-folder]` |
| 0-02 | Create project folder in GENIUS DRIVE | Copy template folder docs into it |
| 0-03 | Create GitHub repo for this project | bspinsky-sketch account; enable Git LFS |
| 0-04 | Activate shared venv | `& "C:\Users\Ben\venvs\webprojects\Scripts\Activate.ps1"` |
| 0-05 | Copy source workbook (.xlsx) into project folder | Add to .gitattributes for LFS tracking. The workbook comes from a separate, non-Claude client engagement and may still be partially finished. |
| 0-06 | Copy source PPT template (.pptx) into project folder | Add to .gitattributes for LFS tracking |
| 0-07 | **Workbook structural pass** | Sheet names, obvious named ranges only -- see WORKBOOK_CONVENTIONS.md Part 2, Steps 1-2. Not a full audit; the workbook is often not final yet. |
| 0-08 | **PPT audit** -- run shape name audit script | See PPT_CONVENTIONS.md Part 2 |
| 0-09 | Fill CLAUDE.md placeholders | Client, deliverable, file paths |
| 0-10 | Draft challenge-benefit matrix in CLAUDE.md | From the live workbook -- never from memory. Mark provisional if the workbook is not final. |
| 0-11 | Set up .env from .env.example | FLASK_SECRET_KEY, GMAIL_*, AUTH0_* stubs |
| 0-12 | Commit initial project files | `git add -A && git commit -m "Session 1: project init"` |

GATE: Workbook and PPT template received; structural pass complete (0-07, 0-08 passed). Full named-range completeness is confirmed later, at the Phase 4 gate, not here.
GATE: CLAUDE.md placeholders filled; challenge-benefit matrix drafted, marked provisional if the workbook is not yet final (0-09, 0-10)

---

## Phase 1: Design Lock and Wireframe

| ID | Task | Notes |
|----|------|-------|
| 1-01 | Run the `design-system-creation` skill against the client's brand materials | Extracts real tokens (color, type, spacing, shape) from a live site or existing brand deck; flags anything in a handoff doc that doesn't match reality. Falls back to Design_Questionnaire.docx if no existing brand system to extract from. |
| 1-02 | Draft page-flow requirements from the workbook, even if it's not final | What screens are needed, what inputs/outputs each one shows -- not final calc logic, just enough to wireframe |
| 1-03 | Build static wireframe pages | No Flask, no backend -- plain HTML per screen, styled with the tokens from 1-01 |
| 1-04 | Maintain a DESIGN_DECISIONS.md log scoped to the wireframe | Write each decision before implementing it, not after, so it survives an interrupted session or compaction |
| 1-05 | Internal review with Ben | |
| 1-06 | Get client sign-off on the wireframe | This is the design lock: colors, fonts, logo, layout, and page flow all confirmed here |

GATE: design-system-creation skill run (or Design_Questionnaire.docx completed) and tokens documented, with verification status noted per token (confirmed-live vs. inherited/unverified)
GATE: Wireframe explicitly approved by Ben and the client before any Flask or backend work begins

---

## Phase 2: Flask Scaffold

| ID | Task | Notes |
|----|------|-------|
| 2-01 | Rename blueprint folder from project_name to project codename | Update app/__init__.py import |
| 2-02 | Verify `flask run` starts without error | GET / returns 200 |
| 2-03 | Set up structural baseline | `python3 check_structure.py --update` |
| 2-04 | Add project to PROJECT_STATE.md phase table | |

GATE: `flask run` starts; GET / returns 200; `bash check_files.sh` all pass

---

## Phase 3: Production Templates and Input Forms

| ID | Task | Notes |
|----|------|-------|
| 3-01 | Build Profile form (step1_profile.html) against the approved Phase 1 design | Company, revenue, employees, IT headcount |
| 3-02 | Build Challenges form (step2_challenges.html) against the approved design | Priority selection per challenge area |
| 3-03 | Wire routes.py: GET /, POST /step1_profile, GET /challenges, POST /step2_challenges | |
| 3-04 | Add session storage for profile and priorities | |
| 3-05 | Add back-navigation: /edit_profile pre-fills from session | Never route back to / (P036) |
| 3-06 | Add comma formatting to numeric inputs | type="text" class="num-fmt"; JS focus/blur handlers |
| 3-07 | Confirm production templates match the approved wireframe | Design was locked at Phase 1 -- there should be no separate rebuild pass later in this project |
| 3-08 | Run check_files.sh | All 4 layers must pass |

GATE: Profile and Challenges forms submit; session stores correctly; templates match the approved design; check_files.sh passes

---

## Phase 4: Calculations Engine

| ID | Task | Notes |
|----|------|-------|
| 4-01 | Tier the workbook's formulas | Tier 1 (simple lookups/averages) hand-port to Python. Tier 2 (VLOOKUP/INDEX-MATCH/SUMIFS, no volatile or array formulas) use xlcalculator in-process. Tier 3 (LAMBDA, dynamic arrays, volatile functions) fall back to LibreOffice headless. See modules/calc_engine.md and WORKBOOK_CONVENTIONS.md Part 1. |
| 4-02 | Run the full named-range audit now that the workbook is final | See WORKBOOK_CONVENTIONS.md Part 2, Step 1 |
| 4-03 | Implement run_calculation() per the chosen tier's pattern | See modules/calc_engine.md |
| 4-04 | Write read_defaults() -- reads workbook defaults at session/startup | |
| 4-05 | Define _DISC_MAP (assumption field -> Discovery sheet row/col), if the model has user-adjustable assumptions | |
| 4-06 | Wire Challenges POST to run_calculation() | Store kpis in session |
| 4-07 | Build stub Summary page to display KPIs | Verify values against workbook manually |
| 4-08 | Test locally with the real workbook | Compare KPI values to expected |
| 4-09 | Run check_files.sh | |

GATE: Named ranges present and complete for all inputs and outputs (4-02 passed)
GATE: KPI values match workbook for default inputs; check_files.sh passes

---

## Phase 5: PPT Generation

| ID | Task | Notes |
|----|------|-------|
| 5-01 | Inspect PPT template shapes (run audit command from PLATFORM.md) | Identify pre-filled vs empty shapes |
| 5-02 | Write generate_report() -- slide deletion pre-pass + shape population | |
| 5-03 | Add /download route | Stream .pptx as attachment |
| 5-04 | Add Download button to Summary page | |
| 5-05 | Decide chart approach: flattened image vs. native editable shapes | Still an open convention as of v2.0 -- see PPT_CONVENTIONS.md. Whatever is decided here should get written back into PPT_CONVENTIONS.md as the standard. |
| 5-06 | Smoke test: download .pptx, open in PowerPoint, verify shape values | |
| 5-07 | Run check_files.sh | |

GATE: Downloaded .pptx opens without error; key shapes populated correctly

---

## Phase 6: Email Delivery

| ID | Task | Notes |
|----|------|-------|
| 6-01 | Verify Gmail app password exists (see modules/email_gmail_smtp.md) | Ben to create dedicated Gmail address if needed |
| 6-02 | Write send_report_email() -- LibreOffice PDF + smtplib SMTP | LibreOffice is retained here for PDF conversion even on projects using xlcalculator/Python for calculation -- the RAM tradeoff that matters is the calc engine, not PDF conversion |
| 6-03 | Add /send_report route | |
| 6-04 | Add email modal to Summary page | Input: email address; confirm state after send |
| 6-05 | Test: send to real address; verify PDF attachment renders | |

GATE: Email received with PDF attachment; PDF renders correctly

---

## Phase 7: Auth Scaffold

| ID | Task | Notes |
|----|------|-------|
| 7-01 | Wire auth.py before_request_hook | AUTH_REQUIRED = False for public tools |
| 7-02 | Verify all routes pass through with AUTH_REQUIRED = False | |
| 7-03 | Document Auth0 on/off decision in CLAUDE.md | |

GATE: Auth scaffold in place; all routes return 200 with AUTH_REQUIRED = False

---

## Phase 8: Hosting and Deployment

| ID | Task | Notes |
|----|------|-------|
| 8-01 | Choose hosting platform | See modules/hosting_*.md |
| 8-02 | Set up hosting account and project | |
| 8-03 | Configure Dockerfile (if Cloud Run) | LibreOffice install (for PDF conversion); gunicorn |
| 8-04 | Write deploy.ps1 | |
| 8-05 | Add env vars to hosting platform | FLASK_SECRET_KEY, GMAIL_*, etc. |
| 8-06 | First production deploy | |
| 8-07 | Verify all routes on production URL | |

GATE: Production URL live; all routes return 200 on production

---

## Phase 9: Full Report Push

| ID | Task | Notes |
|----|------|-------|
| 9-01 | Inspect PPT template: identify all dynamic shapes | Callout tiles, tbl_calc, chart image slots |
| 9-02 | Write per-benefit chart generation | matplotlib.use('Agg') at module level, or chart.js-to-flattened-image per Phase 5-05's decision |
| 9-03 | Write tbl_calc population (named ranges B{n}_{row}{col}) | |
| 9-04 | Write summary chart generation (doughnut, waterfall, CODN, etc.) | |
| 9-05 | Implement slide deletion pre-pass for inactive benefits | Collect then delete in reverse order |
| 9-06 | Smoke test: download report with all benefits active; verify charts and tables | |
| 9-07 | Smoke test: download with partial selection; verify correct slides deleted | |
| 9-08 | Deploy to production; verify report download on production URL | |

GATE: Report downloads with correct slides, charts, and tbl_calc values for both full and partial selections

---

## Phase 10: Data Capture

| ID | Task | Notes |
|----|------|-------|
| 10-01 | Set up Google Sheets + service account (see modules/datacapture_gsheets.md) | One-time Ben action |
| 10-02 | Define capture schema (one row per session) | timestamp, company, KPIs, email (nullable), etc. |
| 10-03 | Write append_session() and update_email() | |
| 10-04 | Wire to Summary page load (anonymous) and email send | |
| 10-05 | Add GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS_JSON to hosting env vars | |
| 10-06 | Verify end-to-end: submit flow -> check Google Sheet row appended | |

GATE: Test row appears in Google Sheet after full flow; email column populated on send

---

## Phase 11: Workbook Lifecycle Setup

| ID | Task | Notes |
|----|------|-------|
| 11-01 | Provision a cloud storage bucket for the live workbook | See modules/workbook_lifecycle.md; reuses the per-project bucket pattern from modules/hosting_cloudrun.md |
| 11-02 | Move the live workbook out of the Docker image and out of module-load-time constants | App reads it from the bucket at startup and on reload, not from a file baked into the container |
| 11-03 | Build the reference-data loader as a callable, not just module-level constants | So it can re-run without a process restart |
| 11-04 | Add an authenticated /admin/reload-workbook route | Shared-secret protected, separate from Auth0 |
| 11-05 | Wire the reload route to re-run the named-range/structure audit before swapping | Reject and keep serving the last good version if the audit fails |
| 11-06 | Add a workbook version log to PROJECT_STATE.md's Authoritative Source Registry | Timestamp, filename/version, who triggered the reload |
| 11-07 | Document the client-to-Ben handoff | Client has no backend access; Ben receives the updated file and triggers the reload manually |
| 11-08 | Test: reload with a deliberately broken workbook (missing named range) | Confirm rejection and the old version stays live |
| 11-09 | Test: reload with a valid updated workbook | Confirm new values appear with no redeploy |

GATE: A workbook refresh goes live via /admin/reload-workbook with no code deploy; a broken workbook is rejected without taking the app down

---

## Phase 12: QA and Delivery

| ID | Task | Notes |
|----|------|-------|
| 12-01 | Full end-to-end QA on production URL | Profile -> Challenges -> Summary -> Report download -> Email |
| 12-02 | PPT report QA -- all slides, charts, tbl_calc values | Compare against workbook for default inputs |
| 12-03 | Edge case testing: all High, all None, mixed | Verify slide deletion and KPI accuracy |
| 12-04 | Workbook reload regression test | Re-run 11-08/11-09 once more against production |
| 12-05 | Regression test: run check_files.sh on final commit | All layers pass |
| 12-06 | Update PROJECT_STATE.md -- all items closed | |
| 12-07 | Final commit and deploy | Tag as v1.0 |
| 12-08 | Update BVF_Functionality_Library equivalent for new project | Catalog any new patterns added |

GATE: All QA items pass; all open items in PROJECT_STATE.md closed; final deploy confirmed
