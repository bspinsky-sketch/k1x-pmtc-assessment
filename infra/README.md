# PMTC infra

One stack: `PmtcApp` -- the Flask assessment tool, on Lambda behind a
Function URL. See `lib/app-stack.ts` for the full reasoning; this file is
just the commands.

Modeled on `../../handoff/infra`'s conventions (same account, same
`tool0001` bootstrap qualifier, same context-value-in-cdk.json pattern) but
this is its own CDK app, not a copy added into the handoff kit -- the
handoff's own docs describe it as a starter to copy from, not a shared
monorepo multiple tools deploy out of.

## First-time setup

```
cd infra
npm install
```

No `cdk bootstrap` needed -- this deploys through the same account
(`019163347448`) and qualifier (`tool0001`) the handoff kit's SmomaSite/
SmomaMail stacks already bootstrapped.

## Fill in cdk.json

Edit the `context` block in `cdk.json` (not committed with real values --
treat `googleCredentialsJson`/`flaskSecretKey` the same as `.env`, never
commit them):

- `flaskSecretKey` -- generate with
  `python3 -c "import secrets; print(secrets.token_hex(32))"`. Use a
  different value than your local `.env`.
- `googleCredentialsJson` -- same value as your local `.env`'s
  `GOOGLE_CREDENTIALS_JSON` (the service-account key, full JSON, one line).
- `googleSheetId` -- same value as your local `.env`'s `GOOGLE_SHEET_ID`.
- `memoryMb` / `timeoutSeconds` -- leave blank for the defaults (512MB, 15s)
  unless you have a reason to change them.

## Deploy

```
npx cdk synth      # sanity-check first -- no AWS calls, just renders the template
npx cdk deploy PmtcApp
```

No Docker required for this stack (unlike the mail stack) -- packaging
installs pure-Python wheels directly via pip, see `lib/app-stack.ts`'s
`bundling` comment for why that's safe here specifically.

`cdk deploy` prints an `AppUrl` output when it finishes -- that's the live
tool, no DNS needed. Click through Profile -> Assessment -> Results once for
real before sharing the link further, same as the `NextStep` output says.

## Updating after a code change

Same two commands (`npx cdk synth` then `npx cdk deploy PmtcApp`) -- CDK
diffs against the deployed stack and only touches what changed. A plain
Flask/template edit repackages the Lambda; an `app-stack.ts` edit changes
infrastructure. Either way, nothing here touches the `git` history the way
committing does -- deploying and committing are two separate actions, do
both when a change is ready to keep the repo and the live tool in sync.

## What this does not do yet

- No custom domain. The Function URL (`*.lambda-url.<region>.on.aws`) is the
  live address until one is asked for -- adding a domain later is
  CloudFront in front of this same Function URL, a new construct, not a
  rewrite of `AppStack`.
- No email delivery (Q3 still open in PROJECT_STATE.md). A `MailStack`
  copied from `../../handoff/infra/lib/mail-stack.ts`, deployed as its own
  stack, is the natural next piece once that's decided.
- Not yet actually deployed. `AppStack` synths clean and was verified with a
  simulated Lambda invocation of the real Flask app locally (see
  `lambda_handler.py`'s own docstring) -- but nobody has run `cdk deploy`
  against the real AWS account yet. That's the next real step.
