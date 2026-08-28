# K1x PMTC Assessment -- Project Reference

**Purpose:** Authoritative project reference for Claude. Read at every session start before any substantive work.

**Last updated:** 2026-08-28 19:46 EDT (Open Item #12 -- launch-blocking iframe-embed cookie fix implemented and verified with a real `Set-Cookie` header, not yet deployed)

> **`AFTER_YOU_PULL.md`'s launch-blocking cookie bug is fixed in code, not yet deployed.**
> The tool has a custom domain (`https://k1x-pmtc.geniusdrive.com/`), added by
> Tristen. Open Item #12 (Flask session cookie had no `SameSite`/`Secure`,
> dropping the session inside the K1x iframe embed) is fixed in
> `app/app/__init__.py` (2026-08-28 19:46 EDT) and verified with a real
> `Set-Cookie` header via the Flask test client -- both the production path
> (`SameSite=None; Secure`, no `.env` present) and the local-dev opt-out
> (`SameSite=Lax`, `.env`'s `SESSION_COOKIE_SAMESITE`/`SESSION_COOKIE_SECURE`).
> **Still needs a `PmtcApp` redeploy to go live**, and per `AFTER_YOU_PULL.md`
> section 3, still needs a real cross-site iframe check afterward -- a
> Set-Cookie header proves the config, not that a real browser accepts the
> cookie in that context. Delete this banner once both are done.

---

## EFFICIENCY DIRECTIVE -- STANDING RULE

Efficiency is a primary objective in all work.

- **Changes Claude can make:** Advise Ben first, then implement immediately unless told otherwise.
- **Changes Ben needs to make:** Advise clearly -- what to change, why, and how.
- Minimize round-trips. Batch related changes. Don't ask for confirmation that can reasonably be inferred.
- **Ben will name the file and approximate location when flagging an issue.** Go straight to the fix.
- **Explicit confirmation is required before proceeding on any plan.** Firm standing rule.
- **Calibrate confidence.** Flag uncertainty explicitly. Do not state compaction reconstructions as facts.
- **No em dashes** -- use en dashes (--) or restructure.
- **No multiple-choice question pickers.** Ask in plain text. Ben's answers are always free text.

---

## SESSION-START PROTOCOL -- MANDATORY

Before any research, coding, or content work, Claude MUST:
1. Read `CLAUDE.md` (this file)
2. Read `PROJECT_STATE.md` for current open/closed status
3. Read `STANDING_RULES.md` -- required before any build operation
4. Read `CLAUDE_problems.md` for any pattern relevant to the current task
5. Read `PLATFORM.md` if about to begin any build operation
6. If working on scoring/weighting/peer-comparison logic, re-verify against the live workbook -- this model has changed shape at least once already (12 dimensions/10 goals down to 10 dimensions/6 goals, tracked via red-cell-fill marking inactive rows) and could change again.
7. Write/verify the session-start verification marker (`.session_protocol_verified`, same folder as this file) once steps 1-4 are confirmed done via actual tool calls this turn -- see STANDING_RULES.md's SESSION-START AND COMPACTION RECOVERY PROTOCOL section for the full mechanism.

---

## Project Overview

**Client:** K1x
**Deliverable:** Web-based Capability & Maturity Assessment ("PMTC" -- Private Market Tax Capability). Embedded (iframe) on a K1x-hosted site. Scores a firm across 10 K-1 processing/tax-workflow capability dimensions on a 0-5 maturity scale, compares against peer benchmarks, and surfaces goal-aligned priority gaps. A downloadable Output Report (HTML-to-PDF, not PPTX -- see Key Decisions Log) is planned; a full 12-page mockup already exists (dummy scenario, built and delivered 2026-08-28) but isn't wired into the live app yet -- see Open Items.
**Primary users:** Prospective/current K1x clients (accounting firms, family offices, financial institutions, funds, tax-exempt orgs) fill out the tool anonymously; K1x sales/CS and the firm's own staff read the Results output. Lead capture (name/company/email) happens at the "Get My Report" step, not at intake.
**Model:** Profile (org name, industry, 6 goal priorities) -> Assessment (10 capability ratings, None/Ad-Hoc/Standardized/Automated/Integrated/Autonomous = 0-5) -> Calculation (per-capability score, overall average, peer comparison, goal-weighted priority-gap ranking) -> Results (score ring, maturity curve, strengths/opportunities, lead-capture modal) -> [future phase] Output Report (HTML-to-PDF).

**Note on scope vs. the template's usual shape:** this project has no dollar-denominated ROI/investment model, no CODN, no benefit calculators. It is a pure capability-maturity scoring and peer-benchmarking tool. Sections below that reference "benefits" or "investment" in the standard template are marked N/A.

---

## File Locations

All files in: `C:\Users\Ben\Documents\GENIUS DRIVE\GD Projects\K1x\PMTC assessment\`

| File | Purpose | Status |
|------|---------|--------|
| `Application\CLAUDE.md` | This file | Maintain actively |
| `Application\CLAUDE_problems.md` | Failure patterns and mitigations (shared template, no K1x-specific entries yet) | Maintain actively |
| `Application\PROJECT_STATE.md` | Running state: open items, decisions log | Maintain actively |
| `Application\SESSION_LOG.md` | Timestamped session log | Maintain actively |
| `Application\STANDING_RULES.md` | Behavioral rules | Read-only reference |
| `Application\PLATFORM.md` | Web stack patterns | Read-only reference |
| `K1x PMTC Assessment.xlsx` | Source workbook -- source of truth for all model logic | Reference -- do not modify |
| `K1x PMTC Assessment OLD1.xlsx` | Prior workbook version, kept alongside for reference | Do not use -- superseded |
| `wireframe\profile.html`, `assessment.html`, `results.html` | Approved (95% -- pending final client sign-off) static wireframe. Production templates in Phase 3 should match these exactly. | Reference -- do not modify directly; port into Jinja2 |
| `wireframe\DESIGN_DECISIONS.md` | Full decision log for the wireframe. Read before touching layout/copy/interaction. | Reference |
| Output Report mockup (12-page HTML + PDF, "Meridian Fund Services" dummy scenario) | Reference for the eventual live Output Report build | **Built and delivered to Ben 2026-08-28, not saved in the project folder** -- exists only in that session's conversation/downloads. Format: HTML-to-PDF via Playwright/headless Chromium, not PPTX -- see Key Decisions Log and "Output Report Slide Map" below. |
| `Application\app\` | Flask application (Phase 2+) | Not yet scaffolded -- see PROJECT_STATE.md Open Items |

---

## Workbook Structure (source of truth, verified 2026-08-26)

**Sheets:** `Profile`, `Assessment`, `Results`, `Data`. (`Sheet1` exists but is an unused stray content-revision note table -- ignore it, nothing references it.)

**Inactive-row convention:** the workbook marks retired rows with solid red fill (`FFFF0000`) rather than deleting them, consistently across `Profile`, `Assessment`, and `Data`. Confirmed 2026-08-26 across the whole workbook (not just Assessment) -- see Key Decisions Log.

**Calc-engine tier: Tier 1 (hand-port to Python).** Every formula in the workbook is VLOOKUP/HLOOKUP/RANK.EQ/COUNTIF/XLOOKUP/AVERAGE/IF -- no LAMBDA, no volatile functions, no spilling dynamic arrays. XLOOKUP appears (Results sheet) but is used as a plain scalar lookup, not a spill. Small enough that Tier 2 (xlcalculator) isn't worth the dependency.

---

## Capability Dimensions (10 active, in workbook row order)

Replaces the template's "Challenge Areas" table -- this project scores capabilities directly rather than gating benefits behind challenge ratings.

| # | Capability | Assessment row | Named ranges (`_lvl` / `_desc` / `_advice`) |
|---|------------|----------------|----------------------------------------------|
| D1 | Document Intake | 9 | `Assess_DocumentIntake_lvl/desc/advice` |
| D2 | Inventory Management | 10 | `Assess_InventoryManagement_lvl/desc/advice` |
| D3 | Data Extraction | 11 | `Assess_DataExtraction_lvl/desc/advice` |
| D4 | Data Validation | 12 | `Assess_DataValidation_lvl/desc/advice` |
| D5 | Data Review | 13 | `Assess_DataReview_lvl/desc/advice` |
| D6 | Tax Analysis & Reporting | 14 | `Assess_TaxAnalysis_Reporting_lvl/desc/advice` |
| D7 | Integration | 15 | `Assess_Integration_lvl/desc/advice` |
| D8 | Resource Structure | 16 | `Assess_ResourceStructure_lvl/desc/advice` |
| D9 | Advisory | 17 | `Assess_Advisory_lvl/desc/advice` |
| D10 | Governance & Trust | 18 | `Assess_Governance_Trust_lvl/desc/advice` |

**Retired (red-filled, do not port):** D11 Adoption Readiness (row 19), D12 Value Realization (row 20). Named ranges still exist for these (`Assess_AdoptionReadiness_*`, `Assess_ValueRealization_*`) but they are out of scope.

**Scale (all 10 dimensions, `Data!B19:C24`):** None=0, Ad-hoc=1, Standardized=2, Automated=3, Integrated=4, Autonomous=5. None is a real, valid, fully-weighted rating -- there is no N/A / exclude concept.

**Overall score:** average of the 10 active dimensions' scores, rounded to 1 decimal. (The live workbook's own `Assessment!N21` formula averages all 12 rows including the 2 retired ones -- do not copy that formula as-is; the Python port must average only the 10 active rows. Same issue in `Data!E97`, the peer-score average -- see Key Decisions Log.)

---

## Goals (6 active, Profile sheet)

| # | Goal | Section | Named range (priority input) | Weight named range |
|---|------|---------|-------------------------------|---------------------|
| G1 | Reduce Cycle Time | Evolve Capacity | `Goal_reduceTime` | `GW_1` |
| G2 | Centralize & Standardize | Evolve Capacity | `Goal_standardize` | `GW_2` |
| G3 | Support Scalable Growth | Evolve Capacity | `Goal_scalableGrowth` | `GW_5` |
| G4 | Improve Accuracy | Evolve Confidence | `Goal_accuracy` | `GW_6` |
| G5 | Elevate Client Experience | Evolve Confidence | `Goal_clientExperience` | `GW_7` |
| G6 | Goal 9 (dynamic) -- "Expand Advisory Services" if Industry=Accounting, else "Elevate Decision Support" | Evolve Capability | `Goal_advisorySvcs` (label/desc driven by `Goal9_lbl`/`Goal9_desc` formulas keyed on `Industry`) | `GW_9` |

Priority scale (`Data!B12:C16`): None=0, Low=1, Medium=2, High=3, Top=4.

**Retired (red-filled, do not port):** Strengthen Integration (`GW_3`), Reduce Total Cost (`GW_4`), Drive Team Adoption (`GW_8`), Expand Capabilities (`GW_10`). These weight ranges still exist in the workbook and resolve to 0 -- safe to leave wired but always 0 if easier than stripping them out.

**Validation (per wireframe, confirmed live):** all 6 goals must be ranked (any level, including all-None) to proceed from Profile. There is no longer a "at least one High/Top" floor -- that was dropped in wireframe decision §33.

---

## Goal-to-Dimension Weighting Model (drives the priority-gap ranking)

Each of the 10 active dimensions' "weighted gap" score (`Assessment!U` column) sums the priority weight (`GW_n`) of every goal that maps to it: **x2 if the dimension is that goal's primary capability, x1 if supporting** (per `Data!B43:E56`), then adds the dimension's own strength rank (`S` column -- rank 1 = highest raw score) as a way of biasing toward dimensions that are both goal-relevant and currently weak. The `T` column then ranks all 10 dimensions by that composite `U` value; Results pulls the top 3 as "priority areas to improve" and the top 3 by raw score (`S` column) as "where you scored highest." This logic isn't written up anywhere else -- confirmed by reading the formulas directly, not documented by the client. Re-verify against the live workbook if goal or dimension counts change again.

---

## Investment Model

**N/A.** No dollar-denominated ROI/investment model exists in this workbook. Do not add one without an explicit request -- this is a maturity-assessment tool, not a business-value calculator.

---

## Output Report Slide Map

**Built once, paused.** A real 12-page slide map exists as an HTML+PDF mockup (dummy "Meridian Fund Services" scenario, uniform 1280x720 pages, K1x's own Evolve Capacity/Confidence/Capability framework as the connective thread, real curve chart and bar chart ported directly from `results.html`'s own JS/CSS) -- built and delivered to Ben 2026-08-28 12:46-13:05 EDT, not saved in the project folder (conversation-only, see SESSION_LOG.md for the full build history). Format is HTML-to-PDF via Playwright/headless Chromium, not PPTX. Ben paused ("put a pin") to prioritize hosting; the live tool has since deployed with its current interim "Get My Report" modal (captures lead info, promises an emailed report, sends nothing yet -- Q3/email delivery still open). Next steps when this resumes: wire the mockup's real design/layout to actual per-user session data instead of the dummy scenario, and resolve Q3 so something can actually be sent. Two known issues flagged when the mockup was built, not yet fixed: the maturity-curve page's Your-Score/Peer-Leaders marks can sit on top of each other when they're numerically equal (a data-coincidence, not a bug -- the curve component has no collision handling for it); the testimonials slide had font-substitution overlap artifacts in the build sandbox (`Outfit`/`Play` weren't installed/fetchable there) -- fix is for Ben to export that one slide to PNG from PowerPoint on his own machine.

---

## Key Decisions Log

| Decision | Rationale |
|----------|-----------|
| Calc engine: Tier 1 (hand-port to Python) | Workbook has no LAMBDA/dynamic-array/volatile formulas; simple enough that xlcalculator's dependency isn't worth it. Confirmed 2026-08-26. |
| 10 active capability dimensions, not 12 | Workbook marks Adoption Readiness and Value Realization red-filled/inactive, consistently across Profile, Assessment, Data, and Results staging rows. Matches the wireframe's `CAPS` array (already built to 10) exactly. Confirmed with Ben 2026-08-26/27. |
| 6 active goals, not 10 | Same red-fill convention retires Strengthen Integration, Reduce Total Cost, Drive Team Adoption, Expand Capabilities. Matches wireframe's `GOALS` array. Confirmed 2026-08-26/27. |
| None = literal 0, no N/A/exclude concept | Ben confirmed 2026-08-27: "None" is a valid, real rating that scores 0 and is averaged in normally. This resolves all of the parked questions in the old `OPEN_QUESTIONS.md` (denominator adjustment, N/A chart rendering, N/A in the gap list, minimum-rated floor) -- none of them apply anymore. That file is fully resolved as of this decision. |
| Peer comparison data source -- **SUPERSEDED 2026-08-28, see CLAUDE_problems.md P047** | Original 2026-08-27 decision (below, struck through) conflated two different tables. There are actually two separate peer-data tables on `Data`: `B27:G39` ("Peer Comparison Data," 5 industry columns, all currently identical seed values) and `D84:E96` (a single column literally headed "PEER LEADERS"). Only the second is ever actually referenced by a live formula for a *score* -- `Results!F7`/`R_peerScore` is `=Data!E97`, which averages `D84:E96`'s 10 active rows. `B27:G39`'s per-capability score columns (rows 28-39) are never referenced by any formula anywhere in the workbook; only its row 40 (Peer Count) is, via `Results!F9`'s HLOOKUP. `calculator.py`'s `PEER_SCORES` had been ported from `B27:G39` (giving a peer score of 1.9) instead of `D84:E96` (the real source, 2.6) -- found when Ben flagged the displayed Peer Leaders number "doesn't look right." Fixed 2026-08-28: `PEER_SCORES` now sourced from `D84:E96`; `PEER_COUNTS` unchanged (still correctly sourced from `B27:G40` row 40, the one part of that table that's actually live-wired). Re-verified against Ben's 2026-08-28 refreshed workbook -- both tables unchanged from the version this was first (mis-)ported from. ~~Ben confirmed 2026-08-27 these are seed/placeholder values, "as complete as it can be until we get actual data rolling in." Not a bug to chase -- implement faithfully as-is (including that all 5 industries currently show identical peer averages), swap in real data later via a normal workbook refresh (see `modules/workbook_lifecycle.md`), no code change needed.~~ That confirmation is still accurate for what it was actually about (the *industry-segmented* seed data, `B27:G39`) -- it just wasn't the table feeding the displayed score. |
| Total-score and peer-score averages -- **CORRECTED 2026-08-28** | Original 2026-08-27 claim (that `Assessment!N21` and `Data!E97` both average across all 12 rows including the 2 retired ones) was wrong -- re-checked directly against the live formulas while investigating P047: `N21` is `=ROUND(AVERAGE(N8:N18),1)` (rows 19-20, where the 2 retired capabilities' scores live, are outside that range) and `E97` is `=ROUND(AVERAGE(E85:E94),1)` (same story -- rows 95-96 are outside it). Both workbook formulas already correctly average only the 10 active rows; no 12-row contamination exists. This doesn't change any code -- `calculator.py`'s Python port already independently averages only the 10 active `CAPABILITY_KEYS`, which was already correct and still is -- it just corrects the *reason* given for that choice. Also surfaced in the same investigation: both formulas wrap their `AVERAGE()` in `ROUND(...,1)`, which Python's built-in `round()` does not reliably match for a sum of decimal (non-integer) inputs landing exactly on a .x5 boundary (`round(2.55, 1)` is `2.5` in Python, `ROUND(2.55,1)` is `2.6` in Excel) -- see `_excel_round()` in `calculator.py` and CLAUDE_problems.md P047, added to guard `your_score`, `peer_score`, and the per-capability gap deltas against this. |
| PPTX report generation deferred to its own phase -- **SUPERSEDED 2026-08-28** | Superseded on two counts: the format was never actually PPTX (HTML-to-PDF was the real agreement, prototyped 2026-08-28 12:46-13:05 EDT as a 12-page mockup -- see "Output Report Slide Map" above), and a template now exists (that mockup), it's just paused rather than blocked. Original sequencing logic (build Phases 0-4 first) still held and is why this was paused, not abandoned. Renamed Open Item #2/Phase 5/9 from "PPTX report" to "Output Report" per Ben 2026-08-28, to stop the docs describing a format that was never actually the plan. |
| Archetype band clamped at score 1 for scores below it -- **SUPERSEDED 2026-08-28** | Original 2026-08-27 decision, superseded once the workbook gained a real fifth band. `Data!B100:E104` now has an explicit score-0 band ("Stuck in the Blocks" / "Value is Unrealized") plus a real descriptive paragraph per band (column E, new). The Python port (`calculator.py`) now carries all 5 bands with their real narrative text (verified byte-for-byte against the workbook and against the matching inert JSON block in wireframe `results.html`, wireframe `DESIGN_DECISIONS.md` §45) and no longer needs the clamp -- band 0 covers the full range with no gap. The old lorem-ipsum `ARCHETYPE_NARRATIVE_PLACEHOLDER` is gone. |
| Archetype narrative text ported into `calculator.py` verbatim from the workbook / wireframe §45 | Five per-archetype paragraphs (previously nonexistent -- the wireframe used lorem ipsum, per the superseded decision above) now live in `Data!E100:E104` and in `calculator.py`'s `ARCHETYPE_BANDS`. Deliberately not ported into production `results.html` as a matching inert reference block the way §44's stat-tile sourcing was -- that block's stated purpose (holding copy for a future score-based band selection that had not been built yet) is fully satisfied once the live app actually does the score-based selection, so an inert duplicate would be redundant. 2026-08-28. |
| `Assess_*_advice` (per-capability, per-level "what to do next" text, `Data!B68:H80`) not wired into calculator.py or the three pages | Not displayed anywhere in the approved wireframe -- it's report content (`Q` column / named ranges), and the Output Report phase is paused (Open Item #2) rather than blocked -- a template/mockup already exists, it's just not wired to live data yet. Revisit when that phase resumes; the underlying `Data!B68:H80` table is fully read and documented in this session's transcript if it's needed sooner. 2026-08-27.
| Lead-capture (`POST /api/lead`) is a stub -- accepts and acknowledges, persists nothing | Data-capture method (Q2) and email delivery (Q3) are both still unconfirmed defaults in PROJECT_STATE.md. Wiring the modal to a real endpoint (rather than leaving it pure client-side, as the wireframe has it) means the UI is ready the moment Ben confirms Q2/Q3 -- only `lead_capture()` in routes.py needs to change, not the templates. 2026-08-27.
| Re-verified 10-active-capability model after Ben briefly live-tested a 12-capability variant in the workbook, then reverted it | On 2026-08-27, Ben edited the live `K1x PMTC Assessment.xlsx` (not the repo's `WORKBOOK.xlsx` copy) to make `Assessment!N19`/`N20` live `VLOOKUP` formulas (previously hardcoded `0`) and widen `Assessment!N21` and `Data!E97` to average all 12 rows instead of 10 -- effectively trialing Adoption Readiness and Value Realization as live capabilities. Both rows were still red-filled (retired) throughout, and no UI question exists for either in the approved wireframe. Ben then reverted all four formula edits back to match the repo's `WORKBOOK.xlsx` baseline exactly. The only surviving diff is `Assessment!E20` ('None' -> 'Ad-hoc'), a demo/current-state value with zero computational effect since `N20` is still hardcoded to `0` and excluded from every live formula. Net result: no scope change, no calculator.py change -- the existing 10-capability decision (row above) and the re-derive-don't-copy decision stand as-is. No further action needed unless Ben asks to formally reactivate these two dimensions (which would need new Assessment-page question cards, not just a workbook formula change).
| No authentication -- Auth0 scaffold removed, not left disabled | Ben confirmed 2026-08-26/27 this is a public tool with no login. Rather than leave the starter's `AUTH_REQUIRED=False` default in place, removed it entirely: deleted `app/auth.py`, the `AUTH_REQUIRED`/`AUTH0_DOMAIN`/`AUTH0_CLIENT_ID`/`AUTH0_CLIENT_SECRET`/`AUTH0_CALLBACK_URL` config lines and `before_request` hook registration from `app/__init__.py`, the `authlib` line from `requirements.txt`, and the Auth0 block from `.env.example`/`.env`. Note: the scaffold's `before_request_hook()` referenced `url_for('auth.login')` but no `auth` blueprint was ever defined anywhere in the starter -- it would have raised `BuildError` if `AUTH_REQUIRED` were ever flipped to `True`, so it was dead/non-functional scaffolding, not a working feature being turned off. Verified the app factory still boots and all routes resolve via the Flask test client after removal.

| Data capture (Phase 10 / Q2) schema and architecture -- resolved 2026-08-28 | Ben set up the target Google Sheet himself and defined the exact column schema directly in the workbook (`NR!G2:AM3`): row 2 is the friendly header label, row 3 is the source named range (or blank for app-generated fields), and it maps 1:1 onto the Sheet's own columns with a fixed 6-column offset -- workbook `G` (a labels-only column, never written to) is Sheet `A`; workbook `H` (Timestamp) is Sheet `B`; every column after that shifts the same 6. Data starts at Sheet row 4. Final 33-column schema: Timestamp (ET, `YYYY-MM-DD HH:MM:SS`, generated at write time -- not a workbook field), Company, Industry, 6 goal priority scores (`GW_1/2/5/6/7/9`, one per active goal -- Ben simplified away the earlier draft's separate text-label columns, numeric score only), 10 capability levels (`Assess_*_lvl`, in the same order `calculator.py` already uses internally -- document_intake first), Your score, Peer score, Number of peers, top-3 strengths, top-3 gaps (capability names), then First Name/Last Name/Email/Opt-In. Timestamp uses Python's `zoneinfo` (`America/New_York`) rather than a fixed UTC offset, to handle the EST/EDT transition correctly automatically. Row lifecycle: a row is appended the first time a session reaches Results (`POST /assessment`, right when `run_calculation()` produces results -- not `GET /results`, since a GET can refire on reload/back-navigation and a POST only fires on a real submission); if the user goes back, revises an answer, and resubmits, the same row's assessment columns are updated in place rather than a second row being appended (`session['capture_row']` correlates the two); the "Get My Report" modal (`POST /api/lead`) backfills the four lead columns into that same row, with a defensive fallback that retries the initial append if `capture_row` was never set (e.g. Sheets was unreachable when the assessment was submitted). Deliberately not carried forward from the old ITSM-shaped stub module: notification-email-on-append, since email delivery (Q3) is explicitly out of scope for this phase per Ben. `data_capture.py` rewritten from scratch against this schema; `routes.py` wired at both trigger points; verified with a mocked-Sheets test harness (no real credentials exist in this environment) covering column order, append-vs-update ranges, row-number parsing, and graceful no-op when unconfigured. See PROJECT_STATE.md's Q2 row and Open Item #7. |
| Hosting platform: AWS (confirmed 2026-08-28) | Ben confirmed this project will host on AWS, resolving Scoping Decision Q1 (was defaulting to Google Cloud Run per PLATFORM.md's template default, `modules/hosting_cloudrun.md`). No AWS hosting module exists yet in the shared template (`modules/` currently only has `hosting_cloudrun.md` and `hosting_render.md`) -- one will need to be authored once the specific AWS service is chosen. This does not block anything today: Phase 8 (hosting and deployment) is still Pending and Phases 0-4/7/10 built so far have no hosting-specific code in them (Tier 1 calc engine has no LibreOffice/subprocess dependency that would be hosting-RAM-sensitive the way P028 describes for the ITSM project). Specific AWS service (ECS/Fargate, App Runner, Elastic Beanstalk, EC2, Lambda+API Gateway) still open -- asked Ben directly. |
| Hosting platform narrowed to AWS Lambda (confirmed 2026-08-28) | Ben chose Lambda specifically, from the set of AWS service options the previous decision (above) left open. Implication for this Flask app: Lambda does not run a WSGI app natively -- will need an adapter (`awslambdaric` base image + a WSGI-to-Lambda shim, or a library like Zappa/Mangum) in front of `create_app()`, plus a Lambda Function URL or API Gateway for the public endpoint. The AWS handoff kit's `StaticSiteStack` (S3+CloudFront) does not apply here regardless of this choice, since this app has a real backend; CloudFront, if used at all, would sit in front of the Lambda only for a custom domain/cert, not for serving static content. Phase 8 (hosting and deployment) is still Pending -- nothing built yet. |

| Lambda hosting architecture -- implementation specifics (drafted 2026-08-28, not yet deployed) | Adapter: `asgiref.wsgi.WsgiToAsgi` wraps the existing `create_app()`, then `mangum.Mangum(asgi_app, lifespan="off")` wraps that -- Flask is WSGI, a Lambda Function URL needs ASGI, and a Function URL's event shape matches Mangum's default expected shape (API Gateway HTTP API v2) so no extra Mangum config is needed. Packaging: local-pip-first bundling (`pip3 install --platform manylinux2014_aarch64 --only-binary=:all: ...`) rather than requiring Docker like `handoff/infra`'s `MailStack` does -- works from Ben's Windows machine with no Docker daemon, only possible because `app/requirements-lambda.txt` (a new, Lambda-only, trimmed dependency list) is pure Python; falls back to Docker-based bundling automatically if the local install ever fails. `requirements-lambda.txt` deliberately excludes `gunicorn` (unneeded under Mangum), `matplotlib`/`python-pptx` (only used by `report.py`, confirmed via `grep` to be unimported/dead code today), and `Flask-Session` (listed in the main `requirements.txt` but never wired into `app/__init__.py`, confirmed in a prior session) -- re-enabling any of those features later requires adding the package back to this specific file. Two bugs caught and fixed via real `cdk synth` runs in a cloud-sandbox scratch project before anything was written to the real repo: an ESM `__dirname` `ReferenceError` (fixed with the standard `path.dirname(fileURLToPath(import.meta.url))` polyfill, made explicit rather than relying on `tsx`'s CJS-interop the way the existing handoff stacks implicitly do) and a `Number("")` empty-string-to-`0` coercion that silently produced a 0MB/0s Lambda (fixed in `infra/bin/app.ts` by checking the raw context string's truthiness before calling `Number()`, since this project's `cdk.json` convention leaves unset context values as `""` rather than deleting the key). Verified beyond `cdk synth`: a real simulated Lambda Function URL invocation of the actual `create_app()` and actual templates (staged from Ben's machine), confirming `GET /` -> 302 `/profile` and `GET /profile` render correctly with zero Flask app code changes. Secrets (`FLASK_SECRET_KEY`, `GOOGLE_CREDENTIALS_JSON`) are passed as plain Lambda environment variables for now, same as `MailStack`'s pattern -- flagged in `infra/lib/app-stack.ts`'s own prop comment as worth moving to Secrets Manager once this tool handles real client data rather than the current test Sheet. Files: `Application/infra/` (new CDK app: `lib/app-stack.ts`, `bin/app.ts`, `cdk.json`, `package.json`, `tsconfig.json`, `README.md`), `Application/app/lambda_handler.py`, `Application/app/requirements-lambda.txt`. Not yet deployed -- see PROJECT_STATE.md Phase 8 and SESSION_LOG.md for status. |
