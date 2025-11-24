#!/usr/bin/env bash
set -euo pipefail

# Teardown script for serverless platform
# Usage: ENV=dev REGION=us-east-1 ./destroy.sh
# Optional: APP_STACK (SAM stack name), INFRA_STACK (main infra stack name)

: "${ENV:?ENV is required (e.g., dev)}"
: "${REGION:?REGION is required (e.g., us-east-1)}"

APP_STACK=${APP_STACK:-serverless-app-${ENV}}
INFRA_STACK=${INFRA_STACK:-serverless-platform-${ENV}}

aws() { command aws --region "$REGION" "$@"; }

echo "[1/2] Deleting application stack: $APP_STACK"
aws cloudformation delete-stack --stack-name "$APP_STACK" || true
aws cloudformation wait stack-delete-complete --stack-name "$APP_STACK" || true

echo "[2/2] Deleting infrastructure stack: $INFRA_STACK"
aws cloudformation delete-stack --stack-name "$INFRA_STACK" || true
aws cloudformation wait stack-delete-complete --stack-name "$INFRA_STACK" || true

echo "Teardown complete."
