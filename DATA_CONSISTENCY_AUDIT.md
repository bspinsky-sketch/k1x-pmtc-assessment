# Output Report -- Dynamic Data Audit

**Purpose:** Steps 2 and 3 of Ben's data-consistency test plan (2026-08-30): identify which Output Report pages carry session-dependent ("dynamic") data, and enumerate the specific objects on each that hold it. This document is inventory only -- it does not yet verify each object's correct source (step 4) or check that sources agree slide to slide (step 5). Those come next, after this is reviewed.

**Method:** Read every page in `output_report/` directly off the device (not from memory), cross-referenced against `calculator.py`'s `run_calculation()` (the single function that will eventually feed all of these pages from one real session) and the workbook conventions already documented in `CLAUDE.md`.

---

## A. Pages with session-dependent data (in scope for steps 4/5)

| Page | Title | Why it's dynamic |
|---|---|---|
| `01-cover.html` | Cover | Client company name only. |
| `02-goals.html` | What You Told Us | Company, industry, and each of the 6 goals' priority ranking; one goal's display name/description also depends on industry. |
| `03-how-scored.html` | How This Is Scored | The maturity curve's three plotted points (your score, recommended target, peer score) and which of the five zone cards is marked "active." |
| `04-capability.html` | Score by Capability | All 10 capabilities' own score, peer score, and ahead/behind styling. |
| `05-where-you-stand.html` | Where You Stand Today | Overall score ring, maturity band name, narrative text, peer ring, peer count, industry-dependent peer label, and the two strengths/gaps cards (3 rows each). |
| `06-solutions.html` | Solutions | The 3 priority gaps mapped to products (`GAPS`), and their names/deltas. |
| `07/08/09-roadmap.html` | Your Roadmap (parts 1-3) | Each of the 10 capabilities' current level (`CAPABILITY_LEVELS`), which drives the current-state description, the next-step advice, and the maturity-ladder dots shown for that capability. |

## B. Pages with no session-dependent data (out of scope)

| Page | Why it's excluded |
|---|---|
| `10-success-story.html` | Real named-client testimonials, fixed regardless of who the report is for. |
| `11-trust.html` | Platform-wide scale/trust stats (firm counts, funding), fixed regardless of client. |
| ~~Page 12 (not yet built)~~ Cancelled 2026-08-30 per Ben -- there will be no page 12, the deck is final at 11 pages. | Was going to be sourced from the live app's platform-general benchmark stats, not tied to the assessed client's own answers -- moot now. |

---

## C. Objects, by page

### 02-goals.html

| Object | Current value | What it represents | Current code shape |
|---|---|---|---|
| Company name (2 places: told-card + footer) | "Meridian Fund Services" | `company` | Hardcoded text, no instance object |
| Industry (told-card) | "Accounting" | `industry` | Hardcoded text |
| 6x goal priority indicator (segmented dots + High/Top/Medium/Low label) | Reduce Cycle Time: High; Centralize & Standardize: Top; Support Scalable Growth: Medium; Improve Accuracy: Top; Elevate Client Experience: Low; Expand Advisory Services: Medium | `goals` (dict of goal key -> 0-4, `PRIORITY_LABELS`) | Hardcoded per-row HTML, no instance object |
| Goal 9 display name + description | Always "Expand Advisory Services" / its Accounting-branch description | Should flip on `industry` (Accounting -> "Expand Advisory Services", else -> "Elevate Decision Support"), per the live app's own `GOAL9_BY_INDUSTRY` logic | **Hardcoded to the Accounting branch only -- no conditional exists on this page at all.** |

### 03-how-scored.html

| Object | Current value | What it represents | Current code shape |
|---|---|---|---|
| Curve plot: `now` | 3.0 | `your_score` | JS literal in `chart.render({ now: 3.0, target: 3.6, peer: 2.6 })` |
| Curve plot: `target` | 3.6 | `RECOMMENDED_TARGET` (a true global constant in `calculator.py`, not per-session) | Same JS literal |
| Curve plot: `peer` | 2.6 | `peer_score` | Same JS literal |
| Active zone card + "You are here" tag | 4th card ("Transforming the Workflow"), tag reads "3.0" | `band_name` (which of the 5 `ARCHETYPE_BANDS` `your_score` falls into) + `your_score` | Hardcoded `class="zone-card active zone-card-scrim"` directly on one card's HTML -- no logic selects it |
| 5 zone narrative texts | Static, one paragraph per band | Master content (same for every client, like `CURRENT_DESCRIPTIONS`) | Static HTML, correctly not treated as per-session |

### 04-capability.html

| Object | Current value | What it represents | Current code shape |
|---|---|---|---|
| 10x capability row: your-score bar width + ahead/behind color | Document Intake 2.0 (40%, behind); Inventory Mgmt 3.0 (60%, ahead); Data Extraction 1.0 (20%, behind); Data Validation 2.0 (40%, ahead); Data Review 2.0 (40%, behind); Tax Analysis 3.0 (60%, ahead); Integration 1.0 (20%, behind); Resource Structure 2.0 (40%, ahead); Advisory 1.0 (20%, behind); Governance & Trust 2.0 (40%, ahead) | `bar_rows[k].you`, plus ahead/behind derived from `you` vs `peer` | Hardcoded inline `style="width:...%"` and class per row -- no instance object at all, not even a literal JS array |
| 10x peer bar width + peer label | Document Intake 2.5; Inventory Mgmt 2.2; Data Extraction 2.1; Data Validation 1.9; Data Review 2.3; Tax Analysis 2.3; Integration 1.4; Resource Structure 1.5; Advisory 1.2; Governance & Trust 1.7 | `bar_rows[k].peer` | Same, hardcoded inline |
| Lede's peer count | "133 Accounting peers" | `peer_count` + `industry` | Hardcoded text in the lede sentence |

### 05-where-you-stand.html

| Object | Current value | What it represents | Current code shape |
|---|---|---|---|
| Score ring (number + arc) | 3.0/5 | `your_score` | Hardcoded `ring-num` text plus a hand-computed `stroke-dashoffset` |
| Band name / subtitle | "Transforming the Workflow" / "(Value is Accelerating)" | `band_name` / `band_subtitle` | Hardcoded text |
| Narrative (3 paragraphs) | Matches page 3's active-zone narrative verbatim | `narrative_sentences` | Hardcoded `<p>` tags |
| Peer ring (number + arc) | 2.6/5 | `peer_score` | Hardcoded `peer-num` text plus hand-computed arc |
| Peer eyebrow label | "Where your Family Office / Wealth Management peer leaders ranked" | Industry-dependent label, should read whatever `industry` is | Hardcoded text |
| Peer note | "Leaders are the top percentile out of 43 peers." | `peer_count` | Hardcoded text |
| "Where you scored highest" (3 rows) | Document Intake 3/5; Inventory Management 3/5; Data Extraction 3/5, each with a current-level description | `strengths` (top 3 by `strength_rank`) | Hardcoded rows |
| "Priority areas to improve" (3 rows) | Governance & Trust +0.8; Integration +0.8; Data Extraction -0.3, each with a note | `gaps` (top 3 by `gap_rank`) | Hardcoded rows |

### 06-solutions.html

| Object | Current value | What it represents | Current code shape |
|---|---|---|---|
| `GAPS` array (3 entries: key, name, delta, note) | Governance & Trust 0.8; Integration 0.8; Data Extraction -0.3 | Should equal `gaps` from `run_calculation()`, shaped identically | Real JS instance object, `var GAPS = [...]`, joined against the static `CAPABILITY_FIXES` lookup by `renderGaps()` |

### 07/08/09-roadmap.html

| Object | Current value | What it represents | Current code shape |
|---|---|---|---|
| `CAPABILITY_LEVELS` (10 keys, 0-5 each) | document_intake 2; inventory_management 3; data_extraction 3; data_validation 2; data_review 2; tax_analysis_reporting 3; integration 0; resource_structure 2; advisory 1; governance_trust 0 | Should equal `capability_scores` from `run_calculation()` | Real JS instance object per file, joined against the static `CURRENT_DESCRIPTIONS`/`NEXT_STEP_ADVICE` lookups |

### 01-cover.html

| Object | Current value | What it represents | Current code shape |
|---|---|---|---|
| "Prepared for" name | "Meridian Fund Services" | `company` | Hardcoded text |
| Date | "August 28, 2026" | Report generation date (not part of `run_calculation()` or any session answer -- should just be "today" at render time) | Hardcoded text, not tied to actual render date |

---

## Preliminary observations (incidental, not yet formal step 4/5 verification)

A few things surfaced just from listing objects and their current values, worth flagging now rather than sitting on until steps 4/5 formally get there:

- **02-goals.html says industry is "Accounting."** **05-where-you-stand.html's peer-eyebrow label says "Family Office / Wealth Management."** Same fictitious client, two different industries stated on two different pages.
- **Document Intake's own score disagrees three ways:** 04-capability.html and the roadmap's `CAPABILITY_LEVELS` both say 2, but 05-where-you-stand.html's "Where you scored highest" row says 3/5.
- **Architecture gap, not just a numbers gap:** only 06-solutions.html and the roadmap pages currently have a real, isolated instance object (`GAPS`, `CAPABILITY_LEVELS`) that a future live session could swap in directly. Pages 02, 03, 04, and 05 have no instance object at all yet -- every dynamic-looking value on those four pages is hand-typed directly into the HTML or into a one-off JS literal, which is a separate problem from whether the numbers agree, and will need its own fix regardless of what steps 4/5 find.
- **Goal 9's industry-conditional label doesn't exist on 02-goals.html at all** (already flagged before this document, included here for completeness).

Let me know if this inventory looks complete and correctly scoped before I move to step 4 (verifying each object's intended source) and step 5 (checking those sources agree across pages).
