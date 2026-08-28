#!/usr/bin/env node
import { App } from 'aws-cdk-lib';
import { AppStack } from '../lib/app-stack.js';
import { DomainStack } from '../lib/domain-stack.js';

/**
 * Two stacks, deployed independently:
 *
 *   PmtcApp     the tool itself, on Lambda behind a Function URL
 *   PmtcDomain  CloudFront + the custom domain, in front of that Function URL
 *
 * Everything specific to a deploy is a context value, same convention as
 * `handoff/infra/bin/app.ts` -- set them once in `cdk.json` under `context`
 * and stop passing them on the command line. `cdk.example.json` in this
 * directory lists every key; `cdk.json` itself is gitignored because the app
 * half of it holds real secrets.
 *
 * Each stack is created only when the context it needs is actually present.
 * That is what lets the domain be deployed from a machine that does not have
 * the app's Flask/Google secrets at all: with those three keys blank,
 * `PmtcApp` simply is not in the app, so there is no way to accidentally
 * redeploy the live Lambda with placeholder credentials, and no way for a
 * `cdk deploy --all` to do it either. The failure mode is a clean "no stacks
 * match" rather than a silently broken deployment.
 *
 * A MailStack (copied from `handoff/infra/lib/mail-stack.ts`) is the natural
 * third stack once Q3 (email delivery) is decided -- deployed separately, on
 * purpose, same reasoning.
 */
const app = new App();

const account = app.node.tryGetContext('account') ?? process.env.CDK_DEFAULT_ACCOUNT;
const region = app.node.tryGetContext('region') ?? 'us-east-1';
if (!account) {
  throw new Error(
    'No account. Set "account" in cdk.json context, or run with credentials so CDK_DEFAULT_ACCOUNT is set.',
  );
}
const env = { account, region };

const prefix = app.node.tryGetContext('prefix') ?? 'Pmtc';

// Raw context values are checked for truthiness before Number(), not just
// nullishness -- cdk.json's own convention is to leave an unset value as ""
// rather than deleting the key (see the "//key" doc-comment pattern), and
// Number("") is 0, not NaN, so `?? 512` alone would silently deploy a
// 0MB/0s Lambda the moment someone leaves memoryMb/timeoutSeconds blank in
// cdk.json exactly as the template asks them to. The same truthiness check
// is why every `if` below works: a blank string reads as "not set".
const memoryMbRaw = app.node.tryGetContext('memoryMb');
const timeoutSecondsRaw = app.node.tryGetContext('timeoutSeconds');

const flaskSecretKey = app.node.tryGetContext('flaskSecretKey') as string | undefined;
const googleCredentialsJson = app.node.tryGetContext('googleCredentialsJson') as string | undefined;
const googleSheetId = app.node.tryGetContext('googleSheetId') as string | undefined;

if (flaskSecretKey && googleCredentialsJson && googleSheetId) {
  new AppStack(app, `${prefix}App`, {
    flaskSecretKey,
    googleCredentialsJson,
    googleSheetId,
    memoryMb: memoryMbRaw ? Number(memoryMbRaw) : undefined,
    timeoutSeconds: timeoutSecondsRaw ? Number(timeoutSecondsRaw) : undefined,
    env,
    description: 'PMTC assessment tool: Flask on Lambda behind a Function URL',
  });
} else {
  console.error(
    `[cdk] ${prefix}App skipped: flaskSecretKey / googleCredentialsJson / googleSheetId are not all ` +
      'set in cdk.json context. Fill them in to deploy or update the app itself.',
  );
}

// The domain half. `functionUrl` is the deployed `PmtcApp` stack's own
// `AppUrl` output, pasted in -- deliberately not a cross-stack reference, so
// that this stack synthesizes and deploys without AppStack being in the app
// at all (see the note above, and domain-stack.ts's `functionUrl` prop).
const domainName = app.node.tryGetContext('domain') as string | undefined;
const certificateArn = app.node.tryGetContext('certArn') as string | undefined;
const functionUrl = app.node.tryGetContext('functionUrl') as string | undefined;

if (domainName || certificateArn || functionUrl) {
  // All three or none. A domain with no certificate is a distribution
  // CloudFront refuses to create; a certificate with no origin is a
  // distribution with nothing behind it. Caught here, at synth, rather than
  // several minutes into a deployment.
  if (!domainName || !certificateArn || !functionUrl) {
    throw new Error(
      'domain, certArn and functionUrl go together: set all three in cdk.json context, or none.',
    );
  }

  new DomainStack(app, `${prefix}Domain`, {
    domainName,
    certificateArn,
    functionUrl,
    // us-east-1 is not a preference. A certificate a CloudFront distribution
    // can use has to live there.
    env: { account, region: 'us-east-1' },
    description: `PMTC assessment tool: ${domainName} via CloudFront`,
  });
}
