# Sending the report

This directory is one Lambda function: it takes a completed assessment, builds
a deck, converts it to PDF, and emails it. `infra/lib/mail-stack.ts` is the
AWS side.

**The deck it builds today is a placeholder.** Ben's real PMTC report template
does not exist yet (PROJECT_STATE.md Open Item #2). Rather than leave the
whole delivery path unbuilt until it does, `generate.py` draws a single slide
from scratch and fills it with the visitor's real computed results. Everything
around that -- the container, LibreOffice, the fonts, the raw-MIME attachment,
SES, the asynchronous invoke from Flask -- is the final architecture and runs
for real.

That is the point of a placeholder that draws something rather than an empty
PDF: the parts most likely to break on the day the template lands are the
parts a placeholder still exercises. Whether python-pptx output converts at
all, how long the conversion takes at this memory setting, whether the fonts
resolve, whether a multi-megabyte attachment survives SES.

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

## When the real deck arrives

Nothing about the architecture changes. Three steps:

1. Drop `master.pptx` into this directory and add `COPY master.pptx ./` to the
   `Dockerfile` (the line is already written there as a comment). Baked into
   the image rather than fetched from S3, so the deck and the code that fills
   it are one artifact and cannot be at different versions.
2. Replace `generate.py`'s body with the real fill. Keep the
   `generate(data, out_path)` signature and `handler.py` does not change at
   all.
3. Delete the "Placeholder layout" line at the bottom of the slide, and the
   paragraph at the top of this file.

Before writing any fill code, run the shape audit from `PPT_CONVENTIONS.md`
Part 2 and push only to shapes confirmed empty -- a pre-filled shape keeps its
formatting and overwriting strips it (STANDING_RULES.md, python-pptx rules).

Recheck `fonts.conf` against whatever the real deck names. The rule for
`Outfit` is a judgement call about which installed face is closest, and if K1x
can license the real font for a server, dropping the .ttf files into the image
and deleting the rule always beats a substitution.
