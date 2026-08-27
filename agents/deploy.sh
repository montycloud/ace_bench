#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — deploy one, many, or all AWS Bedrock Agents to Lambda
#
# Run without flags for an interactive menu:
#   ./deploy.sh
#
# Or pass flags directly (non-interactive):
#   ./deploy.sh --agent s3soa
#   ./deploy.sh --agent s3soa --agent soa          # deploy two agents
#   ./deploy.sh --all                               # deploy all four agents
#   ./deploy.sh --agent eoa --region eu-west-1
#
# Each agent gets its own Lambda function, IAM role, and Secrets Manager secret.
# Credentials are written to .env.<agent> after each deployment.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ALL_AGENTS=("s3soa" "soa" "eoa" "poa")

# ── Parse flags ───────────────────────────────────────────────────────────────
SELECTED_AGENTS=()
REGION="us-east-1"
DEPLOY_ALL=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --agent)  SELECTED_AGENTS+=("$2"); shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --all)    DEPLOY_ALL=true; shift ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

if $DEPLOY_ALL; then
  SELECTED_AGENTS=("${ALL_AGENTS[@]}")
fi

# ── Interactive selection (if no agents specified) ────────────────────────────
if [[ ${#SELECTED_AGENTS[@]} -eq 0 ]]; then
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║           AWS Bedrock Agents — Deployment                   ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  echo "  Which agent(s) do you want to deploy?"
  echo ""
  echo "  1) s3soa — S3 Security Optimization Agent"
  echo "             Scans S3 buckets for public access, encryption,"
  echo "             logging, and ACL issues. Remediates after approval."
  echo ""
  echo "  2) soa   — Storage Optimization Agent"
  echo "             Finds unattached EBS volumes, stale snapshots,"
  echo "             and orphaned AMIs. Estimates cost. Cleans up after approval."
  echo ""
  echo "  3) eoa   — EC2 Optimization Agent"
  echo "             Analyzes CPU utilization, identifies over-provisioned"
  echo "             instances, recommends right-sizing with cost savings."
  echo ""
  echo "  4) poa   — Processor Optimization Agent"
  echo "             Inventories Intel/AMD/Graviton instances, recommends"
  echo "             Graviton migration paths, executes after approval."
  echo ""
  echo "  5) all   — Deploy all four agents"
  echo ""
  read -rp "  Enter number(s) or name(s), space-separated [e.g. 1 3 or s3soa eoa]: " SELECTION_INPUT
  echo ""

  for SEL in $SELECTION_INPUT; do
    case "$SEL" in
      1|s3soa) SELECTED_AGENTS+=("s3soa") ;;
      2|soa)   SELECTED_AGENTS+=("soa")   ;;
      3|eoa)   SELECTED_AGENTS+=("eoa")   ;;
      4|poa)   SELECTED_AGENTS+=("poa")   ;;
      5|all)   SELECTED_AGENTS=("${ALL_AGENTS[@]}"); break ;;
      *)
        echo "ERROR: Unknown agent '${SEL}'. Valid: 1-5, s3soa, soa, eoa, poa, all"
        exit 1
        ;;
    esac
  done

  if [[ ${#SELECTED_AGENTS[@]} -eq 0 ]]; then
    echo "ERROR: No agents selected."
    exit 1
  fi

  # Remove duplicates (bash 3.2 compatible)
  DEDUPED=()
  while IFS= read -r line; do
    DEDUPED+=("$line")
  done < <(printf '%s\n' "${SELECTED_AGENTS[@]}" | sort -u)
  SELECTED_AGENTS=("${DEDUPED[@]}")

  # Interactive region
  read -rp "  Region [us-east-1]: " REGION_INPUT
  [[ -n "$REGION_INPUT" ]] && REGION="$REGION_INPUT"
  echo ""
fi

# ── Shared prerequisite check (run once) ─────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           AWS Bedrock Agents — Deployment                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Agents  : ${SELECTED_AGENTS[*]}"
echo "  Region  : ${REGION}"
echo ""

echo "▶  Checking prerequisites..."
for cmd in aws python3 pip3 zip; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "  ✗ '${cmd}' not found. Please install it."
    exit 1
  fi
done
echo "  ✓ aws, python3, pip3, zip"

if ! aws sts get-caller-identity --region "${REGION}" &>/dev/null; then
  echo "  ✗ No valid AWS credentials."
  echo "    Run: aws configure   OR   aws sso login --profile <profile>"
  exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region "${REGION}")
echo "  ✓ AWS credentials valid (account: ${ACCOUNT_ID})"

echo ""
echo "▶  Checking Bedrock model access..."
MODEL_STATUS=$(aws bedrock list-inference-profiles --region "${REGION}" \
  --query "inferenceProfileSummaries[?inferenceProfileId=='us.anthropic.claude-sonnet-4-6'].status" \
  --output text 2>/dev/null || echo "")
if [[ "${MODEL_STATUS}" != "ACTIVE" ]]; then
  echo "  ⚠  Claude Sonnet 4 not found as ACTIVE in ${REGION}."
  echo "     Enable it at: https://console.aws.amazon.com/bedrock/home#/modelaccess"
  read -rp "  Press Enter to continue anyway, or Ctrl-C to abort: "
else
  echo "  ✓ Claude Sonnet 4 (us.anthropic.claude-sonnet-4-6) is ACTIVE"
fi

# ── Function: deploy one agent ────────────────────────────────────────────────
deploy_agent() {
  local AGENT="$1"
  local STACK="${AGENT}"   # stack name = agent name (s3soa, soa, eoa, poa)

  local AGENT_DIR="${SCRIPT_DIR}/${AGENT}"
  local CFN_TEMPLATE="${AGENT_DIR}/cloudformation.yaml"
  local REQUIREMENTS="${AGENT_DIR}/agent/requirements.txt"
  local HANDLER="${AGENT_DIR}/agent/handler.py"
  local BUCKET="${STACK}-deploy-${ACCOUNT_ID}"
  local KEY="${AGENT}/lambda.zip"
  local ZIP_TMP="/tmp/${AGENT}_lambda.zip"
  local ENV_FILE="${SCRIPT_DIR}/.env.${AGENT}"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Deploying: ${AGENT}  →  stack: ${STACK}  →  region: ${REGION}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # ── S3 deployment bucket ────────────────────────────────────────────────────
  echo "▶  Setting up deployment bucket: ${BUCKET}"
  if aws s3api head-bucket --bucket "${BUCKET}" --region "${REGION}" 2>/dev/null; then
    echo "  ✓ Bucket already exists"
  else
    if [[ "${REGION}" == "us-east-1" ]]; then
      aws s3api create-bucket --bucket "${BUCKET}" --region "${REGION}" >/dev/null
    else
      aws s3api create-bucket --bucket "${BUCKET}" --region "${REGION}" \
        --create-bucket-configuration LocationConstraint="${REGION}" >/dev/null
    fi
    aws s3api put-public-access-block --bucket "${BUCKET}" \
      --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
      >/dev/null
    echo "  ✓ Bucket created (public access blocked)"
  fi

  # ── Build Lambda zip ────────────────────────────────────────────────────────
  echo "▶  Building Lambda package..."
  local BUILD_DIR
  BUILD_DIR=$(mktemp -d)

  pip3 install -q \
    -r "${REQUIREMENTS}" \
    --target "${BUILD_DIR}" \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.12 2>&1 \
    | grep -v "dependency resolver\|but you have\|incompatible" || true

  cp "${HANDLER}" "${BUILD_DIR}/"
  (cd "${BUILD_DIR}" && zip -qr "${ZIP_TMP}" .)
  rm -rf "${BUILD_DIR}"

  local ZIP_SIZE
  ZIP_SIZE=$(du -sh "${ZIP_TMP}" | cut -f1)
  echo "  ✓ Package built (${ZIP_SIZE})"

  # ── Upload ──────────────────────────────────────────────────────────────────
  # Use a content hash in the S3 key so CloudFormation always detects a change
  local ZIP_HASH
  ZIP_HASH=$(md5 -q "${ZIP_TMP}" 2>/dev/null || md5sum "${ZIP_TMP}" | cut -d' ' -f1)
  KEY="${AGENT}/${ZIP_HASH}.zip"
  echo "▶  Uploading to s3://${BUCKET}/${KEY}..."
  aws s3 cp "${ZIP_TMP}" "s3://${BUCKET}/${KEY}" --region "${REGION}" >/dev/null
  rm -f "${ZIP_TMP}"
  echo "  ✓ Uploaded"

  # ── CloudFormation deploy ───────────────────────────────────────────────────
  echo "▶  Deploying CloudFormation stack '${STACK}'..."

  local STATUS
  STATUS=$(aws cloudformation describe-stacks \
    --stack-name "${STACK}" --region "${REGION}" \
    --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "DOES_NOT_EXIST")

  if [[ "${STATUS}" == *"_IN_PROGRESS" ]]; then
    echo "  ⏳ Stack is ${STATUS}, waiting..."
    aws cloudformation wait stack-create-complete \
      --stack-name "${STACK}" --region "${REGION}" 2>/dev/null || \
    aws cloudformation wait stack-update-complete \
      --stack-name "${STACK}" --region "${REGION}" 2>/dev/null || true
  fi

  aws cloudformation deploy \
    --template-file "${CFN_TEMPLATE}" \
    --stack-name "${STACK}" \
    --region "${REGION}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        DeploymentBucket="${BUCKET}" \
        DeploymentKey="${KEY}" \
    --no-fail-on-empty-changeset

  echo "  ✓ Stack deployed"

  # ── Fetch outputs ───────────────────────────────────────────────────────────
  echo "▶  Fetching endpoint and bearer token..."

  local AGENT_URL
  AGENT_URL=$(aws cloudformation describe-stacks \
    --stack-name "${STACK}" --region "${REGION}" \
    --query "Stacks[0].Outputs[?OutputKey=='AgentUrl'].OutputValue" \
    --output text)

  local SECRET_ARN
  SECRET_ARN=$(aws cloudformation describe-stacks \
    --stack-name "${STACK}" --region "${REGION}" \
    --query "Stacks[0].Outputs[?OutputKey=='BearerTokenSecretArn'].OutputValue" \
    --output text)

  local TOKEN
  TOKEN=$(aws secretsmanager get-secret-value \
    --secret-id "${SECRET_ARN}" --region "${REGION}" \
    --query SecretString --output text \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

  # Write per-agent .env file
  cat > "${ENV_FILE}" <<ENVEOF
AGENT_URL=${AGENT_URL}
AGENT_TOKEN=${TOKEN}
ENVEOF

  echo "  ✓ Credentials saved to .env.${AGENT}"
  echo ""
  echo "  Lambda function : ${STACK}-agent"
  echo "  Endpoint        : ${AGENT_URL}"
  echo "  Token           : ${TOKEN}"
}

# ── Deploy each selected agent ────────────────────────────────────────────────
DEPLOYED=()
FAILED=()

for AGENT in "${SELECTED_AGENTS[@]}"; do
  if deploy_agent "$AGENT"; then
    DEPLOYED+=("$AGENT")
  else
    echo "  ✗ Failed to deploy ${AGENT}"
    FAILED+=("$AGENT")
  fi
done

# ── Final summary ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  Deployment Complete ✓                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

for AGENT in "${DEPLOYED[@]}"; do
  ENV_FILE="${SCRIPT_DIR}/.env.${AGENT}"
  AGENT_URL=$(grep AGENT_URL "${ENV_FILE}" | cut -d= -f2-)
  TOKEN=$(grep AGENT_TOKEN "${ENV_FILE}" | cut -d= -f2-)
  echo "  ${AGENT}"
  echo "    Endpoint : ${AGENT_URL}"
  echo "    Token    : ${TOKEN}"
  echo "    Env file : .env.${AGENT}"
  echo ""
done

if [[ ${#FAILED[@]} -gt 0 ]]; then
  echo "  ✗ Failed: ${FAILED[*]}"
  echo ""
fi

echo "  ▶  Start chatting:"
echo "     python3 invoke_remote.py"
echo ""
echo "  ▶  See TESTING_GUIDE.md for API usage and testing instructions."
echo ""
