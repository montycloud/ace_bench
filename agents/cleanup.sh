#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# cleanup.sh — tear down one, many, or all deployed AWS Bedrock Agents
#
# Removes per agent:
#   1. CloudFormation stack  (Lambda, IAM role, Secrets Manager secret, Function URL)
#   2. S3 deployment bucket  (emptied first, then deleted)
#   3. Local .env.<agent>    file
#
# Run without flags for an interactive menu:
#   ./cleanup.sh
#
# Or pass flags directly (non-interactive):
#   ./cleanup.sh --agent s3soa
#   ./cleanup.sh --agent s3soa --agent soa
#   ./cleanup.sh --all
#   ./cleanup.sh --agent eoa --region eu-west-1
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ALL_AGENTS=("s3soa" "soa" "eoa" "poa")

# ── Parse flags ───────────────────────────────────────────────────────────────
SELECTED_AGENTS=()
REGION="us-east-1"
CLEANUP_ALL=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --agent)  SELECTED_AGENTS+=("$2"); shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --all)    CLEANUP_ALL=true; shift ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

if $CLEANUP_ALL; then
  SELECTED_AGENTS=("${ALL_AGENTS[@]}")
fi

# ── Interactive selection (if no agents specified) ────────────────────────────
if [[ ${#SELECTED_AGENTS[@]} -eq 0 ]]; then
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║           AWS Bedrock Agents — Cleanup                      ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  echo "  Which agent(s) do you want to remove?"
  echo ""

  for i in "${!ALL_AGENTS[@]}"; do
    AGENT="${ALL_AGENTS[$i]}"
    NUM=$((i + 1))
    # Show whether the stack actually exists
    STATUS=$(aws cloudformation describe-stacks \
      --stack-name "${AGENT}" --region "${REGION}" \
      --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "not deployed")
    echo "  ${NUM}) ${AGENT}   [${STATUS}]"
  done

  echo ""
  echo "  5) all   — Remove all four agents"
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
        echo "ERROR: Unknown agent '${SEL}'."
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

  read -rp "  Region [us-east-1]: " REGION_INPUT
  [[ -n "$REGION_INPUT" ]] && REGION="$REGION_INPUT"
  echo ""
fi

# ── Verify credentials ────────────────────────────────────────────────────────
if ! aws sts get-caller-identity --region "${REGION}" &>/dev/null; then
  echo "ERROR: No valid AWS credentials."
  echo "       Run: aws configure   OR   aws sso login --profile <profile>"
  exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region "${REGION}")

# ── Show what will be deleted and ask for confirmation ────────────────────────
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           AWS Bedrock Agents — Cleanup                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Region  : ${REGION}"
echo "  Account : ${ACCOUNT_ID}"
echo ""
echo "  The following will be permanently deleted:"
echo ""

for AGENT in "${SELECTED_AGENTS[@]}"; do
  STACK="${AGENT}"
  BUCKET="${STACK}-deploy-${ACCOUNT_ID}"
  ENV_FILE="${SCRIPT_DIR}/.env.${AGENT}"

  STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "${STACK}" --region "${REGION}" \
    --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "not deployed")

  BUCKET_EXISTS=$(aws s3api head-bucket --bucket "${BUCKET}" --region "${REGION}" 2>/dev/null && echo "yes" || echo "no")

  echo "  [${AGENT}]"
  echo "    CloudFormation stack : ${STACK}  (${STACK_STATUS})"
  echo "      └─ Lambda function : ${STACK}-agent"
  echo "      └─ IAM role        : ${STACK}-lambda-role"
  echo "      └─ Secret          : ${STACK}/bearer-token"
  echo "      └─ Lambda URL      : (deleted with stack)"
  if [[ "$BUCKET_EXISTS" == "yes" ]]; then
    OBJECT_COUNT=$(aws s3api list-objects-v2 --bucket "${BUCKET}" --region "${REGION}" \
      --query "length(Contents)" --output text 2>/dev/null || echo "0")
    [[ "$OBJECT_COUNT" == "None" ]] && OBJECT_COUNT="0"
    echo "    S3 deployment bucket : ${BUCKET}  (${OBJECT_COUNT} object(s))"
  else
    echo "    S3 deployment bucket : ${BUCKET}  (does not exist)"
  fi
  if [[ -f "$ENV_FILE" ]]; then
    echo "    Local file           : .env.${AGENT}"
  fi
  echo ""
done

echo "  ⚠  This cannot be undone."
echo ""
read -rp "  Type 'yes' to confirm deletion: " CONFIRM
echo ""

if [[ "$CONFIRM" != "yes" ]]; then
  echo "  Cancelled. Nothing was deleted."
  exit 0
fi

# ── Function: clean up one agent ──────────────────────────────────────────────
cleanup_agent() {
  local AGENT="$1"
  local STACK="${AGENT}"
  local BUCKET="${STACK}-deploy-${ACCOUNT_ID}"
  local ENV_FILE="${SCRIPT_DIR}/.env.${AGENT}"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Cleaning up: ${AGENT}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # ── 1. Delete CloudFormation stack ─────────────────────────────────────────
  STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "${STACK}" --region "${REGION}" \
    --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "DOES_NOT_EXIST")

  if [[ "$STACK_STATUS" == "DOES_NOT_EXIST" ]]; then
    echo "▶  CloudFormation stack '${STACK}' does not exist — skipping"
  else
    echo "▶  Deleting CloudFormation stack '${STACK}'..."

    # If stack is in a failed/stuck state, try to continue anyway
    if [[ "$STACK_STATUS" == *"_IN_PROGRESS" ]]; then
      echo "  ⏳ Stack is ${STACK_STATUS}, waiting for it to settle first..."
      aws cloudformation wait stack-create-complete \
        --stack-name "${STACK}" --region "${REGION}" 2>/dev/null || \
      aws cloudformation wait stack-update-complete \
        --stack-name "${STACK}" --region "${REGION}" 2>/dev/null || true
    fi

    aws cloudformation delete-stack \
      --stack-name "${STACK}" \
      --region "${REGION}"

    echo "  ⏳ Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete \
      --stack-name "${STACK}" \
      --region "${REGION}"

    echo "  ✓ Stack deleted (Lambda, IAM role, Secret, Function URL all removed)"
  fi

  # ── 2. Empty and delete S3 deployment bucket ────────────────────────────────
  if aws s3api head-bucket --bucket "${BUCKET}" --region "${REGION}" 2>/dev/null; then
    echo "▶  Emptying S3 bucket: ${BUCKET}..."

    # Delete all object versions (handles versioned buckets)
    VERSIONS=$(aws s3api list-object-versions \
      --bucket "${BUCKET}" \
      --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
      --output json 2>/dev/null || echo '{"Objects":[]}')

    if [[ "$(echo "$VERSIONS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('Objects') or []))")" -gt 0 ]]; then
      echo "$VERSIONS" | aws s3api delete-objects \
        --bucket "${BUCKET}" \
        --delete "$(echo "$VERSIONS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d))")" \
        --region "${REGION}" >/dev/null
    fi

    # Delete all delete markers
    MARKERS=$(aws s3api list-object-versions \
      --bucket "${BUCKET}" \
      --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' \
      --output json 2>/dev/null || echo '{"Objects":[]}')

    if [[ "$(echo "$MARKERS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('Objects') or []))")" -gt 0 ]]; then
      echo "$MARKERS" | aws s3api delete-objects \
        --bucket "${BUCKET}" \
        --delete "$(echo "$MARKERS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d))")" \
        --region "${REGION}" >/dev/null
    fi

    # Delete remaining objects (non-versioned)
    aws s3 rm "s3://${BUCKET}" --recursive --region "${REGION}" >/dev/null 2>&1 || true

    echo "▶  Deleting S3 bucket: ${BUCKET}..."
    aws s3api delete-bucket --bucket "${BUCKET}" --region "${REGION}"
    echo "  ✓ S3 bucket deleted"
  else
    echo "▶  S3 bucket '${BUCKET}' does not exist — skipping"
  fi

  # ── 3. Remove local .env file ───────────────────────────────────────────────
  if [[ -f "$ENV_FILE" ]]; then
    rm -f "$ENV_FILE"
    echo "  ✓ Removed .env.${AGENT}"
  fi

  # Also clean up .env if it points to this agent
  if [[ -f "${SCRIPT_DIR}/.env" ]]; then
    ENV_URL=$(grep "AGENT_URL" "${SCRIPT_DIR}/.env" 2>/dev/null | cut -d= -f2- || echo "")
    AGENT_URL=$(grep "AGENT_URL" "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || echo "")
    if [[ -n "$ENV_URL" && "$ENV_URL" == "$AGENT_URL" ]]; then
      rm -f "${SCRIPT_DIR}/.env"
      echo "  ✓ Removed .env (was pointing to ${AGENT})"
    fi
  fi

  echo "  ✓ ${AGENT} cleanup complete"
}

# ── Run cleanup for each selected agent ───────────────────────────────────────
CLEANED=()
FAILED=()

for AGENT in "${SELECTED_AGENTS[@]}"; do
  if cleanup_agent "$AGENT"; then
    CLEANED+=("$AGENT")
  else
    echo "  ✗ Failed to clean up ${AGENT}"
    FAILED+=("$AGENT")
  fi
done

# ── Final summary ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Cleanup Complete ✓                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [[ ${#CLEANED[@]} -gt 0 ]]; then
  echo "  Removed: ${CLEANED[*]}"
fi
if [[ ${#FAILED[@]} -gt 0 ]]; then
  echo "  Failed : ${FAILED[*]}"
  echo ""
  echo "  For failed agents, check CloudFormation in the AWS console:"
  echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}"
fi
echo ""
