import { CfnOutput, Duration, Stack, type StackProps } from 'aws-cdk-lib';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import type { Construct } from 'constructs';

export interface DomainStackProps extends StackProps {
  /**
   * The name the tool is served under, e.g. `k1x-pmtc.geniusdrive.com`.
   *
   * Letters, digits and hyphens only. An underscore is a valid DNS label
   * character but not a valid *hostname* character, and both ACM and
   * CloudFront reject it -- verified against the real ACM API 2026-08-28,
   * which returns a ValidationException naming the exact pattern
   * `(\*\.)?(((?!-)[A-Za-z0-9-]{0,62}[A-Za-z0-9])\.)+...`. This is why the
   * subdomain is `k1x-pmtc` and not `k1x_pmtc`.
   */
  readonly domainName: string;

  /**
   * An already-issued certificate for `domainName`, by ARN, in us-east-1.
   *
   * Requested outside this stack on purpose, same reasoning as
   * `mass_group_SMOMA`'s site-stack: a CloudFormation-managed certificate
   * holds the whole deployment in CREATE_IN_PROGRESS until somebody adds a
   * DNS record at GoDaddy, and if that wait times out the rollback deletes
   * the certificate -- so the validation record the DNS owner was already
   * given becomes wrong and the next attempt starts over with a fresh one.
   * Requested standalone it waits indefinitely, costs nothing, and its
   * record stays put.
   */
  readonly certificateArn: string;

  /**
   * The Lambda Function URL to put the domain in front of, exactly as
   * `AppStack`'s `AppUrl` output prints it (scheme, host, trailing slash).
   *
   * A string rather than an `IFunctionUrl` on purpose: this stack must be
   * deployable without synthesizing `AppStack`, because `AppStack` needs the
   * real Flask/Google secrets in context and this stack needs none of them.
   * See `bin/app.ts` -- the two stacks are independent by design, so putting
   * a domain on the tool can never roll back, re-bundle, or re-key the live
   * Lambda.
   */
  readonly functionUrl: string;
}

/**
 * The custom domain for the PMTC assessment tool: CloudFront in front of the
 * Lambda Function URL that `AppStack` already deploys.
 *
 * A Function URL cannot carry a custom domain by itself, so CloudFront is
 * here purely for the name and the certificate -- not to serve content. That
 * is the opposite of the sibling `mass_group_SMOMA` tool's CloudFront, which
 * fronts a static S3 bucket and caches aggressively, and it is why almost
 * every caching decision below is inverted from that stack's.
 *
 * **Deploy this separately from `AppStack`**, same reasoning as the handoff
 * kit's own two-stacks-not-one rule. The `*.lambda-url.us-east-1.on.aws`
 * address keeps working throughout and forever after, as the fallback.
 */
export class DomainStack extends Stack {
  constructor(scope: Construct, id: string, props: DomainStackProps) {
    super(scope, id, props);

    const { domainName, certificateArn, functionUrl } = props;

    const certificate = acm.Certificate.fromCertificateArn(
      this,
      'SiteCertificate',
      certificateArn,
    );

    // CloudFront needs an origin *host*, not a URL. Parsing rather than
    // asking for a bare hostname in props keeps this a straight copy-paste
    // of AppStack's own `AppUrl` output, which is the form anyone reading
    // the deploy notes actually has in hand.
    const originHost = new URL(functionUrl).hostname;

    // A Function URL is a plain HTTPS endpoint from CloudFront's point of
    // view. `FunctionUrlOrigin` would be the typed equivalent, but it needs
    // an `IFunctionUrl` construct, which would drag `AppStack` (and its
    // secrets, and its pip-install bundling step) into every synth of this
    // stack -- exactly the coupling this stack exists to avoid.
    const origin = new origins.HttpOrigin(originHost, {
      protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
      originSslProtocols: [cloudfront.OriginSslPolicy.TLS_V1_2],
      // The Flask app renders in Lambda, so an origin fetch is a cold start
      // plus a render, not a byte-range read off S3. The defaults (10s
      // read) are tight enough to trip on a cold start; AppStack's own
      // function timeout is 15s, so this is set to match it -- CloudFront
      // should give up when, and not before, the Lambda does.
      readTimeout: Duration.seconds(15),
      keepaliveTimeout: Duration.seconds(5),
    });

    // The tool is embedded as an iframe on a K1x-hosted page (CLAUDE.md,
    // "Deliverable"), so there is deliberately NO frame-options and NO
    // frame-ancestors here. Sending either would leave the tool working at
    // its own URL and blank inside the embed -- the exact failure the
    // sibling tool's stack carries the same warning about.
    const headers = new cloudfront.ResponseHeadersPolicy(this, 'SiteHeaders', {
      securityHeadersBehavior: {
        strictTransportSecurity: {
          accessControlMaxAge: Duration.days(365),
          includeSubdomains: false,
          preload: false,
          override: true,
        },
        contentTypeOptions: { override: true },
        referrerPolicy: {
          referrerPolicy:
            cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
          override: true,
        },
      },
    });

    const distribution = new cloudfront.Distribution(this, 'SiteDistribution', {
      comment: `PMTC assessment - ${domainName}`,
      domainNames: [domainName],
      certificate,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      httpVersion: cloudfront.HttpVersion.HTTP2_AND_3,
      defaultBehavior: {
        origin,
        // ALLOW_ALL, not the GET/HEAD default. The flow POSTs twice --
        // `POST /profile`, `POST /assessment` -- and the lead-capture modal
        // POSTs to `/api/lead`. With the default, all three come back 403
        // from CloudFront without ever reaching the Lambda.
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,

        // Nothing is cached, ever. Every page here is per-session: the Flask
        // session cookie carries the visitor's profile, goals and ratings
        // between the three pages, so a shared cache entry would hand one
        // visitor another's answers.
        //
        // This is the managed policy rather than a custom zero-TTL one, and
        // that is a decision with a cost worth recording. The origin sends
        // no Content-Encoding of its own (measured 2026-08-28: `/profile` is
        // 64,991 bytes with `Accept-Encoding: gzip, br` on the request), so
        // enabling CloudFront's own compression would be roughly a 6x cut on
        // every page load. It cannot be done here: CloudFront refuses
        // `EnableAcceptEncodingGzip` on any policy whose TTLs are all zero
        // ("The parameter EnableAcceptEncodingGzip is invalid for policy
        // with caching disabled" -- confirmed directly against the
        // CreateCachePolicy API, see CLAUDE_problems.md P047).
        //
        // The tempting workaround is a 1-second MaxTTL, which makes the
        // policy legal and buys back compression. Rejected: `GET /` calls
        // `session.clear()` and therefore returns a `Set-Cookie`, and a
        // first-time visitor has no cookie to key the cache on -- so within
        // that one second a second cookieless visitor could be served the
        // cached response *including its Set-Cookie* and land inside the
        // first visitor's session. A one-second window is still session
        // fixation on a tool that collects names and email addresses.
        //
        // The right way to get the compression back is at the origin --
        // `flask-compress` in the app, which also speeds up the bare
        // Function URL -- not by loosening anything here.
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,

        // The session cookie has to reach Flask, and so does everything
        // else the browser sends. This is a separate mechanism from the
        // cache policy above and is unaffected by it: the cache policy
        // decides the cache *key*, this decides what is *forwarded to the
        // origin*. AllViewerExceptHostHeader rather than AllViewer because
        // the origin is a Function URL: it routes on the Host header it
        // receives, and forwarding the viewer's `k1x-pmtc.geniusdrive.com`
        // instead would make it 403 every request.
        originRequestPolicy:
          cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        responseHeadersPolicy: headers,
        // Kept true so that the moment the origin does start sending
        // compressible responses, or the cache policy above can be
        // revisited, nothing else has to change. Inert on its own.
        compress: true,
      },
      // No separate /static/* behavior. There is exactly one static asset in
      // the whole app (`app/static/pmtc/picture1.png`) and `url_for` emits no
      // cache-busting query string, so a cached copy would go stale silently
      // the first time that image is replaced. Not worth a second behavior
      // and an invalidation step to save one request per visit.
    });

    new CfnOutput(this, 'SiteUrl', {
      value: `https://${domainName}/`,
      description: 'Where the tool is served, once the CNAME below exists',
    });
    new CfnOutput(this, 'DistributionDomainName', {
      value: distribution.distributionDomainName,
      description: `Add a CNAME at GoDaddy: host "${domainName.split('.')[0]}", pointing at this value`,
    });
    new CfnOutput(this, 'CloudFrontUrl', {
      value: `https://${distribution.distributionDomainName}/`,
      description:
        'Works without any DNS. Use it to prove the distribution is good before the CNAME lands',
    });
    new CfnOutput(this, 'OriginFunctionUrl', {
      value: functionUrl,
      description:
        'The Lambda Function URL behind this. Still public and still works -- the permanent fallback',
    });
  }
}
