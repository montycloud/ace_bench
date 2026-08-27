"""
S3 Security Optimization Agent (S3SOA) — Lambda handlers

Three Lambda functions in one file:
  dispatcher — POST /chat → stores job, invokes agent async, returns jobId immediately
  agent      — runs Strands agent with remote AWS MCP Server, stores result in DynamoDB  
  poller     — GET /result/{jobId} → reads DynamoDB, returns status + result

DynamoDB TTL = 1 hour. Auth = Bearer token from Secrets Manager.
MCP = Remote AWS MCP Server with SigV4 auth + retry on rate limits.
"""

import asyncio
import hmac
import json
import logging
import os
import time
import uuid

import boto3
import botocore.session
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION         = os.environ.get("AGENT_REGION") or os.environ.get("AWS_REGION", "us-east-1")
_REGION_PREFIX = REGION.split("-")[0]
MODEL_ID       = os.environ.get("BEDROCK_MODEL_ID") or f"{_REGION_PREFIX}.anthropic.claude-sonnet-4-6"
SECRET_ARN     = os.environ["BEARER_TOKEN_SECRET_ARN"]
TABLE_NAME     = os.environ["JOBS_TABLE_NAME"]
AGENT_FUNC     = os.environ["AGENT_FUNCTION_NAME"]
MCP_ENDPOINT   = os.environ.get("MCP_ENDPOINT", "https://aws-mcp.us-east-1.api.aws/mcp")
TTL_SECONDS    = 3600

_sm     = boto3.client("secretsmanager", region_name=REGION)
_ddb    = boto3.client("dynamodb", region_name=REGION)
_lambda = boto3.client("lambda", region_name=REGION)
_token_cache: str | None = None

SYSTEM_PROMPT = """You are an AWS security agent. You have access to AWS API tools
provided by the AWS MCP Server (call_aws, search_documentation, and other tools).

SCOPE: You only perform security-related tasks. Decline anything unrelated to security.

SECURITY CHECKS — when asked to scan, cover all five areas:

  1. S3 public buckets
     - aws s3api list-buckets
     - aws s3api get-public-access-block --bucket <name>
     - aws s3api get-bucket-acl --bucket <name>
     - Flag: BlockPublicAcls or BlockPublicPolicy is false, or AllUsers/AuthenticatedUsers in ACL

  2. Public EBS snapshots
     - aws ec2 describe-snapshots --owner-ids self
     - aws ec2 describe-snapshot-attribute --snapshot-id <id> --attribute createVolumePermission
     - Flag: Group="all" in createVolumePermission

  3. GuardDuty coverage
     - aws ec2 describe-regions --all-regions
     - aws guardduty list-detectors (per region)
     - Flag: any region with no active detector

  4. Open SSH / RDP security groups
     - aws ec2 describe-security-groups
     - Flag: inbound rule with port 22 or 3389 and CIDR 0.0.0.0/0 or ::/0

  5. Security Hub & Amazon Detective
     - aws securityhub describe-hub
     - aws detective list-graphs
     - Flag: not enabled

REMEDIATION RULES:
  - Read-only by default. Never mutate unless explicitly asked.
  - Before ANY write: state exactly what you will do and wait for yes/ok/proceed.
  - After any change: verify with a follow-up read call.

OUTPUT FORMAT:
  - Markdown tables. Columns: ID | Resource | Issue | Severity | Recommended Fix
  - IDs: S3-001, EBS-001, GD-001, SG-001, SH-001, DT-001
  - Severity: CRITICAL / HIGH / MEDIUM / LOW
"""


def _load_token() -> str:
    global _token_cache
    if not _token_cache:
        raw = _sm.get_secret_value(SecretId=SECRET_ARN)["SecretString"]
        _token_cache = json.loads(raw)["token"]
    return _token_cache


def _authorized(event: dict) -> bool:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    auth = headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return False
    try:
        return hmac.compare_digest(auth[7:].encode(), _load_token().encode())
    except Exception:
        logger.exception("Token validation failed")
        return False


class _SigV4Auth(httpx.Auth):
    def auth_flow(self, request):
        creds = botocore.session.get_session().get_credentials().get_frozen_credentials()
        aws_req = AWSRequest(method=request.method, url=str(request.url), data=request.content or b"")
        SigV4Auth(creds, "aws-mcp", REGION).add_auth(aws_req)
        for k, v in aws_req.headers.items():
            request.headers[k] = v
        yield request


def _store_job(job_id: str, status: str, prompt: str, messages: list,
               response: str = "", elapsed: float = 0, error: str = "", progress: list | None = None):
    _ddb.put_item(
        TableName=TABLE_NAME,
        Item={
            "jobId":    {"S": job_id},
            "status":   {"S": status},
            "prompt":   {"S": prompt},
            "response": {"S": response},
            "messages": {"S": json.dumps(messages, default=str)},
            "elapsed":  {"N": str(elapsed)},
            "error":    {"S": error},
            "progress": {"S": json.dumps(progress or [])},
            "ttl":      {"N": str(int(time.time()) + TTL_SECONDS)},
        }
    )


def _read_job(job_id: str) -> dict | None:
    resp = _ddb.get_item(TableName=TABLE_NAME, Key={"jobId": {"S": job_id}})
    item = resp.get("Item")
    if not item:
        return None
    return {
        "jobId":    item["jobId"]["S"],
        "status":   item["status"]["S"],
        "response": item.get("response", {}).get("S", ""),
        "messages": json.loads(item.get("messages", {}).get("S", "[]")),
        "elapsed":  float(item.get("elapsed", {}).get("N", "0")),
        "error":    item.get("error", {}).get("S", ""),
        "progress": json.loads(item.get("progress", {}).get("S", "[]")),
    }


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


async def _run_agent(prompt: str, messages: list, job_id: str) -> tuple[str, list, float]:
    """
    Runs the agent using the remote AWS MCP Server.
    Retries up to 3 times on 429 rate limit or connection errors.
    """
    max_attempts = 3
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        if attempt > 0:
            wait = 20 * attempt
            logger.info("Retry %d after %ds: %s", attempt + 1, wait, str(last_error)[:100])
            await asyncio.sleep(wait)

        try:
            client = MCPClient(
                lambda: streamablehttp_client(
                    MCP_ENDPOINT,
                    auth=_SigV4Auth(),
                    timeout=870.0,
                    sse_read_timeout=870.0,
                )
            )
            with client:
                tools = client.list_tools_sync()
                if not tools:
                    raise RuntimeError("No tools loaded from AWS MCP Server")

                logger.info("Loaded %d MCP tools (attempt %d)", len(tools), attempt + 1)

                agent = Agent(
                    model=BedrockModel(model_id=MODEL_ID, region_name=REGION, streaming=True, max_tokens=4096),
                    system_prompt=SYSTEM_PROMPT,
                    tools=tools,
                    messages=messages,
                    callback_handler=None,
                )

                steps: list[str] = []
                text_parts: list[str] = []
                t0 = time.monotonic()

                async for event in agent.stream_async(prompt):
                    if "data" in event:
                        text_parts.append(event["data"])

                    elif "current_tool_use" in event:
                        tool_use = event["current_tool_use"]
                        tool_name = tool_use.get("name", "")
                        tool_input = tool_use.get("input", {})

                        if isinstance(tool_input, str):
                            try:
                                tool_input = json.loads(tool_input)
                            except Exception:
                                tool_input = {}

                        if tool_name == "aws___call_aws":
                            cmd = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
                            step = f"Calling: {cmd}" if cmd else "Calling AWS API"
                        elif tool_name == "aws___search_documentation":
                            q = tool_input.get("query", "") if isinstance(tool_input, dict) else ""
                            step = f"Searching docs: {q[:60]}" if q else "Searching AWS documentation"
                        elif tool_name == "aws___run_script":
                            step = "Running analysis script"
                        elif tool_name == "aws___suggest_aws_commands":
                            step = "Selecting AWS commands"
                        else:
                            step = tool_name.replace("aws___", "").replace("_", " ").title()

                        if not steps or steps[-1] != step:
                            steps.append(step)
                            try:
                                _ddb.update_item(
                                    TableName=TABLE_NAME,
                                    Key={"jobId": {"S": job_id}},
                                    UpdateExpression="SET progress = :p",
                                    ExpressionAttributeValues={":p": {"S": json.dumps(steps)}},
                                )
                            except Exception:
                                pass

                elapsed = round(time.monotonic() - t0, 1)
                response_text = "".join(text_parts).strip()
                if not response_text:
                    last = agent.messages[-1] if agent.messages else {}
                    if isinstance(last, dict):
                        content = last.get("content", [])
                        if isinstance(content, list) and content:
                            first = content[0]
                            response_text = first.get("text", "") if isinstance(first, dict) else str(first)
                        elif isinstance(content, str):
                            response_text = content
                return response_text, agent.messages, elapsed

        except Exception as e:
            last_error = e
            err_str = str(e)
            if any(x in err_str for x in ["429", "Too Many Requests", "Connection", "closed", "TaskGroup"]):
                logger.warning("Retryable error attempt %d: %s", attempt + 1, err_str[:150])
                continue
            raise

    raise RuntimeError(f"Failed after {max_attempts} attempts: {last_error}")


def dispatcher(event: dict, context):
    if not _authorized(event):
        return _resp(401, {"error": "Unauthorized"})
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _resp(400, {"error": "Invalid JSON body"})
    prompt   = (body.get("prompt") or "").strip()
    messages = body.get("messages") or []
    if not prompt:
        return _resp(400, {"error": "Missing 'prompt'"})
    job_id = str(uuid.uuid4())[:12]
    logger.info("Dispatching job %s", job_id)
    _store_job(job_id, "pending", prompt, messages)
    _lambda.invoke(
        FunctionName=AGENT_FUNC,
        InvocationType="Event",
        Payload=json.dumps({"jobId": job_id, "prompt": prompt, "messages": messages}).encode(),
    )
    return _resp(202, {"jobId": job_id, "status": "pending"})


def agent(event: dict, context):
    job_id   = event["jobId"]
    prompt   = event["prompt"]
    messages = event.get("messages", [])
    logger.info("Agent running job %s", job_id)
    try:
        response_text, updated_messages, elapsed = asyncio.run(
            _run_agent(prompt, messages, job_id)
        )
        _store_job(job_id, "done", prompt, updated_messages, response_text, elapsed)
        logger.info("Job %s done in %.1fs", job_id, elapsed)
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        _store_job(job_id, "error", prompt, messages, error=str(exc))


def poller(event: dict, context):
    if not _authorized(event):
        return _resp(401, {"error": "Unauthorized"})
    job_id = (event.get("pathParameters") or {}).get("jobId", "")
    if not job_id:
        return _resp(400, {"error": "Missing jobId"})
    job = _read_job(job_id)
    if not job:
        return _resp(404, {"error": "Job not found"})
    return _resp(200, job)
