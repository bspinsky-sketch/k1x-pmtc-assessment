# Module: Google Sheets Data Capture

**Status:** Complete -- verified on ITSMweb (2026-06-12)
**Library:** gspread + google-auth

---

## One-Time Setup (per project)

### 1. Create Google Cloud Project (or reuse existing)

If using the same GCP project as Cloud Run hosting, skip project creation.

### 2. Enable Google Sheets API

console.developers.google.com -> APIs & Services -> Enable APIs -> Google Sheets API

### 3. Create Service Account

IAM & Admin -> Service Accounts -> Create
- Name: [project]-sheets-writer
- Role: Editor (or Sheets-specific if preferred)
- Download JSON credentials file

### 4. Create Google Sheet

- Create a new Google Sheet
- Share it with the service account email (Editor role)
- Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit`

### 5. Add to .env (never commit)

```
GOOGLE_SHEET_ID=[sheet-id]
GOOGLE_CREDENTIALS_JSON=[full JSON content as single-line string]
```

To convert JSON file to single-line string:
```python
import json
with open('credentials.json') as f:
    print(json.dumps(json.load(f)))
```

### 6. Add to hosting platform env vars

Cloud Run: set GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS_JSON in Cloud Run environment variables.

---

## data_capture.py Pattern

```python
import json, os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def _get_sheet():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')
    if not creds_json:
        raise ValueError('GOOGLE_CREDENTIALS_JSON not set')
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
    return client.open_by_key(sheet_id).sheet1

def append_session(profile, priorities, kpis, email=None):
    try:
        sheet = _get_sheet()
        row = [
            datetime.utcnow().isoformat(),
            profile.get('company', ''),
            profile.get('revenue', ''),
            profile.get('employees', ''),
            profile.get('it_headcount', ''),
            # challenge priorities ch1-ch7
            priorities.get('ch1', 'None'),
            priorities.get('ch2', 'None'),
            # ... ch3-ch7 ...
            # KPI values
            kpis.get('roi', ''),
            kpis.get('payback_mo', ''),
            kpis.get('benefit_3y', ''),
            kpis.get('npv', ''),
            kpis.get('irr', ''),
            kpis.get('benefit_ann', ''),
            kpis.get('codn_mo', ''),
            kpis.get('fte_avg_annual', ''),
            email or '',
        ]
        sheet.append_row(row)
    except Exception as e:
        print(f'Data capture error: {e}')  # log but never raise

def update_email(email, company):
    """Backfill email into the most recent row for this company."""
    try:
        sheet = _get_sheet()
        records = sheet.get_all_values()
        for i in range(len(records) - 1, -1, -1):
            if records[i][1] == company:  # column 1 = company_name
                sheet.update_cell(i + 1, len(records[i]), email)
                break
    except Exception as e:
        print(f'Email update error: {e}')
```

---

## Column Schema (adapt per project)

| Column | Field |
|--------|-------|
| A | timestamp |
| B | company_name |
| C | revenue_M |
| D | employees |
| E | it_headcount |
| F-L | ch1-ch7 priorities |
| M | roi |
| N | payback_mo |
| O | benefit_3y |
| P | npv |
| Q | irr |
| R | benefit_ann |
| S | codn_mo |
| T | fte_avg_annual |
| U | email (nullable) |

---

## Notification Email

To receive an email on every row append, add to append_session():
```python
import smtplib, ssl
from email.mime.text import MIMEText

def _notify(row):
    msg = MIMEText(f'New session captured:\n{row}')
    msg['Subject'] = 'New BVF Session'
    msg['From'] = os.environ['GMAIL_ADDRESS']
    msg['To'] = os.environ['GMAIL_ADDRESS']
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ctx) as s:
        s.login(os.environ['GMAIL_ADDRESS'], os.environ['GMAIL_APP_PASSWORD'])
        s.send_message(msg)
```

