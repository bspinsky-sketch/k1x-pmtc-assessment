"""
Data capture module for the K1x PMTC Assessment.

Appends one row per completed assessment to a Google Sheet, and backfills
lead info into that same row if the "Get My Report" modal is submitted.

Trigger points (see routes.py):
  - POST /assessment  -- the moment results are computed, calls
    capture_result(). First time in a session: appends a new row and the
    caller stores the returned row number as session['capture_row']. If the
    user goes back, revises an answer, and resubmits (capture_row already
    set): updates that same row's assessment columns in place rather than
    appending a second row, so one browser session never produces more than
    one row.
  - POST /api/lead -- calls update_lead_info() to backfill First Name/Last
    Name/Email/Opt-In into the row identified by session['capture_row'].
    Defensive fallback in routes.py: if capture_row was never set (e.g.
    Sheets was unreachable at assessment time), routes.py retries
    capture_result() once before calling update_lead_info().

Sheet layout (Ben's own Google Sheet, set up and header-labeled already --
this module never writes headers). Source: K1x PMTC Assessment.xlsx,
NR!G2:AM3. Workbook column G ("Friendly name", label only) is Sheet column
A -- a fixed offset of 6 for every column after that. Data starts at row 4;
column A is never touched by this module.

  Sheet col | Workbook col | Field                          | Source
  ----------|--------------|--------------------------------|------------------------------
  B         | H            | Timestamp (ET, write-time)     | -- (generated here, not a named range)
  C         | I            | Company                        | Company
  D         | J            | Industry                       | Industry
  E         | K            | Goal 1 (Reduce Cycle Time)      | GW_1
  F         | L            | Goal 2 (Centralize/Standardize) | GW_2
  G         | M            | Goal 5 (Support Scalable Growth)| GW_5
  H         | N            | Goal 6 (Improve Accuracy)       | GW_6
  I         | O            | Goal 7 (Elevate Client Exp.)    | GW_7
  J         | P            | Goal 9 (Advisory/Decision Supp.)| GW_9
  K-T       | Q-Z          | Assessed capability 1-10        | Assess_*_lvl (calculator.py order)
  U         | AA           | Your score                      | R_youScore
  V         | AB           | Peer score                      | R_peerScore
  W         | AC           | Number of peers compared against| R_peerCount
  X-Z       | AD-AF        | Results top capability 1-3      | R_strengthRank1-3
  AA-AC     | AG-AI        | Results GAP capability 1-3      | R_gapRank1-3
  AD        | AJ           | First Name                      | FirstName (blank until modal)
  AE        | AK           | Last Name                       | LastName (blank until modal)
  AF        | AL           | Email address                   | Email (blank until modal)
  AG        | AM           | Opt-In                          | OptIn (blank until modal)

Credentials read from environment:
  GOOGLE_CREDENTIALS_JSON  -- full service-account JSON as a single-line string
  GOOGLE_SHEET_ID          -- the Sheet ID from the URL

Deliberately out of scope for this pass (per Ben, "not the data capture
[email] yet"): no notification email on append -- the old ITSM module's
send_capture_notification() has no PMTC equivalent here. Add one against
emailer.py once Q3 (email delivery) is confirmed, if wanted.
"""

import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")

DATA_START_ROW = 4      # first row of pushed data -- rows 1-3 are title/headers, already set up
FIRST_DATA_COL = "B"    # column A ("Friendly name") is manually maintained, never written here
LAST_ASSESSMENT_COL = "AC"  # last assessment-portion column (Results GAP capability 3)
LAST_DATA_COL = "AG"        # last column overall (Opt-In)

# Goal keys in the exact order the sheet expects (E:J) -- must match
# calculator.py's GOALS / GOAL_KEYS order exactly.
GOAL_KEYS_ORDER = [
    "reduce_time", "standardize", "scalable_growth",
    "accuracy", "client_experience", "advisory_services",
]

# Capability keys in the exact order the sheet expects (K:T) -- must match
# calculator.py's CAPABILITIES / CAPABILITY_KEYS order exactly.
CAPABILITY_KEYS_ORDER = [
    "document_intake", "inventory_management", "data_extraction",
    "data_validation", "data_review", "tax_analysis_reporting",
    "integration", "resource_structure", "advisory", "governance_trust",
]

_gc = None  # module-level gspread client (lazy init)


def _get_sheet():
    """Return the target worksheet (lazy init). Returns None if Sheets
    isn't configured or the connection fails -- callers must handle that
    as "capture skipped," never as an error to surface to the user."""
    global _gc
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        if _gc is None:
            creds_raw = os.environ.get('GOOGLE_CREDENTIALS_JSON', '').strip()
            if not creds_raw:
                return None
            creds_dict = json.loads(creds_raw)
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            _gc = gspread.authorize(creds)

        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '').strip()
        if not sheet_id:
            return None

        return _gc.open_by_key(sheet_id).sheet1

    except Exception as exc:
        log.warning('data_capture: could not connect to Google Sheets: %s', exc)
        return None


def _assessment_row_values(company, industry, goals, results):
    """Build the B:AG row for the assessment portion of the schema (28
    values covering B:AC). Columns AD:AG (the lead fields) are appended as
    4 blank placeholders -- update_lead_info() fills those in separately."""
    now_et = datetime.now(EASTERN).strftime('%Y-%m-%d %H:%M:%S')

    goal_scores = [goals.get(key, 0) for key in GOAL_KEYS_ORDER]
    capability_scores = results.get('capability_scores', {})
    capability_levels = [capability_scores.get(key, 0) for key in CAPABILITY_KEYS_ORDER]

    strengths = results.get('strengths', [])
    gaps = results.get('gaps', [])
    strength_names = [s.get('name', '') for s in strengths[:3]] + [''] * (3 - len(strengths[:3]))
    gap_names = [g.get('name', '') for g in gaps[:3]] + [''] * (3 - len(gaps[:3]))

    return [
        now_et,
        company,
        industry,
        *goal_scores,
        *capability_levels,
        results.get('your_score', ''),
        results.get('peer_score', ''),
        results.get('peer_count', ''),
        *strength_names,
        *gap_names,
        '', '', '', '',  # First Name, Last Name, Email, Opt-In -- filled later
    ]


def capture_result(company, industry, goals, results, row_number=None):
    """
    Write the assessment portion of one row (Timestamp through Results GAP
    capability 3, columns B:AC) to the Sheet.

    row_number=None: appends a new row (first time this session reaches
    Results) and returns the new row's 1-based row number.
    row_number=<int>: updates that row's assessment columns in place
    instead of appending -- the revise-and-resubmit case -- and returns the
    same row number back.

    Returns the row number on success, or None on failure. Never raises --
    errors are logged and swallowed so the user flow is unaffected.
    """
    sheet = _get_sheet()
    if sheet is None:
        log.info('data_capture: Google Sheets not configured -- skipping capture')
        return None

    row = _assessment_row_values(company, industry, goals, results)
    assessment_only = row[:-4]  # drop the 4 blank lead placeholders for an in-place update

    try:
        if row_number:
            sheet.update(
                f'{FIRST_DATA_COL}{row_number}:{LAST_ASSESSMENT_COL}{row_number}',
                [assessment_only], value_input_option='USER_ENTERED',
            )
            return row_number

        # 2026-08-28 (P045): append_row()'s table-detection landed the
        # write one column LEFT of table_range's stated boundary (real
        # Timestamp value found in column A instead of B). Compensated at
        # the time by padding one leading blank onto the values and
        # widening table_range's left edge to match.
        #
        # 2026-08-30: the same table-detection landed FOUR separate real
        # captures one column RIGHT of intended instead -- the opposite
        # drift, under the unchanged padded-row/table_range code above.
        # One of those four rows lost real data: its true last assessment
        # value drifted into column AD, which update_lead_info()'s fixed
        # AD:AG write later overwrote with the visitor's first name.
        # Recovered by re-running the row's own goals/ratings back through
        # run_calculation() and confirming every other stored field
        # (your_score, peer_score, peer_count, both surviving gaps)
        # reproduced exactly -- see SESSION_LOG.md 2026-08-30 for the
        # repair. Two confirmed drifts in opposite directions from the
        # same call is proof the anchor point isn't reliably pinned to
        # any fixed offset -- it depends on Sheet state in ways neither
        # occurrence's investigation could fully pin down, exactly what
        # P045's own "rule for future projects" warned this heuristic was
        # capable of ("prefer an explicit target range over an
        # auto-detecting append").
        #
        # Fix: stop asking the Sheets API to find the table at all. Read
        # column B (Timestamp, FIRST_DATA_COL) to find the real next
        # empty row ourselves -- the same approach preview_report.py's
        # --list already uses to find the last captured row -- and write
        # there with an explicit range via sheet.update(), the exact same
        # call the row_number-provided branch above uses. That branch has
        # never shown any drift across every row captured this project,
        # in either direction, because an explicit range leaves the API
        # nothing to auto-detect.
        #
        # Note: reading col_values() then writing is two round trips, not
        # one atomic operation, so two captures landing in the same
        # instant could in principle compute the same next_row and one
        # would silently overwrite the other's row. append_row() carried
        # an equivalent risk under its own undocumented auto-detection;
        # this isn't a new exposure, just a differently-shaped version of
        # the same one, and worth knowing about if concurrent captures
        # ever need a real fix (e.g. row_number reservation, a lock).
        next_row = len(sheet.col_values(2)) + 1
        if next_row < DATA_START_ROW:
            next_row = DATA_START_ROW
        sheet.update(
            f'{FIRST_DATA_COL}{next_row}:{LAST_DATA_COL}{next_row}',
            [row], value_input_option='USER_ENTERED',
        )
        return next_row

    except Exception as exc:
        log.warning('data_capture: capture_result failed: %s', exc)
        return None


def update_lead_info(row_number, first_name, last_name, email, opt_in):
    """
    Backfill the lead columns (AD:AG -- First Name, Last Name, Email,
    Opt-In) into an existing row.

    If row_number is falsy, does nothing and logs -- the caller (routes.py)
    is responsible for attempting a fresh capture_result() first in that
    case, not this function.

    Silent on failure -- never raises.
    """
    if not row_number:
        log.info('data_capture: no capture_row to update lead info into -- skipping')
        return
    sheet = _get_sheet()
    if sheet is None:
        return
    try:
        sheet.update(
            f'AD{row_number}:AG{row_number}',
            [[first_name, last_name, email, 'Yes' if opt_in else 'No']],
            value_input_option='USER_ENTERED',
        )
    except Exception as exc:
        log.warning('data_capture: update_lead_info failed (row %s): %s', row_number, exc)
