"""
Data capture module for the ITSM Business Value Framework.

Appends one row per session to a Google Sheet dashboard, and sends a
notification email to the configured admin address on every append.

Credentials read from environment:
  GOOGLE_CREDENTIALS_JSON  -- full service-account JSON as a single-line string
  GOOGLE_SHEET_ID          -- the Sheet ID from the URL
  GMAIL_ADDRESS            -- sender/notification recipient (itsmbvf@gmail.com)
  GMAIL_APP_PASSWORD       -- Gmail App Password

Schema (columns A-U):
  timestamp, company_name, revenue_M, employees, it_headcount,
  ch1..ch7 (H/M/L/N), roi_x, payback_mo, benefit_3y, npv,
  irr_pct, avg_annual_benefit, codn_mo, ftes_saved, email
"""

import json
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

# Sheet column headers -- must match append_session() row order exactly.
HEADERS = [
    'timestamp', 'company_name', 'revenue_M', 'employees', 'it_headcount',
    'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7',
    'roi_x', 'payback_mo', 'benefit_3y', 'npv', 'irr_pct',
    'avg_annual_benefit', 'codn_mo', 'ftes_saved', 'email',
]

_gc = None  # module-level gspread client (lazy init)


def _get_sheet():
    """Return the first sheet of the dashboard workbook (lazy init)."""
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


def _ensure_headers(sheet):
    """Add header row if the sheet is empty."""
    try:
        if sheet.row_count == 0 or not sheet.row_values(1):
            sheet.append_row(HEADERS, value_input_option='RAW')
    except Exception as exc:
        log.warning('data_capture: could not write headers: %s', exc)


def append_session(profile, priorities, kpis, ftes_saved=None, email=None):
    """
    Append one row to the dashboard sheet.

    Returns the 1-based row number of the appended row, or None on failure.
    Never raises -- all errors are logged and swallowed so the user flow is unaffected.
    """
    sheet = _get_sheet()
    if sheet is None:
        log.info('data_capture: Google Sheets not configured -- skipping append')
        return None

    try:
        _ensure_headers(sheet)

        raw = kpis.get('raw', {})

        row = [
            datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
            profile.get('company_name', ''),
            profile.get('revenue_millions', ''),
            profile.get('employees', ''),
            profile.get('it_headcount', ''),
            priorities.get('challenge_1', 'None'),
            priorities.get('challenge_2', 'None'),
            priorities.get('challenge_3', 'None'),
            priorities.get('challenge_4', 'None'),
            priorities.get('challenge_5', 'None'),
            priorities.get('challenge_6', 'None'),
            priorities.get('challenge_7', 'None'),
            _fmt_raw(raw.get('roi')),
            _fmt_raw(raw.get('payback')),
            _fmt_raw(raw.get('benefit_3y')),
            _fmt_raw(raw.get('npv')),
            _fmt_raw(raw.get('irr') * 100 if raw.get('irr') is not None else None),
            _fmt_raw(raw.get('benefit_ann_avg')),
            _fmt_raw(raw.get('codn_mo')),
            str(ftes_saved) if ftes_saved is not None else '',
            email or '',
        ]

        sheet.append_row(row, value_input_option='USER_ENTERED')

        # Row number: headers in row 1, so appended row = current count
        return len(sheet.get_all_values())

    except Exception as exc:
        log.warning('data_capture: append failed: %s', exc)
        return None


def update_email(row_number, email):
    """
    Write the user's email into column U (index 21) of an existing row.
    Silent on failure.
    """
    if not row_number or not email:
        return
    sheet = _get_sheet()
    if sheet is None:
        return
    try:
        sheet.update_cell(row_number, 21, email)  # column U = 21
    except Exception as exc:
        log.warning('data_capture: update_email failed (row %s): %s', row_number, exc)


def send_capture_notification(profile, kpis, email=None):
    """
    Send a brief notification email to the admin address (GMAIL_ADDRESS).
    Silent on failure.
    """
    gmail_address  = os.environ.get('GMAIL_ADDRESS', '').strip()
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '').strip()
    if not gmail_address or not gmail_password:
        return

    try:
        company = profile.get('company_name', 'Unknown')
        if email:
            subject = f'[ITSMweb] Report requested -- {company}'
            note    = f'<p>Email address provided: <strong>{email}</strong></p>'
        else:
            subject = f'[ITSMweb] New session completed -- {company}'
            note    = '<p>No report requested.</p>'

        body = f"""\
<p><strong>Company:</strong> {company}</p>
<p><strong>Revenue:</strong> ${profile.get("revenue_millions", "?")}M &nbsp;
   <strong>Employees:</strong> {profile.get("employees", "?")}</p>
{note}
<p><strong>Results:</strong><br>
ROI: {kpis.get("roi", "?")} &nbsp;|&nbsp;
Payback: {kpis.get("payback", "?")} &nbsp;|&nbsp;
3-yr benefits: {kpis.get("benefit_3y", "?")} &nbsp;|&nbsp;
IRR: {kpis.get("irr", "?")}
</p>
"""
        msg = MIMEMultipart()
        msg['From']    = gmail_address
        msg['To']      = gmail_address   # notify the admin address
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)

    except Exception as exc:
        log.warning('data_capture: notification email failed: %s', exc)


def _fmt_raw(value):
    """Round a float to 2 decimal places for sheet storage, or return empty string."""
    if value is None:
        return ''
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return ''
