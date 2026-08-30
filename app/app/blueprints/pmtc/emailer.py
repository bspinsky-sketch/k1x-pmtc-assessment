"""
Email delivery module for the K1x PMTC Assessment.

This module does not send anything itself. It hands the job to a separate
Lambda -- `mailer/handler.py`, deployed as the `PmtcMail` stack -- and returns
immediately.

Why the work is not done here:

  - The report is a PDF converted from a PowerPoint deck, and the only
    faithful converter is LibreOffice. LibreOffice does not fit a zip package
    and needs roughly 3GB and a minute of CPU. This app's own Lambda is a
    512MB pure-Python zip with a 15-second timeout, sitting behind a Function
    URL with a person waiting on the other end of it.
  - Nothing about generating a report should be able to fail a request the
    visitor is watching. The modal says "Report on its way" the moment the
    lead is captured, and that is a promise about the lead being recorded, not
    about the mail server.

So the invoke is asynchronous (`InvocationType='Event'`): AWS accepts the
payload, this returns in a few milliseconds, and the report is generated and
sent after the visitor's request has already finished. Failures land in the
mailer's own CloudWatch log, which is the only place they can land, because by
then there is nobody to tell.

That is survivable rather than careless, and for the same reason the data
capture is: the lead is already in the Google Sheet by a separate path
(`data_capture.py`), so a report that did not send can be sent by hand. A lead
that was never captured is gone.

Configuration read from the environment (set by `infra/lib/app-stack.ts`):
  REPORT_MAILER_FUNCTION  -- the mailer Lambda's function name
  AWS_REGION              -- set by the Lambda runtime itself
"""

import json
import logging
import os

log = logging.getLogger(__name__)

_client = None  # module-level boto3 Lambda client (lazy init)


def _get_client():
    """Return a boto3 Lambda client, or None if one cannot be made.

    Lazy and defensive for the same reason `data_capture._get_sheet()` is:
    outside Lambda -- a developer's machine running `flask run` -- there may be
    no credentials and no boto3 at all, and that must read as "mail skipped",
    never as an error the visitor sees.

    boto3 is not in `requirements-lambda.txt` because the managed Python
    runtime already provides it. That is also why it is imported in here
    rather than at module scope: a local dev environment installing only
    `requirements.txt` has no boto3, and an import at the top of this file
    would take the whole blueprint down with it.
    """
    global _client
    if _client is not None:
        return _client
    try:
        import boto3

        _client = boto3.client(
            'lambda', region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        )
        return _client
    except Exception as exc:
        log.warning('emailer: no Lambda client available: %s', exc)
        return None


def send_report(results, lead, goals=None):
    """Ask the mailer for one report. Never raises.

    Args:
        results: the dict `run_calculation()` returned, straight from
                 session['results']. Passed whole rather than picked apart,
                 so that adding a figure to the report later is a change in
                 the mailer only.
        lead:    the dict routes.py assembled from the modal, with at least
                 'email' populated.
        goals:   the dict from session['goals'] (goal key -> priority 0-4),
                 not part of `run_calculation()`'s own return -- needed
                 alongside `results` once the mailer renders the real
                 Jinja2 Output Report templates (Open Item #2/#17), whose
                 page 2 needs the visitor's actual goal priorities, not just
                 the computed results. Defaults to an empty dict so an old
                 call site that doesn't pass it still sends a valid payload
                 (today's placeholder generator doesn't read this key at
                 all, so its absence has never mattered until now).

    Returns:
        True if AWS accepted the invocation, False otherwise. The caller uses
        this for logging only -- there is deliberately nothing a False can be
        turned into that would help the visitor, who has already been told the
        report is coming.
    """
    recipient = (lead or {}).get('email', '').strip()
    if not recipient:
        log.warning('emailer: no recipient, nothing sent')
        return False

    function_name = os.environ.get('REPORT_MAILER_FUNCTION', '').strip()
    if not function_name:
        # The ordinary state on a developer's machine, and the state on any
        # deploy made before PmtcMail existed. Not an error.
        log.info('emailer: REPORT_MAILER_FUNCTION not set, report not requested')
        return False

    client = _get_client()
    if client is None:
        return False

    try:
        client.invoke(
            FunctionName=function_name,
            # 'Event', not 'RequestResponse'. The difference is the whole
            # design: RequestResponse would hold this request open for the
            # minute the conversion takes, blow through the app Lambda's
            # 15-second timeout, and show the visitor a 504 for a report that
            # was in fact about to be sent perfectly.
            InvocationType='Event',
            Payload=json.dumps(
                {'results': results, 'lead': lead, 'goals': goals or {}},
            ).encode('utf-8'),
        )
        log.info('emailer: report requested for %s via %s', recipient, function_name)
        return True
    except Exception as exc:
        # Swallowed on purpose. See the module docstring: by the time this
        # runs, the visitor has already been told the report is on its way,
        # and the lead is already recorded. Raising here would turn a mail
        # problem into a failed request for no gain.
        log.warning('emailer: could not request report for %s: %s', recipient, exc)
        return False
