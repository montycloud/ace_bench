#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# WAFR CloudFormation Stack Manager
# Deploy & Cleanup compliant / non-compliant / combined CFN stacks
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMP_DIR="${SCRIPT_DIR}/compliant"
NONCOMP_DIR="${SCRIPT_DIR}/non_compliant"

# Stack name prefixes — cleanup ONLY touches stacks with these prefixes
PREFIX_COMP="wafr-comp"
PREFIX_NC="wafr-nc"
PREFIX_MIX="wafr-mix"
ALL_PREFIXES=("$PREFIX_COMP" "$PREFIX_NC" "$PREFIX_MIX")

# ─── Colors & Symbols ────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC_CLR='\033[0m'

TICK="✔"
CROSS="✘"
ARROW="➜"
WARN="⚠"

# ─── UI Helpers ───────────────────────────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC_CLR}"
    echo -e "${CYAN}${BOLD}║        WAFR CloudFormation Stack Manager                    ║${NC_CLR}"
    echo -e "${CYAN}${BOLD}║        Deploy & Cleanup Assessment Resources                ║${NC_CLR}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC_CLR}"
    echo ""
}

print_line()    { echo -e "  $1"; }
print_success() { echo -e "  ${GREEN}${TICK} $1${NC_CLR}"; }
print_error()   { echo -e "  ${RED}${CROSS} $1${NC_CLR}"; }
print_warn()    { echo -e "  ${YELLOW}${WARN}  $1${NC_CLR}"; }
print_info()    { echo -e "  ${CYAN}${ARROW} $1${NC_CLR}"; }
print_step()    { echo -e "  ${MAGENTA}$1${NC_CLR}"; }
print_dim()     { echo -e "  ${DIM}$1${NC_CLR}"; }
print_header()  { echo ""; echo -e "${BLUE}${BOLD}── $1 ─────────────────────────────────────${NC_CLR}"; echo ""; }

confirm() {
    local msg="$1"
    echo ""
    echo -ne "  ${YELLOW}${msg} [y/N]: ${NC_CLR}"
    read -r answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

# ─── Region Selection ─────────────────────────────────────────────────────────

SELECTED_REGION=""
CLEANUP_REGIONS=()

REGION_LIST=(
    "us-east-1      US East (N. Virginia)"
    "us-east-2      US East (Ohio)"
    "us-west-1      US West (N. California)"
    "us-west-2      US West (Oregon)"
    "eu-west-1      Europe (Ireland)"
    "eu-west-2      Europe (London)"
    "eu-central-1   Europe (Frankfurt)"
    "ap-south-1     Asia Pacific (Mumbai)"
    "ap-southeast-1 Asia Pacific (Singapore)"
    "ap-northeast-1 Asia Pacific (Tokyo)"
)

show_region_menu() {
    for i in "${!REGION_LIST[@]}"; do
        printf "    ${BOLD}%2d)${NC_CLR}  %s\n" "$((i+1))" "${REGION_LIST[$i]}"
    done
    echo ""
    echo -e "    ${BOLD} 0)${NC_CLR}  Enter a custom region"
    echo ""
}

pick_one_region() {
    while true; do
        echo -ne "  ${CYAN}Enter choice: ${NC_CLR}"
        read -r choice
        if [[ "$choice" == "0" ]]; then
            echo -ne "  ${CYAN}Region code (e.g. eu-north-1): ${NC_CLR}"
            read -r SELECTED_REGION
            [[ -n "$SELECTED_REGION" ]] && break
        elif [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#REGION_LIST[@]} )); then
            SELECTED_REGION=$(echo "${REGION_LIST[$((choice-1))]}" | awk '{print $1}')
            break
        fi
        print_error "Invalid choice."
    done
}

select_region() {
    local label="${1:-deployment}"
    print_header "Select AWS Region for ${label}"
    show_region_menu
    pick_one_region
    print_success "Region: ${BOLD}${SELECTED_REGION}${NC_CLR}"
}

select_cleanup_regions() {
    print_header "Select Region(s) for Cleanup"

    echo -e "  ${YELLOW}${WARN}  WARNING: Cleanup will delete ALL WAFR stacks in the selected region(s).${NC_CLR}"
    echo -e "  ${YELLOW}${WARN}  Only select regions where you want WAFR stacks removed.${NC_CLR}"
    echo -e "  ${DIM}  (Stacks not prefixed with wafr-comp-, wafr-nc-, wafr-mix- are never touched.)${NC_CLR}"
    echo ""
    echo -e "  ${DIM}Enter region codes separated by spaces.${NC_CLR}"
    echo -e "  ${DIM}Examples: us-east-1   or   us-east-1 us-west-2${NC_CLR}"
    echo ""

    CLEANUP_REGIONS=()

    while true; do
        echo -ne "  ${CYAN}Region(s): ${NC_CLR}"
        read -r input

        if [[ -z "$input" ]]; then
            print_error "Enter at least one region."
            continue
        fi

        for r in $input; do
            CLEANUP_REGIONS+=("$r")
        done

        # Deduplicate
        local unique=()
        for r in "${CLEANUP_REGIONS[@]}"; do
            local dup=false
            for u in "${unique[@]+"${unique[@]}"}"; do
                [[ "$r" == "$u" ]] && dup=true && break
            done
            [[ "$dup" == false ]] && unique+=("$r")
        done
        CLEANUP_REGIONS=("${unique[@]}")
        break
    done

    echo ""
    print_info "Regions selected for cleanup:"
    for r in "${CLEANUP_REGIONS[@]}"; do
        print_dim "    ${r}"
    done
}


# ─── Stack Discovery (ONLY our prefixes — never touches other stacks) ────────

discover_wafr_stacks() {
    local region="$1"
    local found=""

    for prefix in "${ALL_PREFIXES[@]}"; do
        local result
        result=$(aws cloudformation list-stacks \
            --region "$region" \
            --stack-status-filter \
                CREATE_COMPLETE UPDATE_COMPLETE ROLLBACK_COMPLETE \
                CREATE_FAILED UPDATE_ROLLBACK_COMPLETE \
            --query "StackSummaries[?starts_with(StackName, '${prefix}')].StackName" \
            --output text 2>/dev/null || true)
        if [[ -n "$result" && "$result" != "None" ]]; then
            found+=" ${result}"
        fi
    done

    echo "$found" | xargs  # trim whitespace
}

check_and_handle_existing() {
    local region="$1"

    print_header "Checking for existing WAFR stacks in ${region}"

    local existing
    existing=$(discover_wafr_stacks "$region")

    if [[ -z "$existing" ]]; then
        print_success "No existing WAFR stacks found. Ready to deploy."
        return 0
    fi

    print_warn "Found existing WAFR stacks in ${BOLD}${region}${NC_CLR}:"
    echo ""
    for stack in $existing; do
        local status
        status=$(aws cloudformation describe-stacks \
            --stack-name "$stack" --region "$region" \
            --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "UNKNOWN")
        local color="${GREEN}"
        [[ "$status" == *"FAILED"* || "$status" == *"ROLLBACK"* ]] && color="${RED}"
        printf "    %-42s ${color}%s${NC_CLR}\n" "$stack" "$status"
    done
    echo ""

    print_info "Auto-cleaning up before deploy ..."
    run_cleanup "$region"
    return 0
}

# ─── S3 Bucket Emptying (versioned objects + delete markers + pagination) ─────

empty_s3_bucket() {
    local bucket="$1"
    local region="$2"

    # Verify bucket exists
    if ! aws s3api head-bucket --bucket "$bucket" --region "$region" 2>/dev/null; then
        print_dim "    Bucket ${bucket} not found, skipping"
        return 0
    fi

    echo -ne "    Emptying ${BOLD}${bucket}${NC_CLR} ... "

    # Delete all object versions in batches
    local key_marker="" version_marker="" truncated="true"
    while [[ "$truncated" == "true" ]]; do
        local cmd="aws s3api list-object-versions --bucket ${bucket} --region ${region} --max-items 1000 --output json"
        [[ -n "$key_marker" ]] && cmd+=" --key-marker ${key_marker} --version-id-marker ${version_marker}"

        local response
        response=$(eval "$cmd" 2>/dev/null || echo '{}')

        # Build delete payload from Versions
        local delete_payload
        delete_payload=$(echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
objects = []
for v in data.get('Versions', []):
    objects.append({'Key': v['Key'], 'VersionId': v['VersionId']})
for d in data.get('DeleteMarkers', []):
    objects.append({'Key': d['Key'], 'VersionId': d['VersionId']})
if objects:
    print(json.dumps({'Objects': objects[:1000], 'Quiet': True}))
else:
    print('')
" 2>/dev/null || echo "")

        if [[ -n "$delete_payload" ]]; then
            aws s3api delete-objects \
                --bucket "$bucket" --region "$region" \
                --delete "$delete_payload" > /dev/null 2>&1 || true
        fi

        truncated=$(echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('true' if data.get('IsTruncated', False) else 'false')
" 2>/dev/null || echo "false")

        if [[ "$truncated" == "true" ]]; then
            key_marker=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('NextKeyMarker',''))" 2>/dev/null || echo "")
            version_marker=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('NextVersionIdMarker',''))" 2>/dev/null || echo "")
        fi
    done

    # Final safety pass — catch anything left
    aws s3 rm "s3://${bucket}" --recursive --region "$region" > /dev/null 2>&1 || true

    echo -e "${GREEN}done${NC_CLR}"
}

# ─── Pre-delete: stop trails, empty buckets for a stack ───────────────────────

prepare_stack_for_deletion() {
    local stack="$1"
    local region="$2"

    local resources
    resources=$(aws cloudformation list-stack-resources \
        --stack-name "$stack" --region "$region" \
        --query "StackResourceSummaries[].{Type:ResourceType,Id:PhysicalResourceId}" \
        --output json 2>/dev/null || echo "[]")

    # Stop CloudTrails first
    local trails
    trails=$(echo "$resources" | python3 -c "
import sys, json
for r in json.load(sys.stdin):
    if r['Type'] == 'AWS::CloudTrail::Trail':
        print(r['Id'])
" 2>/dev/null || true)

    for trail in $trails; do
        [[ -z "$trail" ]] && continue
        echo -ne "    Stopping CloudTrail ${BOLD}${trail}${NC_CLR} ... "
        aws cloudtrail stop-logging --name "$trail" --region "$region" > /dev/null 2>&1 || true
        echo -e "${GREEN}done${NC_CLR}"
    done

    # Empty S3 buckets
    local buckets
    buckets=$(echo "$resources" | python3 -c "
import sys, json
for r in json.load(sys.stdin):
    if r['Type'] == 'AWS::S3::Bucket':
        print(r['Id'])
" 2>/dev/null || true)

    for bucket in $buckets; do
        [[ -z "$bucket" ]] && continue
        empty_s3_bucket "$bucket" "$region"
    done

    # Pre-handle IAM password policy custom resource.
    # Root cause: the Lambda delete handler calls iam.deleteAccountPasswordPolicy()
    # and passes any error (including NoSuchEntity) to cfnresponse.FAILED.
    # Fix: patch the Lambda to always return SUCCESS on Delete, then delete the stack.
    local has_password_policy
    has_password_policy=$(echo "$resources" | python3 -c "
import sys, json
for r in json.load(sys.stdin):
    if r['Type'] == 'Custom::PasswordPolicy':
        print('yes')
        break
" 2>/dev/null || true)

    if [[ "$has_password_policy" == "yes" ]]; then
        # Delete the password policy via CLI first
        echo -ne "    Pre-deleting IAM password policy ... "
        aws iam delete-account-password-policy 2>/dev/null \
            && echo -e "${GREEN}done${NC_CLR}" \
            || echo -e "${DIM}already gone${NC_CLR}"

        # Patch the Lambda to always return SUCCESS on Delete
        local lambda_name
        lambda_name=$(echo "$resources" | python3 -c "
import sys, json
for r in json.load(sys.stdin):
    if r['Type'] == 'AWS::Lambda::Function':
        print(r['Id'])
        break
" 2>/dev/null || true)

        if [[ -n "$lambda_name" ]]; then
            echo -ne "    Patching Lambda for clean deletion ... "
            local tmp_zip
            tmp_zip=$(mktemp /tmp/wafr_lambda_XXXXXX.zip)
            python3 - <<'PYEOF' "$tmp_zip"
import sys, zipfile
out = sys.argv[1]
code = """'use strict';
const response = require('cfn-response');
exports.handler = (event, context, cb) => {
  response.send(event, context, response.SUCCESS, {});
};
"""
with zipfile.ZipFile(out, 'w') as z:
    z.writestr('index.js', code)
PYEOF
            aws lambda update-function-code \
                --function-name "$lambda_name" \
                --region "$region" \
                --zip-file "fileb://${tmp_zip}" > /dev/null 2>&1 \
                && echo -e "${GREEN}done${NC_CLR}" \
                || echo -e "${DIM}skipped${NC_CLR}"
            rm -f "$tmp_zip"
        fi
    fi
}

# ─── Delete a single stack ────────────────────────────────────────────────────

delete_stack() {
    local stack="$1"
    local region="$2"

    # Check existence
    local status
    status=$(aws cloudformation describe-stacks \
        --stack-name "$stack" --region "$region" \
        --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")

    [[ "$status" == "NOT_FOUND" ]] && return 0

    echo -ne "  Deleting ${BOLD}${stack}${NC_CLR} "

    # Pre-delete cleanup
    prepare_stack_for_deletion "$stack" "$region"

    echo -ne "  Deleting stack ... "
    aws cloudformation delete-stack --stack-name "$stack" --region "$region" > /dev/null 2>&1

    if aws cloudformation wait stack-delete-complete \
        --stack-name "$stack" --region "$region" 2>/dev/null; then
        echo -e "${GREEN}${TICK} deleted${NC_CLR}"
    else
        echo -e "${RED}${CROSS} failed — check AWS Console${NC_CLR}"
    fi
}

# Prep a stack (stop trails, empty S3) and fire delete without waiting
initiate_delete() {
    local stack="$1"
    local region="$2"

    local status
    status=$(aws cloudformation describe-stacks \
        --stack-name "$stack" --region "$region" \
        --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")

    if [[ "$status" == "NOT_FOUND" || "$status" == "DELETE_COMPLETE" ]]; then
        return 1  # skip
    fi

    print_info "Preparing ${BOLD}${stack}${NC_CLR} (status: ${status}) ..."
    prepare_stack_for_deletion "$stack" "$region"

    echo -ne "  Deleting ${BOLD}${stack}${NC_CLR} ... "
    if aws cloudformation delete-stack --stack-name "$stack" --region "$region" 2>/dev/null; then
        echo -e "${GREEN}initiated${NC_CLR}"
    else
        echo -e "${RED}delete call failed${NC_CLR}"
    fi
    return 0
}

# Retry a DELETE_FAILED stack — re-run prepare and retry delete
force_delete_failed() {
    local stack="$1"
    local region="$2"

    local status
    status=$(aws cloudformation describe-stacks \
        --stack-name "$stack" --region "$region" \
        --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "GONE")

    [[ "$status" != "DELETE_FAILED" ]] && return 0

    print_warn "Retrying ${BOLD}${stack}${NC_CLR} (DELETE_FAILED) ..."

    # Re-run pre-delete prep (e.g. ensure password policy is gone)
    prepare_stack_for_deletion "$stack" "$region"

    aws cloudformation delete-stack \
        --stack-name "$stack" --region "$region" > /dev/null 2>&1 || true

    echo -ne "  Waiting for retry ... "
    if aws cloudformation wait stack-delete-complete \
        --stack-name "$stack" --region "$region" 2>/dev/null; then
        echo -e "${GREEN}${TICK} deleted${NC_CLR}"
    else
        local final_status
        final_status=$(aws cloudformation describe-stacks \
            --stack-name "$stack" --region "$region" \
            --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "GONE")
        if [[ "$final_status" == "GONE" || "$final_status" == "DELETE_COMPLETE" ]]; then
            echo -e "${GREEN}${TICK} deleted${NC_CLR}"
        else
            echo -e "${RED}${CROSS} still failed (${final_status}) — check AWS Console${NC_CLR}"
        fi
    fi
}

# Wait for a list of stacks to finish deleting, auto-retry DELETE_FAILED
wait_for_deletes() {
    local region="$1"
    shift
    local stacks=("$@")

    [[ ${#stacks[@]} -eq 0 ]] && return 0

    local failed_stacks=()
    for stack_name in "${stacks[@]}"; do
        echo -ne "  Waiting for ${BOLD}${stack_name}${NC_CLR} ... "
        if aws cloudformation wait stack-delete-complete \
            --stack-name "$stack_name" --region "$region" 2>/dev/null; then
            echo -e "${GREEN}${TICK} deleted${NC_CLR}"
        else
            local st
            st=$(aws cloudformation describe-stacks \
                --stack-name "$stack_name" --region "$region" \
                --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "GONE")
            if [[ "$st" == "GONE" || "$st" == "DELETE_COMPLETE" ]]; then
                echo -e "${GREEN}${TICK} deleted${NC_CLR}"
            else
                echo -e "${RED}${CROSS} failed (status: ${st})${NC_CLR}"
                failed_stacks+=("$stack_name")
            fi
        fi
    done

    # Auto-retry any DELETE_FAILED stacks
    if [[ ${#failed_stacks[@]} -gt 0 ]]; then
        echo ""
        print_warn "Retrying ${#failed_stacks[@]} failed stack(s) with force-delete ..."
        for stack_name in "${failed_stacks[@]}"; do
            force_delete_failed "$stack_name" "$region"
        done
    fi
}

# Delete a batch of stacks in parallel: prep all, fire all, wait all
delete_stacks_parallel() {
    local region="$1"
    shift
    local stacks=("$@")
    local to_wait=()

    for stack in "${stacks[@]}"; do
        initiate_delete "$stack" "$region" && to_wait+=("$stack")
    done

    if [[ ${#to_wait[@]} -gt 0 ]]; then
        echo ""
        print_dim "Waiting for ${#to_wait[@]} stack(s) to delete ..."
        wait_for_deletes "$region" "${to_wait[@]}"
    fi
}


# ─── Cleanup (auto-discovers, correct order, ONLY our stacks) ─────────────────

run_cleanup() {
    local region="$1"

    print_header "Cleanup WAFR Stacks in ${region}"

    local existing
    existing=$(discover_wafr_stacks "$region")

    if [[ -z "$existing" ]]; then
        print_success "No WAFR stacks found in ${region}. Nothing to clean up."
        return 0
    fi

    print_info "Found these WAFR stacks to delete:"
    echo ""
    for s in $existing; do
        print_dim "    ${s}"
    done
    echo ""
    print_warn "Only stacks prefixed with wafr-comp-, wafr-nc-, wafr-mix- are touched."
    print_warn "No other stacks in your account will be affected."

    # ── Phase 1: All non-VPC stacks in parallel ──
    # (VPC-dependent and standalone can all go at the same time —
    #  they don't depend on each other, only VPC stack must wait)
    echo ""
    print_dim "Phase 1: All non-VPC stacks (parallel)"
    echo ""

    delete_stacks_parallel "$region" \
        "${PREFIX_NC}-securitygroup" \
        "${PREFIX_NC}-nacl" \
        "${PREFIX_NC}-lambda" \
        "${PREFIX_NC}-logmetrics" \
        "${PREFIX_NC}-apigateway" \
        "${PREFIX_NC}-computeopt" \
        "${PREFIX_NC}-ecr" \
        "${PREFIX_NC}-dynamodb" \
        "${PREFIX_NC}-sqs" \
        "${PREFIX_NC}-budgets" \
        "${PREFIX_NC}-cloudwatch" \
        "${PREFIX_NC}-s3" \
        "${PREFIX_NC}-kms" \
        "${PREFIX_COMP}-securitygroup" \
        "${PREFIX_COMP}-nacl" \
        "${PREFIX_COMP}-lambda" \
        "${PREFIX_COMP}-apigateway" \
        "${PREFIX_COMP}-costopt" \
        "${PREFIX_COMP}-sns" \
        "${PREFIX_COMP}-sqs" \
        "${PREFIX_COMP}-anomaly" \
        "${PREFIX_COMP}-budgets" \
        "${PREFIX_COMP}-cloudwatch" \
        "${PREFIX_COMP}-s3" \
        "${PREFIX_COMP}-kms" \
        "${PREFIX_COMP}-subnet"

    # ── Phase 2: VPC stacks last ──
    # Wait for Phase 1 to fully complete before attempting VPC deletion
    # (CloudFormation won't delete a stack while its exports are still in use)
    echo ""
    print_dim "Phase 2: VPC stacks (deleted last — exports must clear first)"
    echo ""
    sleep 5

    delete_stacks_parallel "$region" \
        "${PREFIX_NC}-vpc" \
        "${PREFIX_COMP}-vpcsg" \
        "${PREFIX_MIX}-vpc"

    # Retry any VPC stacks that failed (export dependency race condition)
    local vpc_retry=("${PREFIX_NC}-vpc" "${PREFIX_COMP}-vpcsg" "${PREFIX_MIX}-vpc")
    local needs_retry=false
    for stack in "${vpc_retry[@]}"; do
        local st
        st=$(aws cloudformation describe-stacks \
            --stack-name "$stack" --region "$region" \
            --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")
        if [[ "$st" == "DELETE_FAILED" ]]; then
            needs_retry=true
            break
        fi
    done

    if [[ "$needs_retry" == true ]]; then
        echo ""
        print_warn "Some VPC stacks failed to delete (export dependency). Retrying ..."
        sleep 10
        delete_stacks_parallel "$region" \
            "${PREFIX_NC}-vpc" \
            "${PREFIX_COMP}-vpcsg" \
            "${PREFIX_MIX}-vpc"
    fi

    echo ""
    print_success "Cleanup complete for ${region}."
}

# ─── Deploy a single stack ────────────────────────────────────────────────────

# Deploy a single stack sequentially (create + wait)
deploy_stack() {
    local stack_name="$1"
    local template="$2"
    local region="$3"

    local file_name
    file_name=$(basename "$template" .yml)

    # Check if stack already exists and clean it up first
    local existing_status
    existing_status=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" --region "$region" \
        --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")

    if [[ "$existing_status" != "NOT_FOUND" && "$existing_status" != "DELETE_COMPLETE" ]]; then
        echo -ne "  Found existing ${BOLD}${stack_name}${NC_CLR} (${existing_status}), deleting first ... "
        prepare_stack_for_deletion "$stack_name" "$region"
        aws cloudformation delete-stack --stack-name "$stack_name" --region "$region" > /dev/null 2>&1 || true
        aws cloudformation wait stack-delete-complete --stack-name "$stack_name" --region "$region" 2>/dev/null || true

        # Verify truly gone
        local post_status
        post_status=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" --region "$region" \
            --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")

        if [[ "$post_status" == "DELETE_FAILED" ]]; then
            force_delete_failed "$stack_name" "$region"
        fi

        local attempts=0
        while true; do
            local check
            check=$(aws cloudformation describe-stacks \
                --stack-name "$stack_name" --region "$region" \
                --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")
            [[ "$check" == "NOT_FOUND" || "$check" == "DELETE_COMPLETE" ]] && break
            (( attempts++ ))
            if (( attempts >= 12 )); then
                echo -e "${RED}${CROSS} stack still exists after cleanup (${check})${NC_CLR}"
                return 1
            fi
            sleep 5
        done
        echo -e "${GREEN}cleared${NC_CLR}"
    fi

    echo -ne "  Deploying ${BOLD}${file_name}${NC_CLR} as ${DIM}${stack_name}${NC_CLR} ... "

    if aws cloudformation create-stack \
        --stack-name "$stack_name" \
        --template-body "file://${template}" \
        --region "$region" \
        --capabilities CAPABILITY_NAMED_IAM CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
        --on-failure DO_NOTHING > /dev/null 2>&1; then
        echo -e "${YELLOW}waiting${NC_CLR}"
    else
        echo -e "${RED}${CROSS} failed to create${NC_CLR}"
        return 1
    fi

    if aws cloudformation wait stack-create-complete \
        --stack-name "$stack_name" --region "$region" 2>/dev/null; then
        print_success "${file_name} deployed"
    else
        print_error "${file_name} failed — check AWS Console for details"
        return 1
    fi
}

# Kick off a stack creation without waiting (for parallel deployment)
launch_stack() {
    local stack_name="$1"
    local template="$2"
    local region="$3"

    local file_name
    file_name=$(basename "$template" .yml)

    # Check if stack already exists in any state and clean it up first
    local existing_status
    existing_status=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" --region "$region" \
        --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")

    if [[ "$existing_status" != "NOT_FOUND" && "$existing_status" != "DELETE_COMPLETE" ]]; then
        echo -ne "  Found existing ${BOLD}${stack_name}${NC_CLR} (${existing_status}), deleting first ... "
        prepare_stack_for_deletion "$stack_name" "$region"
        aws cloudformation delete-stack --stack-name "$stack_name" --region "$region" > /dev/null 2>&1 || true
        aws cloudformation wait stack-delete-complete --stack-name "$stack_name" --region "$region" 2>/dev/null || true

        # Verify it's actually gone — retry delete if stuck in DELETE_FAILED
        local post_status
        post_status=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" --region "$region" \
            --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")

        if [[ "$post_status" == "DELETE_FAILED" ]]; then
            force_delete_failed "$stack_name" "$region"
        fi

        # Poll until truly gone (max 60s extra)
        local attempts=0
        while true; do
            local check
            check=$(aws cloudformation describe-stacks \
                --stack-name "$stack_name" --region "$region" \
                --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")
            [[ "$check" == "NOT_FOUND" || "$check" == "DELETE_COMPLETE" ]] && break
            (( attempts++ ))
            if (( attempts >= 12 )); then
                echo -e "${RED}${CROSS} stack still exists after cleanup (${check})${NC_CLR}"
                return 1
            fi
            sleep 5
        done
        echo -e "${GREEN}cleared${NC_CLR}"
    fi

    if aws cloudformation create-stack \
        --stack-name "$stack_name" \
        --template-body "file://${template}" \
        --region "$region" \
        --capabilities CAPABILITY_NAMED_IAM CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
        --on-failure DO_NOTHING > /dev/null 2>&1; then
        echo -e "${GREEN}initiated${NC_CLR}"
        return 0
    else
        local err
        err=$(aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body "file://${template}" \
            --region "$region" \
            --capabilities CAPABILITY_NAMED_IAM CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
            --on-failure DO_NOTHING 2>&1 || true)
        echo -e "${RED}${CROSS} failed: ${err}${NC_CLR}"
        return 1
    fi
}

# Wait for a list of stacks to finish creating
wait_for_stacks() {
    local region="$1"
    shift
    local stacks=("$@")

    local failed=0
    for stack_name in "${stacks[@]}"; do
        # Check if stack exists first
        local status
        status=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" --region "$region" \
            --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")

        [[ "$status" == "NOT_FOUND" ]] && continue

        # Already done?
        if [[ "$status" == "CREATE_COMPLETE" ]]; then
            print_success "$(basename_from_stack "$stack_name") ready"
            continue
        fi

        echo -ne "  Waiting for ${BOLD}${stack_name}${NC_CLR} ... "
        if aws cloudformation wait stack-create-complete \
            --stack-name "$stack_name" --region "$region" 2>/dev/null; then
            echo -e "${GREEN}${TICK} done${NC_CLR}"
        else
            echo -e "${RED}${CROSS} failed${NC_CLR}"
            failed=$((failed + 1))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        print_warn "${failed} stack(s) failed. Check AWS Console for details."
    fi
}

basename_from_stack() {
    echo "$1" | sed 's/^wafr-[a-z]*-//'
}


# ─── Deploy: Compliant ────────────────────────────────────────────────────────

deploy_compliant() {
    local region="$1"
    local launched=()

    print_header "Deploying Compliant Stacks to ${region}"

    # ── Phase 1: VPC (must complete before VPC-dependent stacks) ──
    print_dim "Phase 1: VPC (sequential — prerequisite)"
    echo ""
    deploy_stack "${PREFIX_COMP}-vpcsg"        "${COMP_DIR}/VPCSGCompliant.yml"            "$region" || true

    # ── Phase 2: All independent stacks in parallel ──
    echo ""
    print_dim "Phase 2: Independent stacks (parallel)"
    echo ""
    launched=()
    launch_stack "${PREFIX_COMP}-subnet"       "${COMP_DIR}/SubnetCompliant.yml"            "$region" && launched+=("${PREFIX_COMP}-subnet")
    launch_stack "${PREFIX_COMP}-kms"          "${COMP_DIR}/KMSCMKCompliant.yml"            "$region" && launched+=("${PREFIX_COMP}-kms")
    launch_stack "${PREFIX_COMP}-s3"           "${COMP_DIR}/S3Compliant.yml"                "$region" && launched+=("${PREFIX_COMP}-s3")
    launch_stack "${PREFIX_COMP}-cloudwatch"   "${COMP_DIR}/CloudWatchCompliant.yml"        "$region" && launched+=("${PREFIX_COMP}-cloudwatch")
    launch_stack "${PREFIX_COMP}-budgets"      "${COMP_DIR}/BudgetsCompliant.yml"           "$region" && launched+=("${PREFIX_COMP}-budgets")
    launch_stack "${PREFIX_COMP}-anomaly"      "${COMP_DIR}/AnomalyDetectionCompliant.yml"  "$region" && launched+=("${PREFIX_COMP}-anomaly")
    launch_stack "${PREFIX_COMP}-sqs"          "${COMP_DIR}/SQSCompliant.yml"               "$region" && launched+=("${PREFIX_COMP}-sqs")
    launch_stack "${PREFIX_COMP}-sns"          "${COMP_DIR}/SNS-Complaint.yml"              "$region" && launched+=("${PREFIX_COMP}-sns")
    launch_stack "${PREFIX_COMP}-costopt"      "${COMP_DIR}/CostOptimizerHubCompliant.yml"  "$region" && launched+=("${PREFIX_COMP}-costopt")
    launch_stack "${PREFIX_COMP}-apigateway"   "${COMP_DIR}/ApiGatewayCompliant.yml"        "$region" && launched+=("${PREFIX_COMP}-apigateway")

    echo ""
    print_dim "Waiting for Phase 2 to complete ..."
    wait_for_stacks "$region" "${launched[@]}"

    # ── Phase 3: VPC-dependent stacks in parallel ──
    echo ""
    print_dim "Phase 3: VPC-dependent stacks (parallel)"
    echo ""
    launched=()
    launch_stack "${PREFIX_COMP}-lambda"       "${COMP_DIR}/LambdaCompliant.yml"            "$region" && launched+=("${PREFIX_COMP}-lambda")
    launch_stack "${PREFIX_COMP}-nacl"         "${COMP_DIR}/NACLCompliant.yml"              "$region" && launched+=("${PREFIX_COMP}-nacl")
    launch_stack "${PREFIX_COMP}-securitygroup" "${COMP_DIR}/SecurityGroupCompliant.yml"    "$region" && launched+=("${PREFIX_COMP}-securitygroup")

    echo ""
    print_dim "Waiting for Phase 3 to complete ..."
    wait_for_stacks "$region" "${launched[@]}"

    echo ""
    print_success "Compliant deployment complete."
}

# ─── Deploy: Non-Compliant ────────────────────────────────────────────────────

deploy_noncompliant() {
    local region="$1"
    local launched=()

    print_header "Deploying Non-Compliant Stacks to ${region}"

    # ── Phase 1: VPC (must complete first) ──
    print_dim "Phase 1: VPC (sequential — prerequisite)"
    echo ""
    deploy_stack "${PREFIX_NC}-vpc"            "${NONCOMP_DIR}/VPCNonCompliant.yml"         "$region" || true

    # ── Phase 2: All independent stacks in parallel ──
    echo ""
    print_dim "Phase 2: Independent stacks (parallel)"
    echo ""
    launched=()
    launch_stack "${PREFIX_NC}-kms"            "${NONCOMP_DIR}/KMSCMKNonCompliant.yml"      "$region" && launched+=("${PREFIX_NC}-kms")
    launch_stack "${PREFIX_NC}-s3"             "${NONCOMP_DIR}/S3NonCompliant.yml"           "$region" && launched+=("${PREFIX_NC}-s3")
    launch_stack "${PREFIX_NC}-cloudwatch"     "${NONCOMP_DIR}/CloudWatchNonComplaint.yml"   "$region" && launched+=("${PREFIX_NC}-cloudwatch")
    launch_stack "${PREFIX_NC}-budgets"        "${NONCOMP_DIR}/BudgetsNonCompliant.yml"     "$region" && launched+=("${PREFIX_NC}-budgets")
    launch_stack "${PREFIX_NC}-sqs"            "${NONCOMP_DIR}/SQSNonCompliant.yml"         "$region" && launched+=("${PREFIX_NC}-sqs")
    launch_stack "${PREFIX_NC}-dynamodb"       "${NONCOMP_DIR}/DynamoDBNonCompliant.yml"    "$region" && launched+=("${PREFIX_NC}-dynamodb")
    launch_stack "${PREFIX_NC}-ecr"            "${NONCOMP_DIR}/ECRNonCompliant.yml"         "$region" && launched+=("${PREFIX_NC}-ecr")
    launch_stack "${PREFIX_NC}-computeopt"     "${NONCOMP_DIR}/ComputeOptimizerNonComplaint.yml" "$region" && launched+=("${PREFIX_NC}-computeopt")
    launch_stack "${PREFIX_NC}-apigateway"     "${NONCOMP_DIR}/ApiGatewayNonCompliant.yml"  "$region" && launched+=("${PREFIX_NC}-apigateway")
    launch_stack "${PREFIX_NC}-logmetrics"     "${NONCOMP_DIR}/LogMetricsNonCompliant.yml"  "$region" && launched+=("${PREFIX_NC}-logmetrics")
    launch_stack "${PREFIX_NC}-lambda"         "${NONCOMP_DIR}/LambdaNonCompliant.yml"      "$region" && launched+=("${PREFIX_NC}-lambda")

    echo ""
    print_dim "Waiting for Phase 2 to complete ..."
    wait_for_stacks "$region" "${launched[@]}"

    # ── Phase 3: VPC-dependent stacks in parallel ──
    echo ""
    print_dim "Phase 3: VPC-dependent stacks (parallel)"
    echo ""
    launched=()
    launch_stack "${PREFIX_NC}-nacl"           "${NONCOMP_DIR}/NACLNonCompliant.yml"        "$region" && launched+=("${PREFIX_NC}-nacl")
    launch_stack "${PREFIX_NC}-securitygroup"  "${NONCOMP_DIR}/SecurityGroupNonCompliant.yml" "$region" && launched+=("${PREFIX_NC}-securitygroup")

    echo ""
    print_dim "Waiting for Phase 3 to complete ..."
    wait_for_stacks "$region" "${launched[@]}"

    echo ""
    print_success "Non-Compliant deployment complete."
}


# ─── Deploy: Combined (Compliant + Non-Compliant in same region) ──────────────

deploy_combined() {
    local region="$1"

    print_header "Deploying Combined Stacks to ${region}"
    print_dim "Compliant + Non-Compliant resources in the same region."
    echo ""

    # ── Phase 1: VPC ──
    print_dim "Phase 1: VPC (Compliant version — includes flow logs, NAT GW, DNS logging)"
    echo ""
    deploy_stack "${PREFIX_MIX}-vpc"           "${COMP_DIR}/VPCSGCompliant.yml"            "$region" || true

    # ── Phase 2: All stacks in parallel ──
    print_header "Deploying All Stacks (parallel)"
    print_dim "Conflicting resources auto-resolved:"
    print_dim "  API Gateway            -> Compliant version"
    print_dim "  Cost Optimization Hub  -> Compliant (enabled)"
    print_dim "  Compute Optimizer      -> Skipped (account-global, would disable it)"
    print_dim "  VPC                    -> Skipped (Non-Compliant VPC, export collision)"
    echo ""

    local launched=()

    # Compliant stacks
    launch_stack "${PREFIX_COMP}-subnet"       "${COMP_DIR}/SubnetCompliant.yml"            "$region" && launched+=("${PREFIX_COMP}-subnet")
    launch_stack "${PREFIX_COMP}-kms"          "${COMP_DIR}/KMSCMKCompliant.yml"            "$region" && launched+=("${PREFIX_COMP}-kms")
    launch_stack "${PREFIX_COMP}-s3"           "${COMP_DIR}/S3Compliant.yml"                "$region" && launched+=("${PREFIX_COMP}-s3")
    launch_stack "${PREFIX_COMP}-cloudwatch"   "${COMP_DIR}/CloudWatchCompliant.yml"        "$region" && launched+=("${PREFIX_COMP}-cloudwatch")
    launch_stack "${PREFIX_COMP}-budgets"      "${COMP_DIR}/BudgetsCompliant.yml"           "$region" && launched+=("${PREFIX_COMP}-budgets")
    launch_stack "${PREFIX_COMP}-anomaly"      "${COMP_DIR}/AnomalyDetectionCompliant.yml"  "$region" && launched+=("${PREFIX_COMP}-anomaly")
    launch_stack "${PREFIX_COMP}-sqs"          "${COMP_DIR}/SQSCompliant.yml"               "$region" && launched+=("${PREFIX_COMP}-sqs")
    launch_stack "${PREFIX_COMP}-sns"          "${COMP_DIR}/SNS-Complaint.yml"              "$region" && launched+=("${PREFIX_COMP}-sns")
    launch_stack "${PREFIX_COMP}-apigateway"   "${COMP_DIR}/ApiGatewayCompliant.yml"        "$region" && launched+=("${PREFIX_COMP}-apigateway")
    launch_stack "${PREFIX_COMP}-costopt"      "${COMP_DIR}/CostOptimizerHubCompliant.yml"  "$region" && launched+=("${PREFIX_COMP}-costopt")

    # Non-Compliant stacks
    launch_stack "${PREFIX_NC}-kms"            "${NONCOMP_DIR}/KMSCMKNonCompliant.yml"      "$region" && launched+=("${PREFIX_NC}-kms")
    launch_stack "${PREFIX_NC}-s3"             "${NONCOMP_DIR}/S3NonCompliant.yml"           "$region" && launched+=("${PREFIX_NC}-s3")
    launch_stack "${PREFIX_NC}-cloudwatch"     "${NONCOMP_DIR}/CloudWatchNonComplaint.yml"   "$region" && launched+=("${PREFIX_NC}-cloudwatch")
    launch_stack "${PREFIX_NC}-budgets"        "${NONCOMP_DIR}/BudgetsNonCompliant.yml"     "$region" && launched+=("${PREFIX_NC}-budgets")
    launch_stack "${PREFIX_NC}-sqs"            "${NONCOMP_DIR}/SQSNonCompliant.yml"         "$region" && launched+=("${PREFIX_NC}-sqs")
    launch_stack "${PREFIX_NC}-dynamodb"       "${NONCOMP_DIR}/DynamoDBNonCompliant.yml"    "$region" && launched+=("${PREFIX_NC}-dynamodb")
    launch_stack "${PREFIX_NC}-ecr"            "${NONCOMP_DIR}/ECRNonCompliant.yml"         "$region" && launched+=("${PREFIX_NC}-ecr")
    launch_stack "${PREFIX_NC}-logmetrics"     "${NONCOMP_DIR}/LogMetricsNonCompliant.yml"  "$region" && launched+=("${PREFIX_NC}-logmetrics")
    launch_stack "${PREFIX_NC}-lambda"         "${NONCOMP_DIR}/LambdaNonCompliant.yml"      "$region" && launched+=("${PREFIX_NC}-lambda")
    launch_stack "${PREFIX_NC}-apigateway"     "${NONCOMP_DIR}/ApiGatewayNonCompliant.yml"  "$region" && launched+=("${PREFIX_NC}-apigateway")

    echo ""
    print_dim "Waiting for Phase 2 to complete ..."
    wait_for_stacks "$region" "${launched[@]}"

    # ── Phase 3: VPC-dependent from both folders (parallel) ──
    echo ""
    print_dim "Phase 3: VPC-dependent stacks (parallel)"
    echo ""
    launched=()
    launch_stack "${PREFIX_COMP}-lambda"       "${COMP_DIR}/LambdaCompliant.yml"            "$region" && launched+=("${PREFIX_COMP}-lambda")
    launch_stack "${PREFIX_COMP}-nacl"         "${COMP_DIR}/NACLCompliant.yml"              "$region" && launched+=("${PREFIX_COMP}-nacl")
    launch_stack "${PREFIX_COMP}-securitygroup" "${COMP_DIR}/SecurityGroupCompliant.yml"    "$region" && launched+=("${PREFIX_COMP}-securitygroup")
    launch_stack "${PREFIX_NC}-nacl"           "${NONCOMP_DIR}/NACLNonCompliant.yml"        "$region" && launched+=("${PREFIX_NC}-nacl")
    launch_stack "${PREFIX_NC}-securitygroup"  "${NONCOMP_DIR}/SecurityGroupNonCompliant.yml" "$region" && launched+=("${PREFIX_NC}-securitygroup")

    echo ""
    print_dim "Waiting for Phase 3 to complete ..."
    wait_for_stacks "$region" "${launched[@]}"

    echo ""
    print_success "Combined deployment complete."
}


# ─── Pre-flight ───────────────────────────────────────────────────────────────

preflight() {
    print_header "Pre-flight Checks"

    if command -v aws &> /dev/null; then
        print_success "AWS CLI installed"
    else
        print_error "AWS CLI not found. Install: https://aws.amazon.com/cli/"
        exit 1
    fi

    local identity
    if identity=$(aws sts get-caller-identity --output json 2>/dev/null); then
        local acct arn
        acct=$(echo "$identity" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])")
        arn=$(echo "$identity" | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'])")
        print_success "Credentials valid — Account: ${acct}"
        print_dim "${arn}"
    else
        print_error "AWS credentials not configured or expired."
        exit 1
    fi

    if command -v python3 &> /dev/null; then
        print_success "Python3 available"
    else
        print_error "Python3 required for S3 cleanup operations."
        exit 1
    fi

    [[ -d "$COMP_DIR" ]]    || { print_error "Missing: ${COMP_DIR}"; exit 1; }
    [[ -d "$NONCOMP_DIR" ]] || { print_error "Missing: ${NONCOMP_DIR}"; exit 1; }

    local cc nc_count
    cc=$(ls -1 "$COMP_DIR"/*.yml 2>/dev/null | wc -l | tr -d ' ')
    nc_count=$(ls -1 "$NONCOMP_DIR"/*.yml 2>/dev/null | wc -l | tr -d ' ')
    print_success "Templates found — Compliant: ${cc}, Non-Compliant: ${nc_count}"
    echo ""
}

# ─── Main Menu ────────────────────────────────────────────────────────────────

main() {
    print_banner
    preflight

    echo -e "  ${BOLD}What would you like to do?${NC_CLR}"
    echo ""
    echo -e "    ${GREEN}${BOLD}DEPLOY${NC_CLR}"
    echo -e "    ${BOLD}1)${NC_CLR}  Deploy Compliant stacks"
    echo -e "    ${BOLD}2)${NC_CLR}  Deploy Non-Compliant stacks"
    echo -e "    ${BOLD}3)${NC_CLR}  Deploy Compliant + Non-Compliant combined"
    echo ""
    echo -e "    ${RED}${BOLD}CLEANUP${NC_CLR}"
    echo -e "    ${BOLD}4)${NC_CLR}  Cleanup WAFR stacks (one or more regions)"
    echo ""
    echo -e "    ${BOLD}0)${NC_CLR}  Exit"
    echo ""

    local choice
    while true; do
        echo -ne "  ${CYAN}Enter choice [0-4]: ${NC_CLR}"
        read -r choice
        case "$choice" in [0-4]) break ;; *) print_error "Enter 0-4" ;; esac
    done

    case "$choice" in
        0)
            print_info "Bye."
            exit 0
            ;;
        1)
            select_region "Compliant deployment"
            echo ""
            print_dim "Will deploy 14 Compliant stacks to ${SELECTED_REGION}"
            print_dim "VPC first, then independent stacks, then VPC-dependent."
            echo ""
            check_and_handle_existing "$SELECTED_REGION" || exit 1
            deploy_compliant "$SELECTED_REGION"
            ;;
        2)
            select_region "Non-Compliant deployment"
            echo ""
            print_dim "Will deploy 14 Non-Compliant stacks to ${SELECTED_REGION}"
            print_dim "VPC first, then independent stacks, then VPC-dependent."
            echo ""
            check_and_handle_existing "$SELECTED_REGION" || exit 1
            deploy_noncompliant "$SELECTED_REGION"
            ;;
        3)
            select_region "Combined deployment"
            echo ""
            print_dim "Will deploy Compliant + Non-Compliant stacks to ${SELECTED_REGION}"
            echo ""
            check_and_handle_existing "$SELECTED_REGION" || exit 1
            deploy_combined "$SELECTED_REGION"
            ;;
        4)
            select_cleanup_regions

            # Scan all selected regions and show what will be deleted
            echo ""
            local total_found=0
            for region in "${CLEANUP_REGIONS[@]}"; do
                local stacks_in_region
                stacks_in_region=$(discover_wafr_stacks "$region")
                if [[ -n "$stacks_in_region" ]]; then
                    echo ""
                    print_info "Region ${BOLD}${region}${NC_CLR}:"
                    for s in $stacks_in_region; do
                        print_dim "    ${s}"
                        total_found=$((total_found + 1))
                    done
                else
                    print_dim "Region ${region}: no WAFR stacks found"
                fi
            done

            if [[ "$total_found" -eq 0 ]]; then
                echo ""
                print_success "No WAFR stacks found in any selected region. Nothing to do."
            else
                echo ""
                print_warn "${total_found} WAFR stack(s) will be deleted across ${#CLEANUP_REGIONS[@]} region(s)."
                print_warn "S3 buckets will be emptied. CloudTrails will be stopped."
                print_warn "Only stacks prefixed wafr-comp-, wafr-nc-, wafr-mix- are touched."
                print_warn "No other stacks in your account will be affected."

                if confirm "Delete all of the above? This cannot be undone."; then
                    for region in "${CLEANUP_REGIONS[@]}"; do
                        run_cleanup "$region"
                    done
                else
                    print_info "Cleanup cancelled."
                fi
            fi
            ;;
    esac

    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC_CLR}"
    echo -e "${CYAN}  Done. Run this script again for more operations.${NC_CLR}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC_CLR}"
    echo ""
}

main "$@"
