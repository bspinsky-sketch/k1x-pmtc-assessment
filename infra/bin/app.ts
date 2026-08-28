#!/usr/bin/env node
import { App } from 'aws-cdk-lib';
import { AppStack } from '../lib/app-stack.js';

/**
 * One stack today: the tool itself, on Lambda behind a Function URL.
 *
 * Everything specific to a deploy is a context value, same convention as
 * `handoff/infra/bin/app.ts` -- set them once in `cdk.json` under `context`
 * and stop passing them on the command line.
 *
 * A MailStack (copied from `handoff/infra/lib/mail-stack.ts`, same as this
 * file's own AppStack started life as a copy of the handoff's patterns) is
 * the natural next stack once Q3 (email delivery) is decided -- deployed
 * separately, on purpose, same reasoning as the handoff kit's own
 * two-stacks-not-one rule.
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
// cdk.json exactly as the template asks them to.
const memoryMbRaw = app.node.tryGetContext('memoryMb');
const timeoutSecondsRaw = app.node.tryGetContext('timeoutSeconds');

new AppStack(app, `${prefix}App`, {
  flaskSecretKey: app.node.tryGetContext('flaskSecretKey') as string,
  googleCredentialsJson: app.node.tryGetContext('googleCredentialsJson') as string,
  googleSheetId: app.node.tryGetContext('googleSheetId') as string,
  memoryMb: memoryMbRaw ? Number(memoryMbRaw) : undefined,
  timeoutSeconds: timeoutSecondsRaw ? Number(timeoutSecondsRaw) : undefined,
  env,
  description: 'PMTC assessment tool: Flask on Lambda behind a Function URL',
});
