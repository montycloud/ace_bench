#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Full offline end-to-end mock run of ACE Bench against LocalStack (fake AWS).
#
#   CFN fixtures ──► LocalStack ──► provisioner ──► resolver ──► toolloop agent
#                                                     (Ollama) ──► catalog ──► LocalStack
#                                                                       └──► evaluator
#
# Proves the whole pipeline works with NO real AWS account and NO external agent.
# Uses the `skynet` conda env, a community LocalStack container, and a local Ollama
# model as the agent under test.
#
# Usage:  bash local_test/run_mock_localstack.sh [csv_id]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
SCENARIO="${1:-COPS-point-in-time-recovery-disable-L1-952c1416}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"

# LocalStack credentials (dummy) + endpoint override — boto3 1.28+ routes here.
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4566

source /Users/cane/miniconda3/etc/profile.d/conda.sh
conda activate skynet

echo "▶ 1/4  ensure LocalStack (community) is up on :4566"
if ! curl -s -m 3 http://localhost:4566/_localstack/health | grep -q '"s3"'; then
  docker rm -f localstack-main 2>/dev/null || true
  docker run -d --name localstack-main -p 4566:4566 \
    -e SERVICES=s3,sqs,dynamodb,kms,iam,ec2,logs,cloudwatch,sns,cloudformation,sts,lambda \
    localstack/localstack:3.8 >/dev/null
  for i in $(seq 1 40); do
    curl -s -m 3 http://localhost:4566/_localstack/health | grep -q '"s3"' && break; sleep 3
  done
fi
echo "  LocalStack ready."

echo "▶ 2/4  deploy CloudFormation fixtures (LocalStack-compatible subset)"
deploy () {
  awslocal cloudformation create-stack --stack-name "$1" \
    --template-body "file://benchmark/fixtures/$2" \
    --capabilities CAPABILITY_NAMED_IAM CAPABILITY_IAM >/dev/null 2>&1 || true
  awslocal cloudformation wait stack-create-complete --stack-name "$1" 2>/dev/null || true
  printf "  %-20s %s\n" "$1" "$(awslocal cloudformation describe-stacks --stack-name "$1" --query 'Stacks[0].StackStatus' --output text 2>/dev/null)"
}
deploy wafr-nc-dynamodb non_compliant/DynamoDBNonCompliant.yml
deploy wafr-nc-sqs      non_compliant/SQSNonCompliant.yml
deploy wafr-comp-kms    compliant/KMSCMKCompliant.yml

echo "▶ 3/4  snapshot manifest from live stack outputs"
python -m runner.provisioner --region us-east-1 | tail -4

echo "▶ 4/4  run scenario '$SCENARIO' via toolloop + Ollama ($OLLAMA_MODEL)"
python -m local_test.run_localstack "$SCENARIO"
