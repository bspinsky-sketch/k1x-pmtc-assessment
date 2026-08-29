#!/usr/bin/env bash
# What is actually deployed, as opposed to what anyone believes is deployed.
#
#     bash infra/check-mail.sh
#
# Reads the live values off the stack rather than off `cdk.json`, which is the
# whole point: the two agree only if the last deploy actually went through.
#
# The blind-copy line is the one that earns this script. That address is
# invisible in every message it appears in, so if it is ever wrong or missing,
# nothing about a sent report will show it -- this is the only place it can be
# seen.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"

echo "==> PmtcMail outputs (region $REGION)"
aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name PmtcMail \
  --query 'Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}' \
  --output table

echo
echo "==> live environment on the deployed function"
aws lambda get-function-configuration \
  --region "$REGION" \
  --function-name pmtc-report-mailer \
  --query 'Environment.Variables' \
  --output json

echo
echo "==> sending identity and account sending status"
aws sesv2 get-email-identity --region "$REGION" --email-identity geniusdrive.com \
  --query '{Verified:VerifiedForSendingStatus,DkimStatus:DkimAttributes.Status}' --output json
aws sesv2 get-account --region "$REGION" \
  --query '{ProductionAccess:ProductionAccessEnabled,SendingEnabled:SendingEnabled,Sent24h:SendQuota.SentLast24Hours,Max24h:SendQuota.Max24HourSend}' \
  --output json
