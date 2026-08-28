# Read this after you pull -- custom domain work (2026-08-28)

**Who this is for:** Ben, and/or Claude working on Ben's machine. Written by Tristen's session.

**Short version: nothing you already do is broken, and there is nothing you must
change just to keep working.** Your `cdk deploy PmtcApp` still works exactly as
before, from the same `cdk.json` you already have. Two app-level fixes are
described below and one of them is a real launch blocker, but neither is caused
by these changes.

---

## 1. What changed

The tool now has a custom domain: **https://k1x-pmtc.geniusdrive.com/**

It works by putting CloudFront in front of the Lambda Function URL you already
deployed. The Function URL
(`https://ssida3ob72gzabi2ai5r6kqzle0ltmcp.lambda-url.us-east-1.on.aws/`) is
unchanged, still public, and still works -- it is the permanent fallback.

This was built as a **separate CDK stack** (`PmtcDomain`), not as a change to
`PmtcApp`. Your Lambda was never touched, redeployed, or re-keyed.

New/changed files, all under `infra/` except the docs:

| File | What |
|---|---|
| `infra/lib/domain-stack.ts` | New. The CloudFront + domain stack. |
| `infra/bin/app.ts` | Changed. Each stack is now created only when its own `cdk.json` values are filled in. |
| `infra/cdk.example.json` | New. A committed template for `cdk.json`, which is gitignored because it holds secrets. |
| `infra/README.md` | Rewritten to cover both stacks. |

---

## 2. What you need to do after pulling: nothing, for the deploy to keep working

Your existing `infra/cdk.json` has the app secrets and no domain values. With
that shape, `PmtcDomain` simply does not exist in the CDK app on your machine,
and everything behaves as before. You can confirm in one command:

```
cd infra
npx cdk list
```

Expected output: **`PmtcApp`**, plus a line saying `PmtcDomain` was skipped.
That is correct and is the intended state on your machine. Deploy as usual:

```
eval "$(aws configure export-credentials --format env)"   # PowerShell users: see infra/README.md
npx cdk deploy PmtcApp
```

**Three things that are safe, and were tested rather than assumed:**

- Redeploying the app does **not** disturb the domain. CloudFront points at the
  Function URL's hostname, which belongs to the function, not to the deployment.
- Because the distribution caches nothing, your app changes appear at
  `k1x-pmtc.geniusdrive.com` **immediately**. There is no cache to clear and no
  invalidation step to remember.
- `cdk deploy --all` and `cdk destroy --all` from your machine **cannot** touch
  `PmtcDomain`. CDK never affects stacks that are not in the app, and on your
  machine it is not in the app.

**The one thing that would break the domain:** a change that *replaces* the
Lambda function rather than updating it -- renaming the `App` construct in
`app-stack.ts`, or anything else that changes its logical ID. AWS then issues a
brand-new Function URL, and the domain would keep pointing at the old, dead one.
Ordinary code, template, and environment-variable changes never do this. If you
do rename that construct, tell Tristen, or fix it yourself: put the new `AppUrl`
into `cdk.json` as `functionUrl` and run `npx cdk deploy PmtcDomain`.

---

## 3. What you DO need to fix: the iframe embed is currently broken

**This is the launch blocker, and it has nothing to do with the domain work.**
It is equally true of the bare Function URL today. The domain going live is just
what makes the embed real.

**The problem.** `create_app()` never sets `SESSION_COOKIE_SAMESITE` or
`SESSION_COOKIE_SECURE`, so Flask's defaults apply and browsers treat the
session cookie as `SameSite=Lax`. A `Lax` cookie is **not sent** when the page
is loaded inside an iframe on someone else's domain. The tool is designed to be
embedded in an iframe on a K1x-hosted page. So in the embed: a visitor fills in
the Profile, clicks Continue, and lands back on a blank Profile, forever. The
session never persists. It works perfectly when you open the URL directly, which
is exactly what makes this easy to miss.

**The fix.** In `app/app/__init__.py`, after the `app.secret_key = ...` line:

```python
    # Cookie settings for the iframe embed. The tool is loaded in an iframe on
    # a K1x-hosted page, which is cross-site: a SameSite=Lax cookie (Flask's
    # effective default) is not sent in that context, so the session would be
    # lost between every step of the wizard. SameSite=None fixes that, and
    # browsers reject SameSite=None unless Secure is also set.
    #
    # Both are read from the environment with secure production defaults so
    # that local development can opt out: Secure means HTTPS-only, and a local
    # dev server on http://127.0.0.1:5000 would otherwise silently stop
    # setting the session cookie at all.
    app.config.update(
        SESSION_COOKIE_SAMESITE=os.environ.get('SESSION_COOKIE_SAMESITE', 'None'),
        SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true',
    )
```

Then add these two lines to your **local** `.env` only (never to `cdk.json`, and
never to the deployed Lambda), so local development keeps working:

```
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_SECURE=false
```

Then redeploy: `npx cdk deploy PmtcApp`.

**How to verify it, and why the obvious check is not enough.** Confirming the
`Set-Cookie` header now says `SameSite=None; Secure` proves the config took
effect. It does **not** prove the embed works -- browsers have their own
third-party-cookie rules on top of this. Verify it the real way: make a scratch
HTML file with just `<iframe src="https://k1x-pmtc.geniusdrive.com/"
width="1000" height="800"></iframe>`, open it from a *different* domain or from
a local file, and click Profile -> Assessment -> Results inside the frame. If
you reach the Results page, it works.

Be aware that some browsers block third-party cookies by default now. If it
still fails in Safari or in Chrome with third-party cookies disabled, that is a
different and harder problem than this fix, and worth raising before launch
rather than after.

---

## 4. Nice to have: pages are being served uncompressed

`/profile` is about 65KB and is sent uncompressed, where gzip/brotli would make
it roughly 6x smaller. CloudFront cannot compress it, for a real reason
documented in `CLAUDE_problems.md` P047 -- and the workaround that would enable
it was rejected on a security ground, also documented there. Do not "fix" this
by changing the CloudFront cache policy.

The correct fix is compression at the origin, which also speeds up the bare
Function URL:

1. Add `flask-compress` to **both** `app/requirements.txt` and
   `app/requirements-lambda.txt` (the Lambda uses the second one only).
2. In `create_app()`: `from flask_compress import Compress`, then
   `Compress(app)` after the config block.
3. `npx cdk deploy PmtcApp`.

Verify with `curl -s -D - -o /dev/null -H 'Accept-Encoding: gzip'
https://k1x-pmtc.geniusdrive.com/profile | grep -i content-encoding`. You want to
see `content-encoding: gzip`, where today you see nothing.

---

## 5. Heads-up on merging

`CLAUDE_problems.md` is append-only, and this branch added **P047**. If you
added an entry during your own session, you may both have written a `P047` and
git will flag a conflict at the end of the file. Resolve it by keeping both
entries and renumbering yours to P048 -- no content is lost either way.

---

## 6. If you want the full story

- `infra/README.md` -- both stacks, the deploy commands, and the DNS steps.
- `infra/lib/domain-stack.ts` -- every CloudFront decision, with the reasoning
  in comments (particularly why nothing is cached and why no `x-frame-options`
  header is sent).
- `CLAUDE_problems.md` P047 -- the deploy failure hit along the way.
- `PROJECT_STATE.md` -- Open Items #10 and #11 track sections 3 and 4 above.
- `SESSION_LOG.md`, entry `2026-08-28 17:15 EDT` -- the full session narrative.
