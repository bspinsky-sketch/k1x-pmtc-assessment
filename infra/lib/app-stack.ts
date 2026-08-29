import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import * as fs from 'node:fs';

// ESM has no built-in __dirname; this is the standard equivalent. (The
// handoff kit's own stacks use bare __dirname, which relies on tsx's CJS
// interop polyfill -- this spells it out explicitly instead of depending on
// that, since it costs nothing and works regardless of how it's ever run.)
const __dirname = path.dirname(fileURLToPath(import.meta.url));
import { CfnOutput, Duration, RemovalPolicy, Stack, type StackProps } from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import type { Construct } from 'constructs';

/**
 * The report mailer this app invokes when a visitor asks for their report.
 *
 * A literal name rather than a cross-stack reference, deliberately. Importing
 * `PmtcMail`'s function would mean this stack could not synthesize without
 * that stack in the same app, which breaks the property `bin/app.ts` exists
 * to protect: each stack deploys from a machine holding only its own context.
 * The cost is that this string and `MailStackProps.functionName` have to
 * agree, and nothing enforces it -- change either and check the other.
 *
 * If `PmtcMail` is not deployed, invoking this simply fails and `emailer.py`
 * logs it. Nothing about the assessment flow depends on the mailer existing.
 */
const REPORT_MAILER_FUNCTION = 'pmtc-report-mailer';

export interface AppStackProps extends StackProps {
  /**
   * The Flask app's secret key (`FLASK_SECRET_KEY`). Signs the session
   * cookie -- this app has no server-side session store (Flask-Session is in
   * requirements.txt but never wired up; sessions are the default signed
   * cookie), so this key is the only thing standing between a visitor's
   * Profile/Assessment answers and a forged one. Generate with
   * `python3 -c "import secrets; print(secrets.token_hex(32))"`, same as
   * `.env.example` already says for local dev -- use a different value here
   * than whatever is in a developer's local `.env`.
   */
  readonly flaskSecretKey: string;

  /**
   * The Google service-account key, as the full JSON exactly as downloaded,
   * collapsed to one line. `data_capture.py` already reads this from the
   * `GOOGLE_CREDENTIALS_JSON` environment variable rather than a file path
   * (confirmed 2026-08-28) -- that was true before Lambda was ever the plan,
   * and it happens to be exactly the shape Lambda needs: no local file to
   * bundle, no Secrets Manager call to add on the first deploy. Revisit
   * putting this in Secrets Manager instead once this tool is handling real
   * client data rather than the current test Sheet -- an env var is visible
   * to anyone with read access to the Lambda's configuration in the console.
   */
  readonly googleCredentialsJson: string;

  /** The target Google Sheet ID (`GOOGLE_SHEET_ID`). Not a secret -- it's an ID, not a key. */
  readonly googleSheetId: string;

  /** Lambda memory, in MB. Default 512 -- this app does no image/PDF work today. */
  readonly memoryMb?: number;

  /**
   * Lambda timeout. Default 15s. A Function URL is a synchronous, human is
   * waiting for a page call -- there is no reason for this to approach
   * Lambda's own 900s ceiling, and a short timeout turns a hung Google
   * Sheets call into a fast, visible 504 instead of a visitor staring at a
   * spinner for 15 minutes.
   */
  readonly timeoutSeconds?: number;
}

/**
 * The PMTC assessment tool itself, on Lambda behind a Function URL.
 *
 * Modeled on `handoff/infra/lib/mail-stack.ts`'s own Function URL section
 * (same reasoning: one route, no stages, no usage plans, nothing to
 * authorise) but this Lambda serves the whole Flask app, not one endpoint --
 * `lambda_handler.py` wraps the existing `create_app()` with Mangum, so
 * every route/template/blueprint that works under gunicorn today works here
 * unchanged.
 *
 * **Deploy this separately from anything else**, same reasoning as the
 * handoff kit's own two-stacks-not-one rule. This stack knows nothing about
 * the custom domain, and all it knows about mail is the name of the function
 * it hands a report request to -- both live in their own stacks.
 *
 * Packaging is pure-Python-only by design (see `requirements-lambda.txt`'s
 * own comment) specifically so this stack does NOT need Docker at deploy
 * time the way `MailStack`'s image-based mailer does -- `pip install` runs
 * directly on whatever machine runs `cdk deploy`, no daemon required. CDK
 * falls back to a Docker-based install automatically if that local install
 * ever fails (e.g. `pip3` not on PATH), so this still works on a machine
 * that only has Docker and not a local Python -- see the `bundling` block
 * below.
 */
export class AppStack extends Stack {
  constructor(scope: Construct, id: string, props: AppStackProps) {
    super(scope, id, props);

    const memorySize = props.memoryMb ?? 512;
    const timeout = Duration.seconds(props.timeoutSeconds ?? 15);

    // Same one-month/DESTROY convention as MailStack's log group, for the
    // same reason: enough to debug a "that never arrived" report, not enough
    // to accumulate cost on a low-traffic assessment tool.
    const logGroup = new logs.LogGroup(this, 'AppLogs', {
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const appDir = path.join(__dirname, '..', '..', 'app');

    const fn = new lambda.Function(this, 'App', {
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'lambda_handler.handler',
      // The whole `app/` directory becomes the Lambda's root: `app/` (the
      // Flask package `create_app()` lives in), `lambda_handler.py`, and
      // `requirements-lambda.txt` all travel together, with dependencies
      // installed alongside them at bundle time below. This is the same
      // directory gunicorn already serves from locally -- nothing about the
      // app's own layout changes for Lambda.
      code: lambda.Code.fromAsset(appDir, {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          // Tried first, on whatever machine runs `cdk synth`/`cdk deploy` --
          // including a Windows machine, which is the point: `--platform
          // manylinux2014_aarch64 --only-binary=:all:` tells pip to fetch
          // precompiled Linux/ARM64 wheels from PyPI rather than build
          // anything locally, so this works with no Docker daemon and no
          // Linux host. It only works because every package in
          // requirements-lambda.txt is pure Python (no C extensions needing
          // a real compile) -- unlike MailStack's mailer, which needs the
          // Docker path below because it may ship a real binary (a document
          // converter) that pip cannot just download a wheel for.
          local: {
            tryBundle(outputDir: string): boolean {
              try {
                execFileSync('pip3', [
                  'install', '--no-cache-dir', '--platform', 'manylinux2014_aarch64',
                  '--target', outputDir, '--implementation', 'cp', '--python-version', '3.13',
                  '--only-binary=:all:',
                  '-r', path.join(appDir, 'requirements-lambda.txt'),
                ], { stdio: 'inherit' });
                // Copy in only what the Lambda actually runs -- NOT a
                // blanket copy of appDir. Two real bugs caught here
                // 2026-08-28 on a real Windows deploy attempt: (1) a shell
                // `cp -a` call doesn't exist on Windows (this synth's whole
                // point is running from a Windows machine with no Docker),
                // and (2) even on Linux, a blanket copy of appDir would have
                // bundled `.env` (real Google service-account key and Flask
                // secret), `.git`, and a `.venv` into the deployed Lambda
                // package -- readable by anyone who could export the
                // function's code from the Lambda console. fs.cpSync is
                // cross-platform and lets us name exactly what ships.
                fs.cpSync(
                  path.join(appDir, 'lambda_handler.py'),
                  path.join(outputDir, 'lambda_handler.py'),
                );
                fs.cpSync(path.join(appDir, 'app'), path.join(outputDir, 'app'), {
                  recursive: true,
                  filter: (src) => !src.includes(`${path.sep}__pycache__`) && !src.endsWith('.pyc'),
                });
              } catch {
                return false; // falls through to the Docker `command` below
              }
              return true;
            },
          },
          command: [
            'bash', '-c',
            // Same selective-copy reasoning as the local path above -- not
            // `cp -a . /asset-output`, which would also sweep in `.env`,
            // `.git`, and `.venv` from appDir (mounted read-only as the
            // working directory here).
            'pip install --no-cache-dir -r requirements-lambda.txt -t /asset-output && ' +
            'cp -a lambda_handler.py app /asset-output/ && ' +
            'find /asset-output/app -name "__pycache__" -type d -prune -exec rm -rf {} +',
          ],
        },
      }),
      memorySize,
      timeout,
      environment: {
        FLASK_SECRET_KEY: props.flaskSecretKey,
        GOOGLE_CREDENTIALS_JSON: props.googleCredentialsJson,
        GOOGLE_SHEET_ID: props.googleSheetId,
        // Which function `emailer.py` asks for the report. An environment
        // variable rather than a constant in the Python, so that a rename or
        // a second environment is a redeploy rather than a code change.
        REPORT_MAILER_FUNCTION,
      },
      logGroup,
      description: 'PMTC assessment tool (Flask via Mangum)',
    });

    // Asking the mailer for a report. Invoke only, and only that one
    // function by name -- this app has no business calling anything else in
    // the account.
    //
    // An identity-based policy on this role is the whole permission: caller
    // and callee are in the same account, so no resource policy is needed on
    // the mailer, which is what keeps `PmtcMail` free of any reference back
    // to this stack. The ARN is built from a literal name for the same reason
    // (see REPORT_MAILER_FUNCTION above).
    //
    // Granted unconditionally, including before `PmtcMail` exists. A policy
    // naming a function that is not there is inert, whereas making it
    // conditional would mean the app needed redeploying in a particular order
    // relative to the mailer.
    fn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['lambda:InvokeFunction'],
      resources: [
        `arn:aws:lambda:${this.region}:${this.account}:function:${REPORT_MAILER_FUNCTION}`,
      ],
    }));

    // Same construct as MailStack's Function URL: one route, no CORS (the
    // page navigating to it IS the request, not a fetch() reading a JSON
    // reply), auth type NONE because this is a public assessment tool with
    // no login (confirmed 2026-08-26/27 -- see CLAUDE.md).
    const url = fn.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
    });

    // The same two-permissions gotcha MailStack's own comment documents:
    // since Oct 2025, a Function URL needs both `lambda:InvokeFunctionUrl`
    // (added automatically by `addFunctionUrl`) AND `lambda:InvokeFunction`
    // granted explicitly, or every request 403s with nothing in the
    // function's own logs to explain why. Copied here rather than
    // rediscovered the hard way a second time.
    new lambda.CfnPermission(this, 'AppInvokeViaUrl', {
      functionName: fn.functionName,
      action: 'lambda:InvokeFunction',
      principal: '*',
      invokedViaFunctionUrl: true,
    });

    new CfnOutput(this, 'AppUrl', {
      value: url.url,
      description: 'The tool, live. No DNS needed to use this today',
    });
    new CfnOutput(this, 'NextStep', {
      value:
        'Open AppUrl and click through Profile -> Assessment -> Results once for real before ' +
        'sharing it further. A custom domain is a separate step (CloudFront in front of this ' +
        'Function URL) -- not part of this stack; ask for it once a subdomain is ready.',
      description: 'What to do by hand',
    });
  }
}
