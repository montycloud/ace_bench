"""
The ACE Bench tool catalog — the fixed, read-only set of AWS investigation tools
the harness offers to a ToolLoop agent.

This is the "complete list of tools" the benchmark defines. An agent is judged on
whether it selects the *right* tools (matched against each scenario's gold-label
``expected_tools``) and identifies the *right* resources — not on whether it can
discover an API surface. Every tool here is strictly read-only; the executor
refuses anything else, so a customer's credentials can never mutate their account.

Each entry pairs:
  - a ToolSpec (name + description + JSON input schema) shown to the agent, and
  - an executor that maps the call onto a boto3 read call and returns JSON.

The catalog intentionally covers exactly the services the fixtures create
(S3, KMS, EC2/VPC/SG/NACL, Lambda, CloudWatch/Logs, SQS, SNS, DynamoDB, ECR,
API Gateway, Budgets, Cost Explorer / Optimization Hub).
"""

from __future__ import annotations
import json
from runner.agents.base import ToolSpec

# A safety allowlist: the executor will only ever call boto3 methods named here.
_READONLY_METHODS = {
    "list_buckets", "get_bucket_encryption", "get_bucket_policy_status",
    "get_public_access_block", "list_keys", "get_key_rotation_status",
    "get_key_policy", "describe_key", "describe_security_groups",
    "describe_network_acls", "describe_vpcs", "describe_subnets",
    "describe_flow_logs", "list_functions", "get_function",
    "describe_log_groups", "describe_metric_filters", "describe_alarms",
    "list_queues", "get_queue_attributes", "describe_table", "list_tables",
    "describe_repositories", "get_repository_policy", "get_rest_apis",
    "get_stages", "describe_budgets", "get_rightsizing_recommendation",
    "list_roles", "get_account_password_policy",
}


def _c(session, service):
    return session.client(service)


def _json(obj) -> str:
    # boto3 returns datetimes / bytes — coerce to a JSON-safe string.
    return json.dumps(obj, default=str, indent=2)[:20000]  # cap payloads


# ── tool definitions: name -> (ToolSpec, executor(session, params) -> str) ──────

def _t(name, desc, schema, fn):
    return name, (ToolSpec(name=name, description=desc, input_schema=schema), fn)


_S = {"type": "object", "properties": {}, "required": []}


def _schema(**props):
    return {"type": "object",
            "properties": {k: {"type": v} for k, v in props.items()},
            "required": []}


CATALOG = dict([
    _t("list_s3_buckets", "List all S3 buckets in the account.", _S,
       lambda s, p: _json(_c(s, "s3").list_buckets().get("Buckets", []))),
    _t("get_s3_public_access", "Get the account/bucket public access block for a bucket.",
       _schema(bucket="string"),
       lambda s, p: _json(_c(s, "s3").get_public_access_block(Bucket=p["bucket"]))),
    _t("get_s3_encryption", "Get default encryption configuration for a bucket.",
       _schema(bucket="string"),
       lambda s, p: _json(_c(s, "s3").get_bucket_encryption(Bucket=p["bucket"]))),
    _t("list_kms_keys", "List all KMS keys.", _S,
       lambda s, p: _json(_c(s, "kms").list_keys().get("Keys", []))),
    _t("get_kms_key_rotation", "Check whether automatic rotation is enabled for a KMS key.",
       _schema(key_id="string"),
       lambda s, p: _json(_c(s, "kms").get_key_rotation_status(KeyId=p["key_id"]))),
    _t("get_kms_key_policy", "Get the key policy for a KMS key.",
       _schema(key_id="string"),
       lambda s, p: _json(_c(s, "kms").get_key_policy(KeyId=p["key_id"], PolicyName="default"))),
    _t("describe_security_groups", "Describe EC2 security groups (optionally by ids).",
       _schema(group_ids="array"),
       lambda s, p: _json(_c(s, "ec2").describe_security_groups(
           **({"GroupIds": p["group_ids"]} if p.get("group_ids") else {})).get("SecurityGroups", []))),
    _t("describe_network_acls", "Describe VPC network ACLs and their rules.", _S,
       lambda s, p: _json(_c(s, "ec2").describe_network_acls().get("NetworkAcls", []))),
    _t("describe_vpcs", "Describe VPCs.", _S,
       lambda s, p: _json(_c(s, "ec2").describe_vpcs().get("Vpcs", []))),
    _t("describe_flow_logs", "Describe VPC flow logs (to detect VPCs without flow logging).", _S,
       lambda s, p: _json(_c(s, "ec2").describe_flow_logs().get("FlowLogs", []))),
    _t("list_lambda_functions", "List Lambda functions with config (DLQ, timeout, runtime).", _S,
       lambda s, p: _json(_c(s, "lambda").list_functions().get("Functions", []))),
    _t("get_lambda_function", "Get full configuration for one Lambda function.",
       _schema(function_name="string"),
       lambda s, p: _json(_c(s, "lambda").get_function(FunctionName=p["function_name"]))),
    _t("describe_log_groups", "Describe CloudWatch log groups (retention, KMS).", _S,
       lambda s, p: _json(_c(s, "logs").describe_log_groups().get("logGroups", []))),
    _t("describe_metric_filters", "Describe CloudWatch Logs metric filters (detective controls).", _S,
       lambda s, p: _json(_c(s, "logs").describe_metric_filters().get("metricFilters", []))),
    _t("describe_cloudwatch_alarms", "Describe CloudWatch alarms.", _S,
       lambda s, p: _json(_c(s, "cloudwatch").describe_alarms().get("MetricAlarms", []))),
    _t("list_sqs_queues", "List SQS queues.", _S,
       lambda s, p: _json(_c(s, "sqs").list_queues().get("QueueUrls", []))),
    _t("get_sqs_queue_attributes", "Get attributes for an SQS queue (encryption, DLQ redrive).",
       _schema(queue_url="string"),
       lambda s, p: _json(_c(s, "sqs").get_queue_attributes(QueueUrl=p["queue_url"], AttributeNames=["All"]))),
    _t("describe_dynamodb_table", "Describe a DynamoDB table (PITR, encryption).",
       _schema(table_name="string"),
       lambda s, p: _json(_c(s, "dynamodb").describe_table(TableName=p["table_name"]))),
    _t("describe_ecr_repositories", "Describe ECR repositories (scan-on-push, tag immutability).", _S,
       lambda s, p: _json(_c(s, "ecr").describe_repositories().get("repositories", []))),
    _t("get_ecr_repository_policy", "Get the repository policy for an ECR repo (public access).",
       _schema(repository_name="string"),
       lambda s, p: _json(_c(s, "ecr").get_repository_policy(repositoryName=p["repository_name"]))),
    _t("list_api_gateways", "List API Gateway REST APIs.", _S,
       lambda s, p: _json(_c(s, "apigateway").get_rest_apis().get("items", []))),
    _t("get_api_gateway_stages", "Get stages for a REST API (throttling, cache encryption).",
       _schema(rest_api_id="string"),
       lambda s, p: _json(_c(s, "apigateway").get_stages(restApiId=p["rest_api_id"]).get("item", []))),
    _t("describe_budgets", "Describe AWS Budgets and their notifications.", _S,
       lambda s, p: _json(_c(s, "budgets").describe_budgets(
           AccountId=s.client("sts").get_caller_identity()["Account"]).get("Budgets", []))),
    _t("get_rightsizing_recommendations", "Get Cost Explorer rightsizing recommendations.", _S,
       lambda s, p: _json(_c(s, "ce").get_rightsizing_recommendation(
           Service="AmazonEC2").get("RightsizingRecommendations", []))),
    _t("list_iam_roles", "List IAM roles (to detect wildcard / over-privileged policies).", _S,
       lambda s, p: _json(_c(s, "iam").list_roles().get("Roles", []))),
    _t("get_account_password_policy", "Get the account IAM password policy.", _S,
       lambda s, p: _json(_c(s, "iam").get_account_password_policy().get("PasswordPolicy", {}))),
])


def tool_specs() -> list[ToolSpec]:
    """The public catalog shown to agents."""
    return [spec for spec, _ in CATALOG.values()]


def execute_tool(session, name: str, params: dict) -> str:
    """Execute one catalog tool against AWS. Read-only and allowlisted."""
    if name not in CATALOG:
        return _json({"error": f"unknown tool '{name}'", "available": list(CATALOG)})
    spec, fn = CATALOG[name]
    try:
        return fn(session, params or {})
    except Exception as e:
        # Missing-resource / access errors are expected signal, not crashes.
        return _json({"error": type(e).__name__, "message": str(e)[:500]})
