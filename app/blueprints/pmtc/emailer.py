"""
Email delivery module for the ITSM Business Value Framework.

Pattern:
  1. Generate the pptx report (via report.py)
  2. Convert pptx -> pdf using LibreOffice headless
  3. Send the pdf as an attachment via Gmail SMTP (App Password auth)
  4. Clean up all temp files

Credentials read from environment:
  GMAIL_ADDRESS      -- sender address (itsmbvf@gmail.com)
  GMAIL_APP_PASSWORD -- 16-char App Password (not the Gmail login password)
"""

import os
import shutil
import smtplib
import subprocess
import sys
import tempfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.itsmbvf.report import generate_report


def _libreoffice_cmd():
    """Return the LibreOffice executable for the current platform."""
    if sys.platform == 'win32':
        candidates = [
            r'C:\Program Files\LibreOffice\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        raise RuntimeError(
            'LibreOffice not found. Install from https://www.libreoffice.org/download/ '
            'then restart the server.'
        )
    return 'libreoffice'


def _pptx_to_pdf(pptx_path):
    """
    Convert a pptx file to pdf using LibreOffice headless.
    Returns the path to the generated pdf (in its own temp dir).
    Caller must delete the returned directory when done.
    """
    tmp_out = tempfile.mkdtemp()
    result = subprocess.run(
        [_libreoffice_cmd(), '--headless', '--norestore', '--nofirststartwizard',
         '--convert-to', 'pdf', '--outdir', tmp_out, pptx_path],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        shutil.rmtree(tmp_out, ignore_errors=True)
        raise RuntimeError(f'LibreOffice PDF conversion failed (code {result.returncode}): {result.stderr}')

    # LibreOffice names the output after the input file
    base = Path(pptx_path).stem
    pdf_path = os.path.join(tmp_out, base + '.pdf')
    if not os.path.exists(pdf_path):
        shutil.rmtree(tmp_out, ignore_errors=True)
        raise RuntimeError('LibreOffice produced no PDF output.')

    return pdf_path, tmp_out


def send_report_email(profile, priorities, kpis, recipient_email, investment=None):
    """
    Generate the pptx report, convert to PDF, and email it to recipient_email.

    Args:
        profile:          dict from session['profile']
        priorities:       dict from session['priorities']
        kpis:             dict from session['kpis']
        recipient_email:  str -- user-supplied email address

    Raises:
        RuntimeError on generation or SMTP failure.
    """
    gmail_address  = os.environ.get('GMAIL_ADDRESS', '')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '')
    if not gmail_address or not gmail_password:
        raise RuntimeError('Email credentials not configured. Check GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env.')

    company   = profile['company_name']
    pptx_path = None
    pptx_dir  = None
    pdf_dir   = None

    try:
        # Step 1: generate pptx
        pptx_path, pptx_dir = generate_report(profile, priorities, kpis, investment)

        # Step 2: convert to pdf
        pdf_path, pdf_dir = _pptx_to_pdf(pptx_path)

        # Step 3: build email
        subject  = f'{company} -- ITSM Business Value Assessment'
        body_html = f"""\
<p>Please find attached your ITSM Business Value Assessment for <strong>{company}</strong>.</p>
<p>This report summarises the projected 3-year financial impact of an ITSM programme,
based on the profile and challenge priorities you entered.</p>
<p style="color:#1F3864;font-weight:bold;">Key results at a glance:</p>
<ul>
  <li>3-Year ROI: {kpis['roi']}</li>
  <li>Payback Period: {kpis['payback']}</li>
  <li>3-Year Benefits: {kpis['benefit_3y']}</li>
  <li>IRR: {kpis['irr']}</li>
</ul>
<p style="font-size:0.85em;color:#666;">
ITSM Business Value Assessment &nbsp;|&nbsp; Confidential
</p>
"""
        msg = MIMEMultipart()
        msg['From']    = gmail_address
        msg['To']      = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))

        safe_name   = ''.join(c for c in company if c.isalnum() or c in (' ', '-', '_')).strip()
        attach_name = f'{safe_name} - ITSM Business Value Assessment.pdf'

        with open(pdf_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{attach_name}"')
        msg.attach(part)

        # Step 4: send via Gmail SMTP SSL
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)

    finally:
        if pptx_dir:
            shutil.rmtree(pptx_dir, ignore_errors=True)
        if pdf_dir:
            shutil.rmtree(pdf_dir, ignore_errors=True)
