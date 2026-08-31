# Sending the report

This directory is one Lambda function: it takes a completed assessment,
renders the real 11-page Output Report as PDF, and emails it.
`infra/lib/mail-stack.ts` is the AWS side.

**As of 2026-08-31, `generate.py` renders the real deck.** It runs the 11
locked `output_report/*.tmpl.html` Jinja2 templates -- the same templates
`tools/preview_report.py` already verified against 4 real
`run_calculation()` scenarios and real Google Sheet rows (PROJECT_STATE.md
Open Item #2/#17) -- against the visitor's actual `results`/`goals`, then
merges the rendered pages into one PDF with headless Chromium via
Playwright. `output_report/` is baked into this image at build time (see
Dockerfile); nothing is fetched at runtime.

This replaces the earlier python-pptx placeholder (one slide, drawn from
scratch, converted with LibreOffice) that shipped first so the rest of the
pipeline -- the container, the raw-MIME attachment, SES, the asynchronous
invoke from Flask -- could be built and proven real before the report
template existed. That architecture is unchanged; only what fills the PDF
is different. See CLAUDE_problems.md and SESSION_LOG.md (2026-08-31) for
the switch.

## What is already done, and did not have to be

`geniusdrive.com` is **already a verified SES domain identity in this
account**, DKIM-signed, and the account **already has production access**
(50,000 a day, verified 2026-08-28). Both were set up by the sibling SMOMA
project. They were the two steps with a queue in front of them -- DNS records
by hand at GoDaddy, and a review by a person at AWS -- and this tool inherits
both at no cost.

**Which is exactly why this stack must not declare the identity.** An SES
identity is unique per account and region, and `geniusdrive.com` is a
CloudFormation resource owned by `SmomaMail`. A second `ses.EmailIdentity` for
it fails the deploy, and if one ever did succeed, tearing down `PmtcMail`
would revoke Mass Group's sending along with ours. `mail-stack.ts` references
it only as a string used to build an ARN for an IAM policy.

## How a report is asked for

    results.html modal  ->  POST /api/lead  ->  emailer.py  ->  this function

`emailer.py` invokes this function **asynchronously** and returns in
milliseconds. Nothing waits for the PDF.

That shape is not an optimization, it is the design:

- The app's own Lambda is 512MB with a 15-second timeout, behind a Function
  URL with a person on the other end. The conversion alone took 66 seconds at
  3008MB on the sibling project. A synchronous call would show the visitor a
  504 for a report that was about to send perfectly.
- The modal has already said "Report on its way" before this function starts.
  A failure in here reaches CloudWatch and stops, because by then there is
  nobody to tell.

That is survivable rather than careless: the lead is already in the Google
Sheet by a separate path (`data_capture.py`), so a report that did not send
can be sent by hand. A lead that was never captured is gone.

**Invoked through IAM, not over a Function URL.** The sibling project needs a
public URL and a shared token inside its HTML because its front end is a
static page with no backend. This tool has a Flask backend, so the only caller
is `PmtcApp`'s execution role invoking this function by name. No public
endpoint, no token in the page.

## The seam between the two stacks

`PmtcApp` grants itself `lambda:InvokeFunction` on a **literal ARN** built
from the function's fixed name, `pmtc-report-mailer`. Not a CDK cross-stack
reference, because that would mean neither stack could synthesize without the
other in the same app -- and the whole `bin/app.ts` convention exists to keep
each stack deployable from a machine holding only its own context.

The cost is that the name appears in two places and nothing enforces that they
agree:

| Where | What |
| --- | --- |
| `infra/lib/mail-stack.ts` | `MailStackProps.functionName`, default `pmtc-report-mailer` |
| `infra/lib/app-stack.ts` | `REPORT_MAILER_FUNCTION`, a module constant |

**Change either and check the other.**

## Deploying

    bash infra/deploy-mail.sh

Needs Docker running, which is the one way this differs from
`cdk deploy PmtcApp` (pure Python, no daemon). Takes no arguments: every
address lives in `cdk.json` context, and because none of them is a secret, the
real values are also in the committed `cdk.example.json`.

Then, separately and by whoever holds the app secrets:

    npx cdk deploy PmtcApp

Until that runs, this function is deployed and working but the tool cannot
call it: the IAM grant and the `REPORT_MAILER_FUNCTION` environment variable
both live on the app's Lambda.

## Testing it

    python3 mailer/try_mailer.py you@example.com

Invokes the deployed function and waits, so a failure is visible immediately
rather than only in CloudWatch. Add `--async` to exercise the path the tool
actually uses.

To check what is really deployed rather than what anyone believes is:

    bash infra/check-mail.sh

That is the only way to see the blind-copy address. It is invisible in every
message it appears in, so a copy that silently stopped would look exactly like
one that never stopped.

## Addresses

| What | Value | Set by |
| --- | --- | --- |
| From | `reports@geniusdrive.com` | `sender` in `cdk.json` |
| Reply-To | `tklute@geniusdrive.com` | `replyTo` in `cdk.json` |
| Bounces and complaints | `tklute@geniusdrive.com` | `notify` in `cdk.json` |
| Blind copy | nobody yet | `bcc` in `cdk.json` |

`reports@geniusdrive.com` **has no mailbox and does not need one.** SES
verifies the domain, never the mailbox, so mail sends perfectly well from an
address nothing delivers to. What such an address cannot do is receive, which
is what `Reply-To` is for.

**Two decisions are still open, and both are go-live steps rather than
oversights:**

1. **The sender is a Genius Drive address.** A K1x prospect, filling in a
   K1x-branded tool embedded on a K1x page, receives mail from
   `geniusdrive.com`. Sending as K1x means verifying a domain in K1x's own
   DNS, which is a dependency on their team and an unknown amount of waiting.
   The sibling project weighed the identical trade and took the domain we
   control.
2. **Replies come to Genius Drive, and nothing in the message names anyone
   else.** That is deliberate: until the tool is live every send is a test,
   and a test reply should not land on the client. It also means there is
   exactly one route out of the message. The sibling project put a named
   contact in the body while `Reply-To` still pointed here and ended up with
   two routes to two different people that nothing held in step. When K1x
   names the person this report should come from, add them to `SIGNATURE` in
   `handler.py` **and** re-point `replyTo` in the same change.

## The 2026-08-31 switch to the real deck

The three steps this section used to describe as future work are done. What
actually changed:

`generate.py` was rewritten around `tools/preview_report.py`'s own
`render_deck()`/`try_build_pdf()` logic -- rendering the 11 locked
`output_report/*.tmpl.html` templates with Jinja2, then merging them to one
PDF with headless Chromium via Playwright. `handler.py`'s `report()` lost a
step: there is no `to_pdf()`/LibreOffice conversion anymore, because
`generate()` now writes the PDF directly. `Dockerfile` swapped
`libreoffice-impress`/`python-pptx` for Playwright + Chromium, with
`PLAYWRIGHT_BROWSERS_PATH` pinned to `/opt/pw-browsers` (not under `/tmp`,
which is a separate ephemeral volume at Lambda runtime and would not carry
over anything baked in there at build time) and `--no-sandbox
--disable-dev-shm-usage` on the Chromium launch (Lambda has no user
namespaces for Chromium's own sandbox, and `/dev/shm` is tiny or absent).
`infra/lib/mail-stack.ts`'s Docker build context widened from `mailer/` to
the repo root (with `file: 'mailer/Dockerfile'`) so the build can see
`output_report/`, which is now `COPY`'d into the image.

`fonts.conf` (the LibreOffice font-substitution rules for a hypothetical
PowerPoint deck) is no longer used -- the real templates already reference
the real `Outfit` font files directly via `@font-face` in `output_report/
assets/fonts/`, and Chromium renders those natively. The file is left in
place, unreferenced, rather than deleted mid-deadline; safe to remove in a
later pass. One pre-existing, already-documented gap carries over
unaffected: `Outfit-Medium.ttf` (weight 500) is missing from that fonts
directory, confirmed harmless in CLAUDE_problems.md P061 -- Chromium falls
back to a sibling Outfit weight within the same family rather than a
different font, the same behavior already verified for the live templates.
