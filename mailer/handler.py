"""Take one completed assessment and put a PDF in the visitor's inbox.

The whole pipeline behind the Results page's "Email Report" button: render
the real Output Report deck for this visitor, send it.

**Nothing here is allowed to become the visitor's problem.** `routes.py`
invokes this asynchronously and never waits for it, so the modal has already
said "Report on its way" before this function starts. A failure in here
reaches CloudWatch and stops. That is deliberate, and it is the same rule the
lead capture follows: never trap a prospect behind our own failure. It is also
survivable, because the lead is already in the Google Sheet by a separate path
(`data_capture.py`) -- a report that did not send can be sent by hand, whereas
a lead that was never captured is gone.

**Invoked directly through IAM, not over a Function URL.** The sibling SMOMA
mailer needs a public URL and a shared token in its page because its front end
is a static site with no backend. This tool has a Flask backend, so the call
is `lambda:InvokeFunction` from a role, with no public endpoint to find and no
token shipped to the browser.

**2026-08-31: `generate()` now renders the real 11-page Output Report
templates via headless Chromium and writes a PDF directly.** The earlier
python-pptx-plus-LibreOffice placeholder path (draw one slide, convert with
`soffice`) is gone -- there is no intermediate deck format to convert
anymore, so this file has one fewer step than it used to.
"""

import json
import logging
import os
import re
import tempfile
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from generate import generate

log = logging.getLogger()
log.setLevel(logging.INFO)

# All configuration, so that none of it is a constant somebody has to find.
SENDER = os.environ.get("REPORT_SENDER", "reports@geniusdrive.com")
CONFIG_SET = os.environ.get("REPORT_CONFIG_SET", "")

# Where a reply goes, which is not where the report comes from.
#
# The From address only needs its *domain* verified -- SES never checks the
# mailbox -- so `reports@geniusdrive.com` sends perfectly well without
# existing. What it cannot do is receive, and a prospect who reads their
# report and hits reply is the most valuable thing this tool produces. Without
# this header that reply bounces and nobody learns it happened.
#
# Set to a mailbox that exists. Unset means no header, and replies vanish.
REPLY_TO = os.environ.get("REPORT_REPLY_TO", "")

# Who else receives every report, without the recipient seeing it.
#
# Blind here means genuinely absent from the message: the address goes in the
# SES destination, never into a header. Putting it in a `Bcc:` header would
# hand the recipient the very thing this is avoiding, because SES sends the
# raw message exactly as composed.
#
# Empty as shipped 2026-08-28 -- K1x has not yet said who should be copied.
# When they do, it belongs as a default inside `infra/deploy-mail.sh` rather
# than an argument somebody remembers: this is an environment variable on a
# deployed function, so a redeploy that left the argument off would drop the
# copy while reports went on sending perfectly, and nothing would look wrong,
# because the copy is blind.
BCC = [a.strip() for a in os.environ.get("REPORT_BCC", "").split(",") if a.strip()]

REGION = os.environ.get("AWS_REGION", "us-east-1")

ses = boto3.client("sesv2", region_name=REGION)

# The sign-off, and deliberately not a contact address.
#
# There is exactly one route out of this message: the reader presses reply and
# reaches REPLY_TO. That is a property worth keeping until go-live, because
# until then every send is a test and a test reply should not land on the
# client. The sibling SMOMA project put a named contact in the body while
# Reply-To still pointed here, and ended up with two routes to two different
# people that nothing held in step (`infra/MAIL.md`, "Who the report tells the
# reader to contact").
#
# When K1x names the person this report should come from, add them here **and**
# re-point REPLY_TO in the same change, so the two never disagree.
SIGNATURE = "The K1x team\n"


FILENAME_PREFIX = "K1x Private Market Tax Capability Assessment for "
FILENAME_SUFFIX = ".pdf"
# 255 characters is the practical filename-length ceiling most filesystems
# (NTFS included) enforce -- subtract the fixed prefix/suffix around the
# company name to get the budget left for it. Computed, not hardcoded, so a
# future change to the prefix text can't quietly leave this stale.
MAX_COMPANY_LEN = 255 - len(FILENAME_PREFIX) - len(FILENAME_SUFFIX)


def _safe_filename_fragment(text):
    """Company names come from user input, not our own copy -- strip anything
    that breaks a filename or a Content-Disposition header (path separators,
    quotes, control characters), collapse whitespace, truncate to what fits
    within a normal filesystem's length limit alongside the fixed prefix/
    suffix, and fall back to a generic label if nothing usable survives."""
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned[:MAX_COMPANY_LEN].rstrip()
    return cleaned or "your firm"


def compose(data, pdf):
    """The message, as MIME, because SES needs raw content to carry a file."""
    lead = data.get("lead") or {}
    results = data.get("results") or {}
    company = results.get("company") or lead.get("company") or "your firm"
    name = (lead.get("first_name") or "").strip()

    message = MIMEMultipart()
    message["From"] = SENDER
    message["To"] = lead["email"]
    message["Subject"] = "Your Private Market Tax Capability Assessment - {}".format(company)
    if REPLY_TO:
        message["Reply-To"] = REPLY_TO

    score = results.get("your_score")
    peer = results.get("peer_score")
    band = results.get("band_name") or ""

    greeting = "Hi {},".format(name) if name else "Hi,"
    lines = [
        greeting,
        "",
        "Your Private Market Tax Capability Assessment for {} is attached.".format(company),
        "",
    ]
    if score is not None and peer is not None:
        lines.append(
            "You scored {:.1f} out of 5 across the ten capability dimensions, "
            "against {:.1f} for the peer leaders in your industry.".format(score, peer)
        )
        if band:
            lines.append('That places you in the "{}" band.'.format(band))
        lines.append("")
    lines.append(
        "The attachment carries your full Private Market Tax Capability "
        "Assessment: your score, how it compares, your goals and priorities, "
        "where you scored highest, and your roadmap for the priority areas to "
        "improve."
    )
    lines.append("")
    lines.append(SIGNATURE)
    message.attach(MIMEText("\n".join(lines), "plain"))

    attachment = MIMEApplication(pdf.read_bytes(), _subtype="pdf")
    attachment.add_header(
        "Content-Disposition", "attachment",
        filename=FILENAME_PREFIX + _safe_filename_fragment(company) + FILENAME_SUFFIX,
    )
    message.attach(attachment)
    return message


def send(message, to):
    """Hand the message to SES, and say plainly what went wrong if it refuses.

    The AWS error code and message are logged on one line rather than left to
    `log.exception`, whose traceback CloudWatch splits across events and can
    truncate before the line that actually names the problem. For a function
    designed to fail silently, an unreadable failure is the worst kind.
    """
    request = {
        "FromEmailAddress": SENDER,
        # BccAddresses rather than a Bcc header, which is what keeps it blind:
        # SES delivers to everyone named here and sends the message exactly as
        # composed, and the message names only the recipient.
        "Destination": {"ToAddresses": [to], **({"BccAddresses": BCC} if BCC else {})},
        "Content": {"Raw": {"Data": message.as_bytes()}},
    }
    # Without the configuration set the mail still sends and the bounce and
    # complaint events quietly go nowhere.
    if CONFIG_SET:
        request["ConfigurationSetName"] = CONFIG_SET
    try:
        response = ses.send_email(**request)
    except ClientError as err:
        error = err.response.get("Error", {})
        log.error("SES refused the message: %s: %s (from=%s, configSet=%s)",
                  error.get("Code"), error.get("Message"), SENDER,
                  CONFIG_SET or "(none)")
        raise
    log.info("sent to %s, message id %s, replies to %s, copied to %s", to,
             response.get("MessageId"), REPLY_TO or "(nowhere)",
             ", ".join(BCC) or "nobody")


def handler(event, context):
    """Always succeeds, so that Lambda never retries a send.

    Asynchronous invocation retries a *failed* invocation by default, and a
    send that half-worked is exactly the kind that would be retried into a
    duplicate report. `retryAttempts: 0` on the function says the same thing
    from the infrastructure side; this says it from the code side, so neither
    alone is load-bearing.

    Nothing reads this return value. It exists to be unambiguous in the logs.
    """
    try:
        report(event)
        return {"ok": True}
    except Exception:
        log.exception("report generation failed")
        return {"ok": False}


def report(event):
    """One assessment, from payload to inbox.

    The event is the payload itself. There is no HTTP envelope to unwrap and
    no token to check, because the only caller is an IAM principal that was
    granted `lambda:InvokeFunction` on this function by name.
    """
    data = event if isinstance(event, dict) else json.loads(event)

    recipient = ((data.get("lead") or {}).get("email") or "").strip()
    if not recipient:
        log.warning("refused: no recipient in payload")
        return

    results = data.get("results") or {}
    log.info("generating for %s, company %s, score %s", recipient,
             results.get("company"), results.get("your_score"))

    with tempfile.TemporaryDirectory() as work:
        pdf_path = Path(work) / "report.pdf"
        generate(data, str(pdf_path))
        send(compose(data, pdf_path), recipient)
