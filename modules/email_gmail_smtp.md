# Module: Email Delivery (Gmail SMTP)

**Status:** Complete -- verified on ITSMweb (2026-06-12)
**Library:** smtplib (built into Python; no install required)

---

## One-Time Setup (per project)

### 1. Create a dedicated Gmail address

Do not use a personal Gmail. Create a project-specific address (e.g., itsmbvf@gmail.com).

### 2. Enable 2-Step Verification

Google Account -> Security -> 2-Step Verification -> Turn on

### 3. Generate App Password

Google Account -> Security -> 2-Step Verification -> App passwords
- App: Mail
- Device: Other (enter project name)
- Copy the 16-character password (shown only once)

### 4. Add to .env (never commit)

```
GMAIL_ADDRESS=yourproject@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 5. Add to hosting platform env vars

Cloud Run: set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in environment variables.

---

## emailer.py Pattern

```python
import os, ssl, smtplib, shutil, tempfile, subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

def send_report_email(to_address, profile, kpis, priorities, investment=None):
    """Generate PDF from PPTX and send to to_address."""
    from .report import generate_report

    pptx_bytes = generate_report(kpis, profile, priorities, investment)

    tmp_dir = tempfile.mkdtemp()
    try:
        pptx_path = Path(tmp_dir) / 'report.pptx'
        pdf_path = Path(tmp_dir) / 'report.pdf'
        pptx_path.write_bytes(pptx_bytes)

        # LibreOffice PDF conversion
        lo = _lo_binary()
        result = subprocess.run(
            [lo, '--headless', '--nofirststartwizard',
             '--convert-to', 'pdf', '--outdir', tmp_dir, str(pptx_path)],
            capture_output=True, timeout=120
        )
        if result.returncode != 0 or not pdf_path.exists():
            raise RuntimeError(f'LibreOffice PDF conversion failed: {result.stderr}')

        # Build email
        msg = MIMEMultipart()
        msg['From'] = os.environ['GMAIL_ADDRESS']
        msg['To'] = to_address
        msg['Subject'] = f"ITSM Business Value Report -- {profile.get('company', 'Your Company')}"
        msg.attach(MIMEText('Please find your ITSM Business Value Assessment report attached.'))

        with open(pdf_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename='ITSM_Business_Value_Report.pdf')
        msg.attach(part)

        # Send
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ctx) as server:
            server.login(os.environ['GMAIL_ADDRESS'], os.environ['GMAIL_APP_PASSWORD'])
            server.send_message(msg)

    finally:
        shutil.rmtree(tmp_dir)
```

---

## Known Issues

- **LibreOffice PDF conversion fails when source PPTX is open in PowerPoint:** Close PowerPoint before triggering email send during local development.
- **Gmail App Password with spaces:** The 16-character App Password contains spaces in the UI. Store it with spaces in .env exactly as shown -- smtplib handles it correctly.
- **Timeout on first Cold Run request:** LibreOffice takes 15-30 seconds on first conversion after cold start. Increase `--timeout` in gunicorn if needed.

