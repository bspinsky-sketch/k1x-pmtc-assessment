#!/usr/bin/env bash
# Deploy the mail stack.
#
#     bash infra/deploy-mail.sh
#
# Takes no arguments, on purpose. Every address this stack needs lives in
# `cdk.json` under `context` (and, because none of them is a secret, in the
# committed `cdk.example.json` alongside it), which is this project's
# convention for everything specific to a deploy.
#
# That is a deliberate difference from the sibling SMOMA project, whose script
# takes the addresses as positional arguments and carries defaults for them.
# Its own MAIL.md explains the hazard that produced those defaults: the blind
# copy is an environment variable on a deployed function, so a redeploy that
# left the argument off would drop the copy while reports went on sending
# perfectly, and nothing would look wrong, because the copy is blind. Keeping
# the values in `cdk.json` removes the argument entirely, which is a stronger
# version of the same fix -- there is nothing to forget to pass.
#
# A script rather than a command to paste, because the command needs
#     eval "$(aws configure export-credentials --format env)"
# and those nested quotes do not survive being pasted through every shell
# front end: the command comes back having produced no output at all, looking
# like nothing ran. Running a file needs no quoting.
#
# The export is needed because `aws login` writes a credential format the CDK
# CLI does not read on its own -- it reports "no credentials have been
# configured" while the AWS CLI itself is perfectly happy.
#
# **This needs Docker running.** The mailer is a container image because
# LibreOffice does not fit a zip. That is the one way this deploy differs from
# `cdk deploy PmtcApp`, which is pure Python and needs no daemon.
set -euo pipefail

cd "$(dirname "$0")"
echo "==> in $(pwd)"

if ! docker info >/dev/null 2>&1; then
  echo "!!! Docker is not running. The mailer is a container image (LibreOffice)," >&2
  echo "!!! so this deploy cannot build without it. Start Docker and try again." >&2
  exit 1
fi

echo "==> exporting credentials for the CDK CLI"
eval "$(aws configure export-credentials --format env)"
aws sts get-caller-identity --query Arn --output text

echo "==> deploying PmtcMail"
npx cdk deploy PmtcMail --require-approval never

echo
echo "==> done."
echo "==> If a notify address was set, confirm the subscription email AWS just sent."
echo "==> PmtcApp still has to be redeployed before the tool can call this function."
