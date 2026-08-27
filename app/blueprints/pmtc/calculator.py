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

# Peer Comparison Data (Data!B27:G39) and Peer Count (Data!B40:G40). Per
# Ben's confirmation ("Peer comparison data is just seed values to start,
# so it is actually as complete as it can be until we get actual data
# rolling in"), every industry column currently holds the *same* seed
# value per capability — the table is shaped to vary by industry so real
# per-industry data can be dropped in later without a code change, it just
# doesn't yet.
PEER_SCORES = {
    "document_intake": 2.5,
    "inventory_management": 2.2,
    "data_extraction": 2.1,
    "data_validation": 1.9,
    "data_review": 2.3,
    "tax_analysis_reporting": 2.3,
    "integration": 1.4,
    "resource_structure": 1.5,
    "advisory": 1.2,
    "governance_trust": 1.7,
}
PEER_SCORES_BY_INDUSTRY = {industry: dict(PEER_SCORES) for industry in INDUSTRIES}

PEER_COUNTS = {
    "Accounting": 133,
    "Family Office / Wealth Management": 43,
    "Financial Institution": 76,
    "Fund": 54,
    "Tax Exempt / Non-Profit": 111,
}

# Archetype bands (Data!B99:D103), matched with an approximate-match
# VLOOKUP against the 0-5 "Your Score" average: the band whose threshold is
# the largest value <= the score. The workbook has no band below a score of
# 1 (VLOOKUP returns #N/A, wrapped in IFERROR to blank) — this port clamps
# scores below 1 up to band 1 rather than showing a blank result.
ARCHETYPE_BANDS = [
    {"min": 1, "name": "Automating the Foundation", "subtitle": "(Value is at Risk)"},
    {"min": 2, "name": "Standardizing and Scaling", "subtitle": "(Value is Protected)"},
    {"min": 3, "name": "Transforming the Workflow", "subtitle": "(Value is Accelerating)"},
    {"min": 4, "name": "Optimizing Capabilities", "subtitle": "(Value is Compounding)"},
]

# "What This Means" narrative (ysc-narrative-body). The workbook has no
# named range or authored copy for this block — it is lorem ipsum in the
# approved wireframe (results.html) for every archetype. Carried through
# verbatim rather than inventing marketing copy Ben hasn't reviewed; swap
# in real per-archetype copy once it exists.
ARCHETYPE_NARRATIVE_PLACEHOLDER = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
    "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur."
)

# Maturity-curve "Recommended" mark (assets/DESIGN_DECISIONS.md §34; see the
# curve script in results.html) is a fixed target, not computed from input.
RECOMMENDED_TARGET = 3.6


# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------

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

    your_score = round(mean(scores[k] for k in CAPABILITY_KEYS), 1)
    peer_score = round(mean(peer_by_cap[k] for k in CAPABILITY_KEYS), 1)

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
            "delta": round(scores[k] - peer_by_cap[k], 1),
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
        "narrative": ARCHETYPE_NARRATIVE_PLACEHOLDER,
        "strengths": strengths,
        "gaps": gaps,
        "bar_rows": bar_rows,
        "curve": {"now": your_score, "target": RECOMMENDED_TARGET, "peer": peer_score},
        "capability_scores": scores,
        "strength_rank": strength_rank,
        "gap_rank": gap_rank,
    }
