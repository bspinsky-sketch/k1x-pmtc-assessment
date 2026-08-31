"""Send one report to yourself, without going through the tool.

    python3 mailer/try_mailer.py you@example.com

Invokes the deployed `pmtc-report-mailer` function with a realistic payload
and waits for the result, so a failure is visible here rather than only in
CloudWatch. The tool itself invokes asynchronously and never waits -- this
does the opposite deliberately, because the whole point of a test send is to
find out what went wrong.

Needs AWS credentials for the account the function is in, and nothing else.
It does not need the Flask app running, a browser, or a Google Sheet.

`--async` sends the way the tool does, which is worth doing once: it is the
path that actually runs in production, and it exercises the Lambda
asynchronous invocation queue rather than a direct call.
"""

import argparse
import json
import sys

FUNCTION = "pmtc-report-mailer"
REGION = "us-east-1"

# A realistic result, not an empty one. Long industry and company names on
# purpose: those are what found the live layout bug on the Results page
# (CLAUDE_problems.md P049), and a report is laid out no more forgivingly.
SAMPLE = {
    "results": {
        "company": "Wolf & Marlowe Family Office LLP",
        "industry": "Family Office / Wealth Management",
        "your_score": 1.8,
        "peer_score": 2.6,
        "peer_count": 37,
        "band_name": "Finding Your Stride",
        "band_subtitle": "Value is Emerging",
        "narrative": (
            "You have moved past ad-hoc handling and standardized parts of the K-1 "
            "lifecycle, but the gains are uneven across the process. The next step is "
            "connecting the pieces so that work done once is not redone downstream."
        ),
        "strengths": [
            {"key": "data_review", "name": "Data Review", "score": 3.0},
            {"key": "document_intake", "name": "Document Intake", "score": 3.0},
            {"key": "integration", "name": "Integration", "score": 2.0},
        ],
        "gaps": [
            {"key": "governance_trust", "name": "Governance & Trust", "delta": -1.6},
            {"key": "advisory", "name": "Advisory", "delta": -1.1},
            {"key": "tax_analysis_reporting", "name": "Tax Analysis & Reporting", "delta": -0.6},
        ],
    },
    "lead": {
        "first_name": "Test",
        "last_name": "Recipient",
        "company": "Wolf & Marlowe Family Office LLP",
        "email": None,  # filled from the command line
        "opt_in": True,
    },
    # Added 2026-08-31 alongside the real HTML-to-PDF generator -- page 2 of
    # the real deck reads goal priorities directly, and this payload had no
    # "goals" key (it predates emailer.py forwarding session['goals'],
    # commit 7e74547). Without it the old placeholder never noticed, since
    # it never read this key either; the real templates read it defensively
    # (missing -> {}) so this omission would not have crashed the render,
    # only made this test less representative than the real payload it is
    # standing in for.
    "goals": {
        "reduce_time": 3,
        "standardize": 4,
        "scalable_growth": 2,
        "accuracy": 4,
        "client_experience": 3,
        "advisory_services": 2,
    },
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="who to send the test report to")
    parser.add_argument("--async", dest="asynchronous", action="store_true",
                        help="invoke the way the tool does, without waiting")
    parser.add_argument("--function", default=FUNCTION)
    parser.add_argument("--region", default=REGION)
    args = parser.parse_args()

    import boto3

    payload = json.loads(json.dumps(SAMPLE))
    payload["lead"]["email"] = args.email

    client = boto3.client("lambda", region_name=args.region)
    print("invoking {} ({})".format(
        args.function, "async, like the tool" if args.asynchronous else "waiting for the result"))

    response = client.invoke(
        FunctionName=args.function,
        InvocationType="Event" if args.asynchronous else "RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )

    status = response.get("StatusCode")
    print("status {}".format(status))

    if args.asynchronous:
        # 202 means AWS accepted it for later, which is all an async invoke
        # can tell you. Whether it sent is in the function's log.
        print("accepted. Whether it sent is in the function's CloudWatch log:")
        # Read the log group off the function rather than assuming the
        # conventional path. They agree today, but they did not on the first
        # deploy (CDK generated an unguessable name), and a debugging hint
        # that points at a log group which does not exist is worse than none.
        try:
            config = client.get_function_configuration(FunctionName=args.function)
            group = config.get("LoggingConfig", {}).get(
                "LogGroup", "/aws/lambda/" + args.function)
        except Exception:
            group = "/aws/lambda/" + args.function
        print("  aws logs tail {} --since 10m --follow".format(group))
        return 0 if status == 202 else 1

    body = response["Payload"].read().decode("utf-8")
    print("returned {}".format(body))
    if response.get("FunctionError"):
        print("FUNCTION ERROR: {}".format(response["FunctionError"]), file=sys.stderr)
        return 1
    # The handler catches its own exceptions so that Lambda never retries a
    # send, which means a failed send still returns 200 with ok=False. Read
    # the body, not the status code.
    try:
        return 0 if json.loads(body).get("ok") else 1
    except ValueError:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
