import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

// ESM has no built-in __dirname; same explicit polyfill as app-stack.ts,
// rather than relying on tsx's CJS interop the way the handoff kit's stacks
// implicitly do.
const __dirname = path.dirname(fileURLToPath(import.meta.url));

import { CfnOutput, Duration, RemovalPolicy, Stack, type StackProps } from 'aws-cdk-lib';
import { Platform } from 'aws-cdk-lib/aws-ecr-assets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as ses from 'aws-cdk-lib/aws-ses';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import type { Construct } from 'constructs';

export interface MailStackProps extends StackProps {
  /**
   * The domain the report is sent from.
   *
   * **This stack does not verify it, and must not.** `geniusdrive.com` is
   * already an SES domain identity in this account, DKIM-signed and verified,
   * and it is a CloudFormation resource owned by the sibling `SmomaMail`
   * stack. An SES identity is unique per account and region, so declaring a
   * second `ses.EmailIdentity` for the same domain fails the deploy -- and if
   * it ever did succeed, tearing this stack down would revoke Mass Group's
   * sending along with ours. So this is a name used to build an ARN for an
   * IAM policy, nothing more.
   *
   * The consequence worth knowing: the two things that had a queue in front
   * of them on the sibling project -- DNS verification at GoDaddy, and the
   * AWS human review for production access -- are already done, and this tool
   * inherits both. Verified 2026-08-28: identity status SUCCESS, account
   * production access enabled, 50,000 a day.
   */
  readonly sendingDomain: string;

  /**
   * Where bounce and complaint notices go.
   *
   * Optional and worth setting. A visitor who mistypes their address is a
   * lead nobody hears about otherwise, because the tool deliberately never
   * waits for the send to succeed before telling them it is on its way.
   */
  readonly notify?: string;

  /**
   * The address the report is sent from.
   *
   * Only the domain is verified, never the mailbox, so this sends fine from
   * an address that does not exist. What such an address cannot do is
   * receive, which is what `replyTo` is for.
   */
  readonly sender?: string;

  /**
   * Where a reply to the report goes. Must be a real mailbox.
   *
   * Not the same as the sender, and that is the point. Unset means no
   * `Reply-To` header at all, and a reply to a mailbox-less `reports@`
   * address bounces into nowhere with nobody learning it happened.
   */
  readonly replyTo?: string;

  /**
   * Who receives a copy of every report, blind. Comma-separated.
   *
   * Empty as of 2026-08-28: K1x has not said who, and an address invented
   * here would be worse than none. Blind rather than visible because the
   * message reads as a personal one, and a third-party address in its headers
   * is both odd to receive and an address published to everyone who fills the
   * form in, including whoever submits a junk one.
   *
   * Delivery failures do not come here -- those go to the SNS topic, because
   * a report that would not generate is an operational problem rather than
   * something the client can act on.
   */
  readonly bcc?: string;

  /**
   * The Lambda's function name, fixed rather than generated.
   *
   * This is the seam between the two stacks and it is a string on purpose.
   * `PmtcApp` needs to invoke this function, and a CDK cross-stack reference
   * would couple their deploys: the app could not be deployed without this
   * stack being in the same synthesized app, which breaks the property the
   * whole `bin/app.ts` convention exists to protect -- that each stack
   * deploys from a machine holding only its own context. A fixed name lets
   * the app grant itself `lambda:InvokeFunction` on a literal ARN, with no
   * import and no deploy ordering between the two.
   *
   * The cost of a fixed name is that changing it replaces the function, and
   * that any change here has to be made in `app-stack.ts` too. Neither is
   * likely; both are cheaper than the coupling.
   */
  readonly functionName?: string;
}

/**
 * Sending the report.
 *
 * A separate stack from the app on purpose, the same reasoning as
 * `PmtcDomain`: `cdk deploy PmtcMail` cannot roll back the live tool, and
 * this stack deploys from a machine that holds none of the app's Flask or
 * Google secrets.
 *
 * A container image because LibreOffice is the only faithful way to turn a
 * filled deck into a PDF, and LibreOffice does not fit a zip. That is the
 * whole reason this is not simply `boto3.client('sesv2')` inside the existing
 * Flask function: `PmtcApp` is a 512MB pure-Python zip with a 15-second
 * timeout, and the conversion alone took 66 seconds at 3008MB on the sibling
 * project.
 */
export class MailStack extends Stack {
  constructor(scope: Construct, id: string, props: MailStackProps) {
    super(scope, id, props);

    const { sendingDomain, notify, replyTo, bcc } = props;
    const sender = props.sender ?? `reports@${sendingDomain}`;
    const functionName = props.functionName ?? 'pmtc-report-mailer';

    // Bounces and complaints, somewhere a person sees them. Its own topic
    // rather than the sibling project's, so two tools' delivery problems do
    // not arrive in one undifferentiated feed.
    const alerts = new sns.Topic(this, 'MailAlerts', {
      displayName: 'PMTC report delivery problems',
    });
    if (notify) {
      // Confirm the subscription from the mail AWS sends, or it stays pending
      // and the topic quietly notifies nobody.
      alerts.addSubscription(new subscriptions.EmailSubscription(notify));
    }

    // TLS required rather than opportunistic. The attachment is a named
    // firm's capability assessment, which is exactly what this audience would
    // not expect to cross the internet in the clear. The cost is a delivery
    // failure to a mail server that cannot do TLS, and in this audience that
    // is not a mail server we want to reach.
    //
    // Its own configuration set, for the same reason as its own topic. Note
    // that the shared identity already carries the sibling project's set as
    // its *default*, so every send from this tool has to name this one
    // explicitly -- which `handler.py` does, via REPORT_CONFIG_SET. A send
    // that forgot would still deliver, and its bounce events would simply
    // arrive in the other project's feed.
    // The name is explicit, and that is not cosmetic.
    //
    // This account's CDK execution role carries a guardrail:
    //
    //     Deny ses:* on configuration-set/ReportMail*
    //
    // It exists to protect the sibling SmomaMail stack's live configuration
    // set. The first deploy of this stack hit it -- because this construct was
    // originally called 'ReportMail' too, copied from that project, and CDK
    // derives a ConfigurationSet's physical name from the construct's logical
    // ID. So a brand new resource, one the same policy's own allow statement
    // covers, was refused for looking like somebody else's.
    //
    // Naming it here rather than renaming the construct alone, because an
    // explicit name is deterministic: it cannot drift back into that prefix
    // when a logical ID changes, and it reads as itself in the console. Same
    // trade as the Lambda's fixed name -- changing it replaces the resource.
    //
    // Every other guardrail in that policy is scoped by a `Smoma*` prefix on
    // the resource itself. This one is scoped by a construct-derived name, so
    // it is worth narrowing to the sibling set's exact ARN at some point;
    // until then, do not name anything here `ReportMail...`.
    const configurationSet = new ses.ConfigurationSet(this, 'PmtcReportMail', {
      configurationSetName: 'pmtc-report-mail',
      tlsPolicy: ses.ConfigurationSetTlsPolicy.REQUIRE,
      reputationMetrics: true,
    });

    // Only the events that mean something went wrong. Sends and deliveries
    // are the normal case and would bury the two that need a person.
    configurationSet.addEventDestination('Problems', {
      destination: ses.EventDestination.snsTopic(alerts),
      events: [
        ses.EmailSendingEvent.BOUNCE,
        ses.EmailSendingEvent.COMPLAINT,
        ses.EmailSendingEvent.REJECT,
      ],
    });

    const generator = new lambda.DockerImageFunction(this, 'ReportMailer', {
      functionName,
      code: lambda.DockerImageCode.fromImageAsset(
        // Build context is the repo root, not `mailer/`, as of 2026-08-31 --
        // the image now bakes in `output_report/`'s templates and assets
        // (see Dockerfile), which live outside `mailer/` and would not be
        // visible to the Docker build otherwise. `file` points at the real
        // Dockerfile's location within that wider context.
        path.join(__dirname, '..', '..'),
        {
          file: 'mailer/Dockerfile',
          // Matching the machine this is built and tested on, and the
          // architecture the app's own Lambda already uses.
          platform: Platform.LINUX_ARM64,
        },
      ),
      architecture: lambda.Architecture.ARM_64,
      // 3008MB because that is this account's ceiling, not because it is the
      // right number. The memory is really about CPU: Lambda scales vCPU with
      // it and the conversion is almost entirely CPU-bound. 10240 was tried
      // on the sibling project and refused with "'MemorySize' value failed to
      // satisfy constraint: Member must have value less than or equal to
      // 3008" -- an account quota, adjustable by asking AWS, and worth asking
      // for only if the duration ever starts to matter. It does not: nothing
      // waits on this function.
      memorySize: 3008,
      timeout: Duration.seconds(180),
      // Nobody is waiting, so a slow send costs nothing -- but a *duplicated*
      // send costs the recipient's trust. Asynchronous invocation retries a
      // failed invocation twice by default, and a send that failed after SES
      // had already accepted it is exactly the case that would be retried into
      // a second report. `handler.py` also swallows its own exceptions, so
      // neither this nor that is load-bearing alone.
      retryAttempts: 0,
      environment: {
        REPORT_SENDER: sender,
        REPORT_CONFIG_SET: configurationSet.configurationSetName,
        ...(replyTo ? { REPORT_REPLY_TO: replyTo } : {}),
        ...(bcc ? { REPORT_BCC: bcc } : {}),
      },
      // Same one-month/DESTROY convention as the app stack's log group, and
      // for a stronger reason here: this function fails silently by design,
      // so its log is the only place a report that never arrived shows up.
      // Declared as a log group rather than `logRetention`, which is
      // deprecated and deploys a custom resource and a second Lambda to do
      // what one log group does.
      logGroup: new logs.LogGroup(this, 'ReportMailerLogs', {
        // Named explicitly, at the conventional path Lambda would have used
        // itself. Without this CDK generates something unguessable
        // (`PmtcMail-ReportMailerLogs6692A03F-tNeZuXsBFWMG` on the first
        // deploy), and since this function is designed to fail silently, its
        // log is the only place a report that never arrived shows up. Anyone
        // debugging one will type `/aws/lambda/pmtc-report-mailer` first --
        // this makes that work. Found the hard way: the first live test send
        // succeeded and the log could not be tailed at the obvious path.
        logGroupName: '/aws/lambda/pmtc-report-mailer',
        retention: logs.RetentionDays.ONE_MONTH,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
      description: 'Fills the PMTC report, converts it to PDF and emails it',
    });

    // Sending only, and only as this domain. The function has no reason to
    // manage identities, read the suppression list, or send as anything else.
    //
    // Both actions, and `ses:SendRawEmail` is the one that actually matters.
    // The v2 SendEmail API authorises against `ses:SendEmail` for simple
    // content and against `ses:SendRawEmail` when the content is raw MIME --
    // and raw MIME is the only way to attach a PDF, which is the entire
    // point. Granting only the obvious one produced, on the sibling project,
    // an AccessDeniedException naming an action that appears nowhere in the
    // codebase.
    generator.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      resources: [
        `arn:aws:ses:${this.region}:${this.account}:identity/${sendingDomain}`,
        `arn:aws:ses:${this.region}:${this.account}:configuration-set/${configurationSet.configurationSetName}`,
      ],
    }));

    // No Function URL, deliberately. The sibling project needs one because
    // its front end is a static page with no backend, which is also why it
    // needs a shared token shipped inside its HTML. This tool has a Flask
    // backend, so the only caller is `PmtcApp`'s execution role invoking this
    // function by name through IAM: no public endpoint to find, no token in
    // the page, and nothing to rate-limit.

    new CfnOutput(this, 'MailerFunctionName', {
      value: generator.functionName,
      description: 'PmtcApp invokes this by name. Must match REPORT_MAILER_FUNCTION in app-stack.ts',
    });
    new CfnOutput(this, 'ReportSender', {
      value: sender,
      description: 'Sends as this; needs no mailbox, only the verified domain',
    });
    new CfnOutput(this, 'ReportReplyTo', {
      // Logical OR, not nullish coalescing: an unset context key in cdk.json is
      // an empty string rather than undefined (that is the file's own
      // convention), and `??` would print a blank output that reads as a
      // configured value rather than an absent one.
      value: replyTo || '(none - replies to the report vanish)',
      description: 'Where a reply actually goes. Must be a real mailbox',
    });
    new CfnOutput(this, 'ReportBcc', {
      value: bcc || '(none - nobody is copied)',
      description: 'Blind copy of every report. The recipient never sees this',
    });
    new CfnOutput(this, 'ConfigurationSetName', {
      value: configurationSet.configurationSetName,
      description: 'Passed on every send, or the bounce events go to the sibling project',
    });
    new CfnOutput(this, 'AlertsTopicArn', {
      value: alerts.topicArn,
      description: 'Bounces, complaints and rejections publish here',
    });
    new CfnOutput(this, 'NextStep', {
      value: notify
        ? 'Confirm the SNS subscription email AWS just sent, then have PmtcApp redeployed so the app can invoke this function'
        : 'Have PmtcApp redeployed so the app can invoke this function. No notify address was given, so nothing is watching bounces',
      description: 'What has to happen by hand',
    });
  }
}
