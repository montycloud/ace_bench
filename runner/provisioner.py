"""
Provisioner — turns a customer's deployed CloudFormation fixtures into a portable
environment manifest.

The benchmark fixtures (benchmark/fixtures/deploy.sh) create the compliant /
non-compliant AWS resources every scenario is evaluated against. Each CFN stack
exports its real resource IDs as CloudFormation *Outputs*. Crucially, the Output
**keys** are template-defined and therefore stable across every AWS account — only
the **values** (physical IDs like ``sg-0abc…``) change per deployment.

This module discovers the deployed WAFR stacks in a customer account and snapshots
their outputs into ``benchmark/env_manifest.json``. Everything downstream
(gold-label resolution, the tool catalog, the agent's resource inventory) reads the
manifest instead of hardcoding account-specific IDs. That is what makes ACE Bench
runnable against *any* AWS account with only credentials + a region.

Usage:
    python -m runner.provisioner --region us-east-1                 # snapshot manifest
    python -m runner.provisioner --region us-east-1 --out custom.json
    python -m runner.provisioner --region us-east-1 --print         # show, don't write

Prerequisite: deploy the fixtures first (benchmark/fixtures/deploy.sh, option 3 for
the combined single-region environment that covers all 40 scenarios).
"""

import os
import json
import argparse
from pathlib import Path

# Stack prefixes used by benchmark/fixtures/deploy.sh — the ONLY stacks we read.
WAFR_PREFIXES = ("wafr-comp", "wafr-nc", "wafr-mix")

MANIFEST_PATH = Path(__file__).parent.parent / "benchmark" / "env_manifest.json"

# Map a stack-name suffix to a coarse AWS service, for the resource inventory the
# agent is shown. Keyed on the "<prefix>-<suffix>" segment produced by deploy.sh.
_SERVICE_BY_SUFFIX = {
    "s3": "S3", "kms": "KMS", "lambda": "Lambda", "securitygroup": "EC2/SecurityGroup",
    "nacl": "EC2/NACL", "vpc": "EC2/VPC", "subnet": "EC2/Subnet", "cloudwatch": "CloudWatch",
    "logmetrics": "CloudWatch/CloudTrail", "budgets": "Budgets", "sns": "SNS", "sqs": "SQS",
    "dynamodb": "DynamoDB", "ecr": "ECR", "apigateway": "APIGateway", "anomaly": "CostExplorer",
    "costopt": "CostOptimizationHub", "computeopt": "ComputeOptimizer", "iam": "IAM",
}


def _boto_session(region: str):
    try:
        import boto3
    except ImportError as e:
        raise RuntimeError("boto3 not installed. Run: pip install -r requirements.txt") from e
    # boto3 reads AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN (or a
    # named profile) from the environment — the only AWS input the customer provides.
    return boto3.Session(region_name=region)


def _is_wafr_stack(name: str) -> bool:
    return any(name.startswith(p) for p in WAFR_PREFIXES)


def _compliance_of(stack_name: str) -> str:
    if stack_name.startswith("wafr-comp"):
        return "compliant"
    if stack_name.startswith("wafr-nc"):
        return "non_compliant"
    return "mixed"


def _service_of(stack_name: str) -> str:
    suffix = stack_name.split("-", 2)[-1] if stack_name.count("-") >= 2 else ""
    return _SERVICE_BY_SUFFIX.get(suffix, suffix or "unknown")


def discover_stacks(region: str) -> list[dict]:
    """Return every deployed WAFR stack with its outputs, via CloudFormation."""
    session = _boto_session(region)
    cfn = session.client("cloudformation")

    stacks = []
    paginator = cfn.get_paginator("describe_stacks")
    for page in paginator.paginate():
        for s in page["Stacks"]:
            name = s["StackName"]
            if not _is_wafr_stack(name):
                continue
            if s["StackStatus"] in ("DELETE_COMPLETE", "DELETE_IN_PROGRESS"):
                continue
            outputs = {o["OutputKey"]: o.get("OutputValue", "") for o in s.get("Outputs", [])}
            stacks.append({
                "stack": name,
                "status": s["StackStatus"],
                "compliance": _compliance_of(name),
                "service": _service_of(name),
                "outputs": outputs,
            })
    return stacks


def build_manifest(region: str) -> dict:
    """Assemble the portable env manifest from live stack outputs."""
    session = _boto_session(region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    stacks = discover_stacks(region)

    # Flat, addressable resource list. `key` is a stable "<stack>:<OutputKey>" handle
    # that gold labels and the tool catalog reference; `id` is the live physical value.
    resources = []
    for st in stacks:
        for out_key, out_val in st["outputs"].items():
            resources.append({
                "key": f"{st['stack']}:{out_key}",
                "output_key": out_key,
                "id": out_val,
                "stack": st["stack"],
                "service": st["service"],
                "compliance": st["compliance"],
            })

    return {
        "schema_version": 1,
        "account_id": account_id,
        "region": region,
        "stack_count": len(stacks),
        "resource_count": len(resources),
        "stacks": [
            {k: st[k] for k in ("stack", "status", "compliance", "service", "outputs")}
            for st in stacks
        ],
        "resources": resources,
    }


def write_manifest(manifest: dict, out: Path = MANIFEST_PATH) -> Path:
    out.write_text(json.dumps(manifest, indent=2))
    return out


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    """Load the manifest, or raise a clear, actionable error if it is missing."""
    if not path.exists():
        raise FileNotFoundError(
            f"No environment manifest at {path}.\n"
            "  1. Deploy fixtures: cd benchmark/fixtures && ./deploy.sh   (option 3)\n"
            "  2. Snapshot:        python -m runner.provisioner --region <your-region>"
        )
    return json.loads(path.read_text())


def main():
    ap = argparse.ArgumentParser(description="Snapshot deployed WAFR fixtures into env_manifest.json")
    ap.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"), help="AWS region the fixtures were deployed to")
    ap.add_argument("--out", default=str(MANIFEST_PATH), help="Manifest output path")
    ap.add_argument("--print", dest="print_only", action="store_true", help="Print manifest without writing")
    args = ap.parse_args()

    print(f"\n  Discovering WAFR fixtures in {args.region} ...")
    manifest = build_manifest(args.region)
    print(f"  Account : {manifest['account_id']}")
    print(f"  Stacks  : {manifest['stack_count']}")
    print(f"  Outputs : {manifest['resource_count']} resources indexed")

    if manifest["stack_count"] == 0:
        print("\n  [!] No wafr-* stacks found. Deploy fixtures first:")
        print("      cd benchmark/fixtures && ./deploy.sh   (option 3 = combined)")
        return

    if args.print_only:
        print(json.dumps(manifest, indent=2))
    else:
        out = write_manifest(manifest, Path(args.out))
        print(f"\n  [saved] {out}")


if __name__ == "__main__":
    main()
