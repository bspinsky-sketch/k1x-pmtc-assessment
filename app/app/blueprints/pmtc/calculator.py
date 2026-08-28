"""
K1x PMTC Assessment — Tier 1 calculation engine.

This is a hand-port of the formulas in K1x PMTC Assessment.xlsx (Profile,
Assessment, Results, and Data sheets) to plain Python. There is no runtime
dependency on the workbook — the workbook's named ranges, lookup tables, and
formulas are reproduced here as constants and functions. See
Application/CLAUDE.md for the full named-range reference and the goal-to-
capability weighting derivation, and Application/PROJECT_STATE.md's Key
Decisions Log for why Tier 1 (hand-port) was chosen over Tier 2/3.

Scope note: the workbook also defines Assess_*_advice named ranges (a
per-capability, per-level "what to do next" text block used for report
generation). That table is not ported here — it is not displayed anywhere
in the approved profile/assessment/results wireframes, and Ben has
confirmed the PPTX report template does not exist yet (PROJECT_STATE.md
Open Item #2). Wire it in when the report-generation phase starts.
"""

from decimal import Decimal, ROUND_HALF_UP
from statistics import mean


# ---------------------------------------------------------------------------
# Reference data — ported directly from the workbook
# ---------------------------------------------------------------------------

# Profile!C5 dropdown (Data!B5:B9)
INDUSTRIES = [
    "Accounting",
    "Family Office / Wealth Management",
    "Financial Institution",
    "Fund",
    "Tax Exempt / Non-Profit",
]

# Priority-selector labels, for reference only — the profile page's
# SegmentSlider submits the 0-4 index directly (Data!B12:C16: None=0, Low=1,
# Medium=2, High=3, Top=4), so the backend never needs to parse the label.
PRIORITY_LABELS = ["None", "Low", "Medium", "High", "Top"]

# Maturity-level labels, for reference only — same story: the assessment
# page's SegmentSlider submits the 0-5 index directly (Data!B19:C24: None=0,
# Ad-hoc=1, Standardized=2, Automated=3, Integrated=4, Autonomous=5).
LEVEL_LABELS = ["None", "Ad-Hoc", "Standardized", "Automated", "Integrated", "Autonomous"]

# The 10 active capability dimensions (Assessment!B9:C18). The workbook also
# defines two retired dimensions — Adoption Readiness and Value Realization
# (Assessment!B19:C20, red-filled) — which are out of scope per Ben's
# confirmation ("10 capabilities is correct... red fill = not active") and
# have no corresponding input anywhere in the assessment page.
CAPABILITIES = [
    {"key": "document_intake", "name": "Document Intake"},
    {"key": "inventory_management", "name": "Inventory Management"},
    {"key": "data_extraction", "name": "Data Extraction"},
    {"key": "data_validation", "name": "Data Validation"},
    {"key": "data_review", "name": "Data Review"},
    {"key": "tax_analysis_reporting", "name": "Tax Analysis & Reporting"},
    {"key": "integration", "name": "Integration"},
    {"key": "resource_structure", "name": "Resource Structure"},
    {"key": "advisory", "name": "Advisory"},
    {"key": "governance_trust", "name": "Governance & Trust"},
]
CAPABILITY_KEYS = [c["key"] for c in CAPABILITIES]
CAPABILITY_NAMES = {c["key"]: c["name"] for c in CAPABILITIES}

# The 6 active goals (Profile!B9:B21). Four goals are retired in the
# workbook (Strengthen Integration/GW_3, Reduce Total Cost/GW_4, Drive Team
# Adoption/GW_8, Expand Capabilities/GW_10 — all red-filled, always 0) and
# have no input on the profile page, so they are omitted entirely rather
# than hardcoded to 0 — there is nothing for them to ever be added to.
#
# "advisory_services" is Goal 9 (Profile!B20/Goal9_lbl) — its display label
# and description flip on industry (Accounting -> "Expand Advisory
# Services"; everyone else -> "Elevate Decision Support", per
# Profile!B20/E20's IF(C5="Accounting", ...) formula) but the goal *weight*
# (GW_9) and its role in the capability weighting below are identical
# either way, so the backend only ever needs the one key.
GOALS = [
    {"key": "reduce_time", "label": "Reduce Cycle Time", "gw": "GW_1"},
    {"key": "standardize", "label": "Centralize & Standardize", "gw": "GW_2"},
    {"key": "scalable_growth", "label": "Support Scalable Growth", "gw": "GW_5"},
    {"key": "accuracy", "label": "Improve Accuracy", "gw": "GW_6"},
    {"key": "client_experience", "label": "Elevate Client Experience", "gw": "GW_7"},
    {"key": "advisory_services", "label": "Expand Advisory Services / Elevate Decision Support", "gw": "GW_9"},
]
GOAL_KEYS = [g["key"] for g in GOALS]

# Goal -> capability weighting coefficients (Assessment!U9:U18), with the 4
# retired goals' terms (which are always *0 in the live workbook) dropped.
# Each capability's raw U-column formula, for reference (GW_1=reduce_time,
# GW_2=standardize, GW_5=scalable_growth, GW_6=accuracy,
# GW_7=client_experience, GW_9=advisory_services; GW_3/4/8/10 struck out
# below since they're retired and always contribute 0):
#   Document Intake:         GW_1 + (GW_2*2) + S
#   Inventory Management:    (GW_2*2) + S
#   Data Extraction:         GW_6 + ((GW_1+GW_5)*2) + S
#   Data Validation:         GW_1 + GW_2 + (GW_6*2) + S
#   Data Review:             GW_6 + GW_9 + (GW_7*2) + S
#   Tax Analysis & Reporting: ~~GW_3~~ + GW_7 + ~~GW_10~~ + (GW_9*2) + S
#   Integration:             ~~GW_4~~ + GW_5 + GW_9 + ((~~GW_3~~+GW_1)*2) + S
#   Resource Structure:      ~~GW_4~~ + ((GW_5+~~GW_8~~)*2) + S
#   Advisory:                ((GW_9+~~GW_10~~)*2) + S
#   Governance & Trust:      ((GW_6+GW_7)*2) + S
# where S is the capability's own strength rank (see strength_rank below) —
# folded directly into the weighted-gap score, not just the raw score.
WEIGHT_COEFFICIENTS = {
    "document_intake": {"reduce_time": 1, "standardize": 2},
    "inventory_management": {"standardize": 2},
    "data_extraction": {"accuracy": 1, "reduce_time": 2, "scalable_growth": 2},
    "data_validation": {"reduce_time": 1, "standardize": 1, "accuracy": 2},
    "data_review": {"accuracy": 1, "advisory_services": 1, "client_experience": 2},
    "tax_analysis_reporting": {"client_experience": 1, "advisory_services": 2},
    "integration": {"scalable_growth": 1, "advisory_services": 1, "reduce_time": 2},
    "resource_structure": {"scalable_growth": 2},
    "advisory": {"advisory_services": 2},
    "governance_trust": {"accuracy": 2, "client_experience": 2},
}

# Peer scores: Data!D84:E96, the column literally headed "PEER LEADERS" --
# this, not the differently-shaped "Peer Comparison Data" table at
# Data!B27:G39 (see PEER_COUNTS below), is what the live workbook's own
# Results!F7 (named range R_peerScore, the number shown under the score
# ring) actually computes from -- its formula is =Data!E97, the average of
# this column's 10 active rows. Found and fixed 2026-08-28 (CLAUDE_problems.md
# P047): an earlier port used Data!B27:G39 for both peer count AND
# per-capability peer score, but B27:G39's per-capability columns
# (rows 28-39) are never actually referenced by any formula anywhere in
# the workbook -- only its row 40 (Peer Count) is, via Results!F9's
# HLOOKUP. B27:G39's per-capability numbers are vestigial/unused in the
# real model. Re-verified against Ben's 2026-08-28 refreshed workbook --
# this column is unchanged from the version this was first ported from.
# Like B27:G39, this column has no per-industry breakdown (one column,
# not five) -- so, same as before the fix, every industry currently shows
# the same peer benchmark; that's a real characteristic of the source
# data, not a shortcut taken here.
PEER_SCORES = {
    "document_intake": 3.5,
    "inventory_management": 3.2,
    "data_extraction": 3.3,
    "data_validation": 2.3,
    "data_review": 2.1,
    "tax_analysis_reporting": 2.8,
    "integration": 2.2,
    "resource_structure": 2.1,
    "advisory": 1.8,
    "governance_trust": 2.2,
}
PEER_SCORES_BY_INDUSTRY = {industry: dict(PEER_SCORES) for industry in INDUSTRIES}

# Peer Count (Data!B27:G40, row 40 specifically -- "Peer Comparison Data"'s
# only part that's actually live-wired, via Results!F9's HLOOKUP). This
# table IS broken out by industry, unlike PEER_SCORES above.
PEER_COUNTS = {
    "Accounting": 133,
    "Family Office / Wealth Management": 43,
    "Financial Institution": 76,
    "Fund": 54,
    "Tax Exempt / Non-Profit": 111,
}

# Archetype bands (Data!B100:E104), matched with an approximate-match
# VLOOKUP against the 0-5 "Your Score" average: the band whose threshold is
# the largest value <= the score. Band 0 ("Stuck in the Blocks") now covers
# the full 0-5 range with no gap below it, so no clamping is needed here --
# this exactly matches the workbook's VLOOKUP(...,TRUE) behavior for every
# real score. Narrative copy is the real per-archetype text written into the
# workbook and carried into results.html's inert archetype-reference-data
# block (wireframe DESIGN_DECISIONS.md §45); ported here verbatim now that
# this function does the score-based band selection that block's own
# comment flagged as not yet built.
ARCHETYPE_BANDS = [
    {
        "min": 0,
        "name": "Stuck in the Blocks",
        "subtitle": "(Value is Unrealized)",
        "narrative": "Nothing here is measured, so nothing here can be improved. Work moves by memory and habit rather than process, whether it's K-1s, other tax filings, or the reporting layered on top of them. Automation hasn't been tried yet, so there's no baseline to compare against and no case yet made for change.",
    },
    {
        "min": 1,
        "name": "Automating the Foundation",
        "subtitle": "(Value is at Risk)",
        "narrative": "The basics are in place, but they still run on manual effort. Collection, entry, and review depend on specific people doing specific things by hand, across K-1s and the other filings that share the same season. That's fragile: a busy week, a departure, or a missed handoff is enough to put accuracy or a deadline at risk.",
    },
    {
        "min": 2,
        "name": "Standardizing and Scaling",
        "subtitle": "(Value is Protected)",
        "narrative": "Process now exists where habit used to run things, with checklists and defined steps covering K-1s and adjacent tax work alike. That structure protects accuracy and makes the busy season repeatable rather than reinvented each year. The ceiling is effort, though: doing more still means adding people, not leverage.",
    },
    {
        "min": 3,
        "name": "Transforming the Workflow",
        "subtitle": "(Value is Accelerating)",
        "narrative": "Automation is doing real work now, not just supporting it, and the effect compounds across whatever tax and compliance tasks run through it. Cycle time keeps shrinking as fewer steps need a person, and the team is starting to spend time on judgment instead of entry. Confidence in the numbers is rising along with the speed.",
    },
    {
        "min": 4,
        "name": "Optimizing Capabilities",
        "subtitle": "(Value is Compounding)",
        "narrative": "Data flows on its own, and the team's attention has shifted from producing it to using it, across K-1s, other filings, and whatever comes next. Each season builds on the last instead of starting over, and the operation runs on evidence rather than heroics. That headroom is what turns compliance work into an advisory practice.",
    },
]

# Maturity-curve "Recommended" mark (assets/DESIGN_DECISIONS.md §34; see the
# curve script in results.html) is a fixed target, not computed from input.
RECOMMENDED_TARGET = 3.6


# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------

def _excel_round(value, digits=1):
    """Match Excel's ROUND() -- round-half-away-from-zero on the value's
    printed base-10 digits -- rather than Python's built-in round(), which
    is round-half-to-even AND operates on the value's actual binary float
    representation. The two disagree for sums of decimal (non-integer)
    inputs that land exactly on a .x5 boundary: round(2.55, 1) is 2.5 in
    Python (2.55 isn't exactly representable in binary; the nearest float
    is a hair under it) but ROUND(2.55, 1) is 2.6 in Excel. Found via the
    peer-score fix in CLAUDE_problems.md P047 -- mean(PEER_SCORES.values())
    lands on exactly this boundary (25.5 / 10 = 2.55), and the live
    workbook's own Data!E97 is explicitly =ROUND(AVERAGE(...), 1), not a
    bare average. Routing the value through str() first (rather than
    handing the float straight to Decimal) is what makes this match Excel
    -- it rounds on the value's decimal digits as printed, not on whatever
    exact binary fraction Python happens to be holding underneath.
    """
    quantum = Decimal("1").scaleb(-digits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def _split_sentences(text):
    """Split a narrative paragraph into its individual sentences for the
    Results page's "What This Means" card (one sentence per line -- Ben's
    2026-08-28 design request, mocked up and approved before wiring in).
    Every ARCHETYPE_BANDS narrative is hand-written prose ending each
    sentence in ". " (a period-plus-space, never an ellipsis, question
    mark, or abbreviation), so a plain split on that exact separator is
    safe here -- this is not a general-purpose sentence tokenizer and
    isn't meant to become one; if a future narrative rewrite introduces
    something like "e.g." or "!", revisit this.
    """
    parts = text.split(". ")
    return [p if p.endswith(".") else p + "." for p in parts]


def _stable_rank_desc(values_by_key, ordered_keys):
    """Reproduce RANK.EQ(..., 0) + COUNTIF(...)-1 : a dense, stable rank by
    descending value, with ties broken by the capability's position in
    ordered_keys (first occurrence wins the lower/better rank number),
    exactly matching Excel's top-to-bottom tie-break behavior for this
    RANK.EQ + running-COUNTIF idiom."""
    order = sorted(ordered_keys, key=lambda k: (-values_by_key[k], ordered_keys.index(k)))
    return {key: i + 1 for i, key in enumerate(order)}


def run_calculation(company, industry, goals, ratings):
    """
    company: str
    industry: str, one of INDUSTRIES
    goals: dict of goal key -> int 0-4 (PRIORITY_LABELS index)
    ratings: dict of capability key -> int 0-5 (LEVEL_LABELS index)

    Returns a dict with every value the Results page needs.
    """
    gw = {key: int(goals.get(key, 0)) for key in GOAL_KEYS}
    scores = {key: int(ratings.get(key, 0)) for key in CAPABILITY_KEYS}

    strength_rank = _stable_rank_desc(scores, CAPABILITY_KEYS)

    weighted = {}
    for key in CAPABILITY_KEYS:
        coeffs = WEIGHT_COEFFICIENTS[key]
        weighted[key] = sum(coeffs.get(g, 0) * gw[g] for g in coeffs) + strength_rank[key]
    gap_rank = _stable_rank_desc(weighted, CAPABILITY_KEYS)

    peer_by_cap = PEER_SCORES_BY_INDUSTRY.get(industry, PEER_SCORES)
    peer_count = PEER_COUNTS.get(industry, PEER_COUNTS["Accounting"])

    your_score = _excel_round(mean(scores[k] for k in CAPABILITY_KEYS), 1)
    peer_score = _excel_round(mean(peer_by_cap[k] for k in CAPABILITY_KEYS), 1)

    band = ARCHETYPE_BANDS[0]
    for candidate in ARCHETYPE_BANDS:
        if your_score >= candidate["min"]:
            band = candidate

    strengths_order = sorted(CAPABILITY_KEYS, key=lambda k: strength_rank[k])[:3]
    strengths = [
        {"key": k, "name": CAPABILITY_NAMES[k], "score": scores[k]}
        for k in strengths_order
    ]

    gaps_order = sorted(CAPABILITY_KEYS, key=lambda k: gap_rank[k])[:3]
    gaps = [
        {
            "key": k,
            "name": CAPABILITY_NAMES[k],
            "delta": _excel_round(scores[k] - peer_by_cap[k], 1),
        }
        for k in gaps_order
    ]

    bar_rows = [
        {"key": k, "name": CAPABILITY_NAMES[k], "you": scores[k], "peer": peer_by_cap[k]}
        for k in CAPABILITY_KEYS
    ]

    return {
        "company": company,
        "industry": industry,
        "your_score": your_score,
        "peer_score": peer_score,
        "peer_count": peer_count,
        "band_name": band["name"],
        "band_subtitle": band["subtitle"],
        "narrative": band["narrative"],
        "narrative_sentences": _split_sentences(band["narrative"]),
        "strengths": strengths,
        "gaps": gaps,
        "bar_rows": bar_rows,
        "curve": {"now": your_score, "target": RECOMMENDED_TARGET, "peer": peer_score},
        "capability_scores": scores,
        "strength_rank": strength_rank,
        "gap_rank": gap_rank,
    }
