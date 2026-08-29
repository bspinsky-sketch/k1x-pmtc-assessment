# PMTC infra

Three stacks, deployed independently:

| Stack | What it is | File |
|---|---|---|
| `PmtcApp` | The Flask assessment tool, on Lambda behind a Function URL | `lib/app-stack.ts` |
| `PmtcDomain` | CloudFront and the custom domain, in front of that Function URL | `lib/domain-stack.ts` |
| `PmtcMail` | Report generation and delivery: LibreOffice on a container Lambda, sent via SES | `lib/mail-stack.ts` |

See each stack file for the full reasoning; this file is just the commands.

Modeled on `../../handoff/infra`'s conventions (same account, same
`tool0001` bootstrap qualifier, same context-value-in-cdk.json pattern) but
this is its own CDK app, not a copy added into the handoff kit -- the
handoff's own docs describe it as a starter to copy from, not a shared
monorepo multiple tools deploy out of.

## First-time setup

```
cd infra
npm install
cp cdk.example.json cdk.json
```

`cdk.json` is gitignored, because the app half of it holds real secrets (see
CLAUDE_problems.md P046). `cdk.example.json` is committed in its place and
documents every key inline. Copying it is not optional even if you only
want the domain stack: `cdk.json` is also what tells the CDK CLI where the
app entrypoint is, so without one, `npx cdk synth` fails before reaching any
of this project's code at all.

No `cdk bootstrap` needed -- this deploys through the same account
(`019163347448`) and qualifier (`tool0001`) the sibling SmomaSite/SmomaMail
stacks already bootstrapped.

## Each stack appears only when its context is filled in

`bin/app.ts` creates `PmtcApp` only when `flaskSecretKey`,
`googleCredentialsJson` and `googleSheetId` are all set, `PmtcDomain`
only when `domain`, `certArn` and `functionUrl` are all set, and `PmtcMail`
only when `mailDomain` is set. `npx cdk list`
tells you which ones you currently have.

That is deliberate, and it is what lets the domain be deployed from a
machine that has none of the app's secrets: with those three keys blank,
`PmtcApp` is not in the app at all, so there is no way to redeploy the live
Lambda with placeholder credentials -- not by naming it, and not via
`cdk deploy --all` either.

## Credentials

The CDK CLI's bundled SDK does not read the credential format `aws login`
writes: it reports "no credentials have been configured" while the AWS CLI
itself is perfectly happy with the same session. Bridge the two before any
`cdk` command:

```
eval "$(aws configure export-credentials --format env)"
```

Re-run it per command rather than exporting once -- the snapshot expires in
about fifteen minutes even though the underlying session lasts hours. Do not
"fix" this with `aws configure`, which trades a short-lived session for
long-lived keys sitting on disk.

## Deploying the app

Fill in `flaskSecretKey`, `googleCredentialsJson`, `googleSheetId` in
`cdk.json` (`cdk.example.json` says where each value comes from), then:

```
npx cdk synth PmtcApp     # sanity-check first -- no AWS calls, just renders the template
npx cdk deploy PmtcApp
```

No Docker required for this stack -- packaging installs pure-Python wheels
directly via pip, see `lib/app-stack.ts`'s `bundling` comment for why that is
safe here specifically.

`cdk deploy` prints an `AppUrl` output when it finishes: the Function URL.
That address works forever, with or without a domain, and stays the fallback.

## Deploying the domain

The certificate is requested by hand, **not** by CloudFormation. A
CFN-managed certificate holds the deploy in `CREATE_IN_PROGRESS` until
somebody adds a DNS record at GoDaddy, and a rollback on timeout deletes the
certificate -- so the validation record the DNS owner was already given
becomes wrong. Standalone, it waits indefinitely and costs nothing.

1. **Request it**, in `us-east-1` (not a preference -- a certificate a
   CloudFront distribution can use has to live there):

   ```
   aws acm request-certificate \
     --domain-name k1x-pmtc.geniusdrive.com \
     --validation-method DNS --region us-east-1
   ```

   Hostname characters only: letters, digits, hyphens. An underscore is a
   valid DNS label character but not a valid hostname character, and ACM
   rejects it outright with a `ValidationException`. This is why the
   subdomain is `k1x-pmtc` and not `k1x_pmtc`.

2. **Get the validation record:**

   ```
   aws acm describe-certificate --region us-east-1 \
     --certificate-arn arn:aws:acm:us-east-1:...:certificate/... \
     --query 'Certificate.DomainValidationOptions[0].ResourceRecord'
   ```

3. **Add it at GoDaddy.** `geniusdrive.com`'s DNS is at GoDaddy
   (`ns57`/`ns58.domaincontrol.com`), in an account this project does not
   control, so both records below go in by hand.

   **GoDaddy wants the host label, not the full name.** It appends the
   domain itself. For `_abc123.k1x-pmtc.geniusdrive.com` the Host is
   `_abc123.k1x-pmtc`; pasting the whole thing gives you
   `...geniusdrive.com.geniusdrive.com`, which resolves to nothing and looks
   completely correct in the console. This is the single most common way
   this step fails. 1 hour TTL is fine.

   **Leave that record in the zone forever.** It is what lets ACM renew
   without anyone doing anything. Tidying it up later silently breaks
   renewal thirteen months out.

4. **Wait for `ISSUED`**, then put the ARN in `cdk.json` as `certArn`, the
   deployed `AppUrl` in as `functionUrl`, and the hostname in as `domain`:

   ```
   npx cdk synth PmtcDomain
   npx cdk deploy PmtcDomain
   ```

5. **Point the subdomain at it.** One more CNAME at GoDaddy: Host
   `k1x-pmtc`, value the `DistributionDomainName` output. 1 hour TTL.

The `CloudFrontUrl` output works immediately and needs no DNS -- use it to
prove the distribution is good while the CNAME propagates.

## Deploying the mail stack

```
bash deploy-mail.sh
```

Takes no arguments. Every address lives in `cdk.json` context, and because
none of them is a secret, the real values are also in the committed
`cdk.example.json` -- so unlike the app's secrets, they survive this machine.

**This one needs Docker running**, which is the only way it differs from the
other two. The mailer is a container image because LibreOffice is the only
faithful PPTX-to-PDF converter and does not fit a zip. `deploy-mail.sh`
checks for the daemon and stops with a readable message rather than letting
CDK fail several minutes in.

**It does not verify the sending domain, and must not.** `geniusdrive.com` is
already a verified, DKIM-signed SES identity in this account with production
access, set up by the sibling SMOMA project, and it is a CloudFormation
resource owned by `SmomaMail`. An SES identity is unique per account and
region: declaring a second one fails, and if it ever succeeded, tearing down
`PmtcMail` would revoke Mass Group's sending too. See `lib/mail-stack.ts`.

**Before adding a resource to this stack, read the deny guardrails on the CDK
execution role.**

```
aws iam get-policy-version --policy-arn arn:aws:iam::019163347448:policy/ToolKitCfnExec \
  --version-id $(aws iam get-policy --policy-arn arn:aws:iam::019163347448:policy/ToolKitCfnExec \
  --query 'Policy.DefaultVersionId' --output text) --query 'PolicyVersion.Document'
```

`tool0001` is a scoped bootstrap, not the account's admin one, and it carries
explicit denies protecting the sibling SMOMA project's live resources. Most
are scoped by a `Smoma*` prefix, which nothing here can collide with. One is
not: `Deny ses:* on configuration-set/ReportMail*`. The first deploy of this
stack hit it, because the configuration-set construct had been given the same
ID as SMOMA's and CDK derives that resource's physical name from the logical
ID alone. See CLAUDE_problems.md P052. **Do not name anything here
`ReportMail...`**, and prefer an explicit physical name for any resource whose
generated name carries no stack prefix.

Two things happen by hand afterwards:

1. **Confirm the SNS subscription.** AWS emails the `notify` address once.
   Until somebody clicks it, the topic notifies nobody and bounces go
   unwatched.
2. **Redeploy `PmtcApp`.** The app's half of the wiring -- the
   `lambda:InvokeFunction` grant and the `REPORT_MAILER_FUNCTION` environment
   variable -- lives on the app's Lambda, so it belongs to whoever holds the
   app secrets. Until that runs, the mailer is deployed and working but the
   tool cannot call it.

To see what is actually deployed rather than what `cdk.json` claims:

```
bash check-mail.sh
```

That is the only way to see the blind-copy address, which is invisible in
every message it appears in.

`../mailer/README.md` covers the function itself: what it sends today, why
the invoke is asynchronous, and what changes when the real report template
arrives.

## Updating after a code change

`npx cdk synth PmtcApp` then `npx cdk deploy PmtcApp` -- CDK diffs against
the deployed stack and only touches what changed. A plain Flask/template
edit repackages the Lambda; an `app-stack.ts` edit changes infrastructure.
Nothing in `PmtcDomain` or `PmtcMail` needs redeploying for an app change:
`PmtcDomain` points at the Function URL, which does not change, and caches
nothing; `PmtcMail` is a separate function the app calls by name. Changing
the mailer itself (`mailer/`) is the reverse: `bash deploy-mail.sh`, and the
app needs nothing.

Deploying and committing are two separate actions -- do both when a change
is ready, to keep the repo and the live tool in sync.

## What this does not do yet

- The report itself is a placeholder. The whole delivery path is real and
  deployable, but the deck it fills is a single slide drawn from
  scratch, because the K1x report template does not exist yet
  (PROJECT_STATE.md Open Item #2). See `../mailer/README.md`, "When the real
  deck arrives" -- it is a template swap, not an architecture change.
- Secrets are plain Lambda environment variables, not Secrets Manager.
  Worth moving once this tool handles real client data rather than the
  current test Sheet -- an environment variable is visible to anyone with
  read access to the function's configuration in the console.
- The Function URL stays publicly reachable after the domain goes live.
  Locking it to CloudFront only (Function URL auth `AWS_IAM` plus an origin
  access control) would be the hardening step, at the cost of the fallback
  URL -- and it would mean `PmtcDomain` could no longer be deployed without
  touching `PmtcApp`, which is the property that makes the split useful
  today.
- **Do not trust this file for what is currently deployed.** It describes how
  to deploy, not what is live. `PROJECT_STATE.md`'s Authoritative Source
  Registry is the record of which commit is actually running -- check there
  rather than inferring from anything written here. (This bullet exists
  because the section originally said "not yet actually deployed" and stayed
  that way after the first real deploy.)
