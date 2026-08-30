# Output Report -- Steps 4/5 Findings: Source Verification & Cross-Page Consistency

**Purpose:** Steps 4 and 5 of Ben's test plan (2026-08-30), building on `DATA_CONSISTENCY_AUDIT.md`. For every object identified there, this confirms what it should be sourced from, then checks whether the pages that share a field currently agree. Per Ben's instruction, every fix candidate below is flagged for review, not applied yet -- each is marked mechanical or judgment call.

**Method:** Every object traced against `calculator.py`'s actual constants and `run_calculation()`'s return fields, read directly from the file, not from memory. Company/industry/goals/ratings are session inputs (Profile-page answers feeding the function), everything else is computed.

---

## Step 4: source of truth, by object

| Object (page) | Authoritative source |
|---|---|
| Company name (01, 02) | `company` -- a Profile-page input, not computed |
| Date (01) | Not part of `run_calculation()` at all. Should be the report's actual generation date, not a session answer |
| Industry (02, 04's lede, 05's peer label) | `industry` -- a Profile-page input |
| 6x goal priority (02) | `goals[key]`, a Profile-page input per goal, 0-4 against `PRIORITY_LABELS` |
| Goal 9 label/description (02) | Should switch on `industry`: "Expand Advisory Services" for Accounting, "Elevate Decision Support" otherwise, same as the live app's `GOAL9_BY_INDUSTRY` |
| Curve now/target/peer (03) | `curve.now` = `your_score`; `curve.target` = `RECOMMENDED_TARGET` (global constant, 3.6, not session-dependent); `curve.peer` = `peer_score` |
| Active zone + "You are here" tag (03) | `band_name` (which `ARCHETYPE_BANDS` entry `your_score` falls into) + `your_score` itself |
| 5 zone narratives (03) | Static master text, `ARCHETYPE_BANDS[*].narrative` -- same for every client, correctly not session-dependent |
| 10x your-score bar + peer bar (04) | `bar_rows[k].you` = `capability_scores[k]`; `bar_rows[k].peer` = `PEER_SCORES_BY_INDUSTRY[industry][k]` |
| Peer count in lede (04) | `peer_count` = `PEER_COUNTS[industry]` |
| Score ring (05) | `your_score` -- same field as 03's curve.now |
| Band name/subtitle (05) | `band_name`/`band_subtitle` -- same field as 03's active zone |
| Narrative (05) | `narrative_sentences` -- same `ARCHETYPE_BANDS` entry as 03's active zone narrative |
| Peer ring (05) | `peer_score` -- same field as 03's curve.peer |
| Peer eyebrow label (05) | `industry` -- same field as 02 |
| Peer note "N peers" (05) | `peer_count` -- same field as 04's lede |
| Strengths rows (05) | `strengths`, top 3 of `capability_scores` by `strength_rank` |
| Gaps rows (05) | `gaps`, top 3 by `gap_rank` (goal-weighted, not raw score), each row's delta = `capability_scores[k] - PEER_SCORES_BY_INDUSTRY[industry][k]` |
| `GAPS` array (06) | Should equal `gaps` above, verbatim |
| `CAPABILITY_LEVELS` (07/08/09) | Should equal `capability_scores` above, verbatim |

`PEER_SCORES_BY_INDUSTRY` is worth flagging on its own: despite the name, it's currently identical for every industry in `calculator.py` (`{industry: dict(PEER_SCORES) for industry in INDUSTRIES}`) -- only `PEER_COUNTS` actually varies by industry. That's not a bug I'm flagging, just a fact worth knowing before assuming a peer-score difference between two pages means an industry difference; it doesn't, since peer scores don't move with industry at all today.

If any of this needs to be traced back to an actual workbook cell rather than `calculator.py`'s own constant, this is exactly where I'd take you up on the named-range offer -- I didn't need it for this pass since `calculator.py`'s constants were sufficient to check page-to-page agreement.

---

## Step 5: cross-page consistency findings, most severe first

**1. The overall score and band shown on pages 3 and 5 cannot be produced by either detailed capability dataset in the deck. [Judgment call -- this is the one that needs a decision, not just a copy-fix.]**

Pages 3 and 5 both show "Your Score: 3.0" and the "Transforming the Workflow" band (`min: 3`). But averaging the 10 capability scores from either existing dataset lands far below that:
- Page 4's bars (document_intake 2.0, inventory_management 3.0, data_extraction 1.0, data_validation 2.0, data_review 2.0, tax_analysis_reporting 3.0, integration 1.0, resource_structure 2.0, advisory 1.0, governance_trust 2.0) average to **1.9**.
- The Roadmap's `CAPABILITY_LEVELS` (document_intake 2, inventory_management 3, data_extraction 3, data_validation 2, data_review 2, tax_analysis_reporting 3, integration 0, resource_structure 2, advisory 1, governance_trust 0) average to **1.8**.

Both land in the "Automating the Foundation" band (`min: 1`), two bands below what pages 3/5 actually show. This isn't a small rounding gap, it's the deck's headline number being incompatible with its own detail. There's no way to mechanically reconcile this, since it depends on which 10 capability scores are treated as ground truth -- that's the decision this flags for you, and it's the reason I'd recommend the fix strategy at the bottom of this document rather than patching numbers in place.

**2. Every one of page 4's 10 peer-score values is wrong against the real `PEER_SCORES` constant. [Mechanical.]**

| Capability | Page 4's peer value | Real `PEER_SCORES` |
|---|---|---|
| Document Intake | 2.5 | 3.5 |
| Inventory Management | 2.2 | 3.2 |
| Data Extraction | 2.1 | 3.3 |
| Data Validation | 1.9 | 2.3 |
| Data Review | 2.3 | 2.1 |
| Tax Analysis & Reporting | 2.3 | 2.8 |
| Integration | 1.4 | 2.2 |
| Resource Structure | 1.5 | 2.1 |
| Advisory | 1.2 | 1.8 |
| Governance & Trust | 1.7 | 2.2 |

Not one row matches. This whole column on page 4 needs to be regenerated from the real constant, not adjusted row by row. Worth noting as a positive: the aggregate `peer_score` (2.6) shown on pages 3 and 5 IS the correct mean of the real `PEER_SCORES` values (confirmed: sums to 25.5 over 10 capabilities, rounds to 2.6 by Excel's rounding rule) -- so the top-line peer number is already right, only this page's per-capability breakdown is wrong.

**3. Industry is stated two different ways for the same client. [Mechanical once one is chosen.]**

02-goals.html says "Accounting." 05-where-you-stand.html's peer label says "Family Office / Wealth Management." Downstream of this, 04's lede says "133 Accounting peers" while 05's peer note says "43 peers" -- both numbers are individually correct for their respective stated industry per `PEER_COUNTS`, so this is one root cause, not two separate bugs.

**4. Per-capability scores disagree across pages for several capabilities, not just Document Intake. [Mechanical, but needs one master dataset -- see recommendation below.]**

| Capability | Page 4 | Roadmap `CAPABILITY_LEVELS` | Page 5 (strengths/gaps rows) |
|---|---|---|---|
| Document Intake | 2.0 | 2 | 3 (shown as a top strength) |
| Data Extraction | 1.0 | 3 | 3 (shown as a top strength, and separately as a gap at -0.3) |
| Integration | 1.0 | 0 | not shown as a row, but implied ~3.0 by its gap delta (see finding 5) |
| Governance & Trust | 2.0 | 0 | not shown as a row, but implied ~3.0 by its gap delta (see finding 5) |

**5. The two `gaps` deltas that aren't Data Extraction's don't reconcile with any combination of real peer score and either page's current-score dataset. [Judgment call -- may just confirm finding 1's root cause, flagging separately since the math is worth seeing directly.]**

`06-solutions.html`'s `GAPS` (matching 05's "Priority areas to improve" exactly) shows Governance & Trust and Integration both at delta +0.8. Since `PEER_SCORES` for both is 2.2, a delta of +0.8 implies a current score of 3.0 for each. Neither page 4 (2.0 and 1.0) nor the Roadmap (0 and 0) has either capability anywhere near 3.0. A positive delta also reads oddly for a "priority area to improve" card in the first place, since positive means currently ahead of peers by this formula (`scores[k] - peer[k]`) -- Data Extraction's -0.3 fits that framing (slightly behind despite being strong), these two don't. Worth confirming whether +0.8 was ever computed or just typed as a plausible-looking placeholder alongside Data Extraction's more carefully-reasoned entry.

**Update 2026-08-30 01:09 EDT:** the "positive delta still shown as a gap" half of this is now understood as a real, reproducible `run_calculation()` behavior, not a placeholder typo -- confirmed with real test data (test2, all-Level-5, produced 3 gaps with deltas +2.8/+1.7/+2.8, all "ahead of peers") and confirmed the live app's own `results.html` renders `results.gaps` the same unfiltered way. Ben's call: leave this behavior alone on both the app and the deck for now, fix it once in `run_calculation()`'s gap-selection logic shortly after the deck ships, so both consumers inherit the fix together. See CLAUDE.md Key Decisions Log (2026-08-30 01:09 EDT) and SESSION_LOG.md for the verification. The specific +0.8/+0.8 numeric mismatch this finding also raises (whether those exact deltas were ever really computed) is unrelated to the behavior question and still stands as a separate, still-open mechanical question -- see finding 1's recommended fix strategy below, which resolves it by regenerating from a real `run_calculation()` output rather than guessing at the old numbers.

**6. 02-goals.html's goal-priority indicators (segmented dots + High/Top/Medium/Low labels) have nothing to check them against yet. [Not a mismatch, a missing-mechanism finding -- flagged in the audit, repeated here since step 5 is where it becomes concrete.]**

Every other object above at least has two pages (or a page and a constant) to compare. This one doesn't: there's no `goals`-shaped instance object anywhere in the deck today to confirm these six hardcoded indicators against, and Ben's a Profile-side input rather than something `run_calculation()` computes, so there's nothing to derive it from either. This can't be verified until the page has something to read from, which is really the same fix as finding 1's recommendation below applied to `goals`.

---

## Recommended fix strategy (for discussion, not started)

Findings 1 through 5 share one root cause: pages were built independently, each inventing its own plausible-looking numbers instead of being computed from one shared input. The fix that actually closes all of them at once, rather than patching each page's numbers in isolation, is to pick ONE set of raw session inputs (company, industry, `goals` 0-4 x6, `ratings` 0-5 x10) for the illustrative scenario, run them through the real `run_calculation()` (or hand-derive the same math, since I can call that function directly without the Flask app), and then update every page's hardcoded values to match that single output -- the same discipline the two test scenarios and the final Skywalker scenario will need anyway. That turns "which number is right" from a judgment call per page into a single upstream decision (what should this illustrative client's answers be), with everything downstream mechanically derived and therefore guaranteed consistent.

Let me know how you want to handle the two flagged judgment calls (finding 1's band mismatch, finding 5's gap deltas) and whether the fix strategy above sounds right, and I'll fold the actual reconciliation into building test set 1.

---

## Update 2026-08-30 01:32 EDT: findings 1-6 resolved by reconciling all 11 pages to test1

Per Ben's instruction ("fix bugs, then run against the app & fix more bugs, then run Skywalker") and the recommended fix strategy above, all 11 output_report pages were rewritten to derive every dynamic value from test_runs/test1_result.json (real run_calculation() output for company "Test Scenario 1", industry Accounting), rather than each page's own hand-typed guess.

**Finding 1 (band/score mismatch):** resolved by construction. Pages 3 and 5 now both show 1.9 / "Automating the Foundation" / "(Value is at Risk)", matching page 4's real capability average and the Roadmap pages' real `CAPABILITY_LEVELS`, because all four now read from the same source. Page 3's active zone card and "you are here" tag moved from "Transforming the Workflow" to "Automating the Foundation" to match.

**Finding 2 (page 4's ten wrong peer values):** resolved. All ten bars on 04-capability.html now show the real `PEER_SCORES` values from test1's `bar_rows` (Document Intake 3.5 through Governance & Trust 2.2), replacing the old wrong column. Every capability now reads as "behind peer" for this scenario, consistent with the 1.9-vs-2.6 overall gap.

**Finding 3 (industry stated two ways):** resolved. 02-goals.html and 05-where-you-stand.html both now say Accounting, and the peer count (133) is consistent on both 04-capability.html's lede and 05's peer note.

**Finding 4 (per-capability scores disagree across pages):** resolved. 04-capability.html's bars, 05-where-you-stand.html's strengths/gaps rows, and 07/08/09-roadmap.html's `CAPABILITY_LEVELS` object all now read from the same `capability_scores` dict.

**Finding 5 (gaps deltas don't reconcile):** the numeric half is resolved -- 05-where-you-stand.html and 06-solutions.html's `GAPS` array both now show the real three gaps (Data Review -1.1, Integration -1.2, Governance & Trust -0.2), all genuinely behind peer for this scenario, so the "positive delta on a gap card" question doesn't come up here. The behavior question (can a gap ever show a positive delta) is separately already decided -- see CLAUDE.md's 2026-08-30 01:09 EDT Key Decisions Log entry -- left alone deliberately, not something this reconciliation pass touches.

**Finding 6 (goals page missing mechanism):** resolved with an actual fix, not just correct values. 02-goals.html now carries a real `SESSION_GOALS` instance object (test1's actual Profile answers) and, separately, a `GOAL9_BY_INDUSTRY` conditional ported verbatim from the live app's own `profile.html`, so Goal 9's label/description are no longer a hardcoded string that happens to be right for Accounting -- they're computed from `INDUSTRY` the same way the live app computes them. This was necessary, not optional: Skywalker's industry (Fund) would have silently broken the old hardcoded text.

All five other pages (01-cover, 06-solutions, 07/08/09-roadmap, 10-success-story, 11-trust) also had every "Test Scenario 1" footer/company reference updated for consistency (was "Meridian Fund Services"). 10-success-story.html and 11-trust.html needed no other changes -- confirmed their content (named-client testimonials, platform-wide scale stats) is genuinely not session-dependent, matching DATA_CONSISTENCY_AUDIT.md's out-of-scope table.

Verified after the pass: full-directory grep sweep for em dashes, eyebrows, and leftover "Meridian" references across all 11 pages returned zero hits; div-tag open/close counts balanced on every file; every touched file's tail confirmed intact.

Not yet done: the live-app Jinja2/Playwright comparison pass (next step per Ben's instruction), and wiring the Skywalker Industries scenario in as the deck's permanent content (after the live-app pass is clean).
