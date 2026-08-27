#!/usr/bin/env python3
"""
AWS Security Agent — local CLI
Uses Strands Agents SDK + Amazon Bedrock + AWS API MCP Server (stdio).

The AWS API MCP Server (awslabs.aws-api-mcp-server) handles all AWS interactions.
It runs as a local subprocess via uvx — no Lambda, no web hosting needed.

Modes:
  - Default (scan/report): READ_OPERATIONS_ONLY=true  → safe, no writes possible
  - Fix mode:              READ_OPERATIONS_ONLY=false → writes allowed

Shortcuts at the prompt:
    scan    — security scan across 5 areas (read-only)
    fix     — remediate findings (confirms before each change)
    report  — markdown security report (read-only)
    quit    — exit

Prerequisites:
    pip install strands-agents mcp
    pip install uv   (or: brew install uv)
    aws configure    (or export AWS_PROFILE=...)
"""

import asyncio
import os
import sys
import time

from mcp import StdioServerParameters, stdio_client
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient

console = Console(highlight=False)

# ── Config ────────────────────────────────────────────────────────────────────
REGION   = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-sonnet-4-6",  # latest active cross-region inference profile
)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an AWS security agent. You have access to AWS API tools
provided by the AWS API MCP Server (call_aws and suggest_aws_commands).

SCOPE: You only perform security-related tasks. If the user asks you to do
anything unrelated to security (e.g., deploy code, manage costs, create
infrastructure), politely decline and explain you are scoped to security only.

SECURITY CHECKS — when asked to scan, cover all five areas:

  1. S3 public buckets
     - aws s3api list-buckets
     - aws s3api get-bucket-location --bucket <name>
     - aws s3api get-public-access-block --bucket <name>
     - aws s3api get-bucket-acl --bucket <name>
     - Flag: BlockPublicAcls or BlockPublicPolicy is false, or AllUsers/AuthenticatedUsers in ACL

  2. Public EBS snapshots
     - aws ec2 describe-snapshots --owner-ids self
     - aws ec2 describe-snapshot-attribute --snapshot-id <id> --attribute createVolumePermission
     - Flag: Group="all" in createVolumePermission

  3. GuardDuty coverage
     - aws ec2 describe-regions --all-regions
     - aws guardduty list-detectors  (run per region using --region flag)
     - Flag: any region with no active detector

  4. Open SSH / RDP security groups
     - aws ec2 describe-security-groups
     - Flag: inbound rule with port 22 or 3389 and CIDR 0.0.0.0/0 or ::/0

  5. Security Hub & Amazon Detective
     a) Security Hub
        - aws securityhub describe-hub --region <region>
        - Run in us-east-1 and any other regions the user has resources in
        - Flag: SecurityHub not enabled (HubArn missing or ResourceNotFoundException)
        - If enabled, also run: aws securityhub get-findings --filters '{"RecordState":[{"Value":"ACTIVE","Comparison":"EQUALS"}],"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}' --max-items 5
        - Report count of CRITICAL active findings if any

     b) Amazon Detective
        - aws detective list-graphs --region <region>
        - Run in us-east-1 and any other regions the user has resources in
        - Flag: Detective not enabled (empty GraphList)
        - If enabled, report the graph ARN and creation time

REMEDIATION RULES:
  - Read-only by default. Never call a write/mutating API unless the user
    explicitly asks you to fix something.
  - Before ANY write operation: clearly state what you will do (resource name,
    exact API call, expected outcome) and wait for the user to say yes/ok/proceed.
  - After any change: verify it worked with a follow-up read call.
  - If a check fails due to permissions, note it and continue with the rest.

OUTPUT FORMAT:
  - Use markdown tables for findings.
  - Columns: ID | Resource | Issue | Severity | Recommended Fix
  - IDs: S3-001, EBS-001, GD-001, SG-001, SH-001, DT-001 (increment for multiples)
  - Severity: CRITICAL / HIGH / MEDIUM / LOW
"""

# ── Prompt shortcuts ──────────────────────────────────────────────────────────
SHORTCUTS = {
    "scan": (
        "Scan my AWS account for security issues across all five areas: "
        "public S3 buckets, public EBS snapshots, GuardDuty coverage gaps, "
        "open SSH/RDP security group rules, and Security Hub + Amazon Detective status. "
        "Show a findings table with ID, resource, issue, severity, and recommended fix."
    ),
    "fix": (
        "Remediate all the security findings you discovered. "
        "For each finding, tell me exactly what AWS API call you will make and on which "
        "resource, then wait for my confirmation before proceeding. "
        "After each fix, verify it worked with a read call."
    ),
    "report": (
        "Produce a final security report in markdown. Include: "
        "executive summary, findings table, what was remediated, "
        "remaining open items, and recommended next steps."
    ),
}


def mcp_server_params(read_only: bool) -> StdioServerParameters:
    """
    Build the MCP server subprocess config.

    read_only=True  → READ_OPERATIONS_ONLY=true  (scan/report — safe)
    read_only=False → READ_OPERATIONS_ONLY=false (fix — writes allowed)
    """
    return StdioServerParameters(
        command="uvx",
        args=["awslabs.aws-api-mcp-server@latest"],
        env={
            **os.environ,                          # inherit AWS_PROFILE, creds, etc.
            "AWS_REGION": REGION,
            "READ_OPERATIONS_ONLY": "true" if read_only else "false",
            "FASTMCP_LOG_LEVEL": "ERROR",          # suppress MCP server noise
        },
    )


def make_agent(mcp_client: MCPClient) -> Agent:
    """Create a Strands agent wired to the MCP client's tools."""
    tools = mcp_client.list_tools_sync()
    if not tools:
        console.print("[red]ERROR:[/red] No tools loaded from MCP server.")
        console.print("       Make sure 'uvx' is installed: [bold]pip install uv[/bold]")
        sys.exit(1)

    console.print(f"  [dim]Loaded {len(tools)} tools from AWS API MCP Server.[/dim]")

    model = BedrockModel(
        model_id=MODEL_ID,
        region_name=REGION,
        streaming=True,
        max_tokens=4096,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        # callback_handler=None — we handle all output ourselves via stream_async
        callback_handler=None,
    )


async def stream_response(agent: Agent, prompt: str) -> None:
    """
    Stream the agent response live to the terminal.

    During tool calls  → show live ⚙ progress lines (so screen isn't blank)
    After all tools    → render the final markdown response with rich
    """
    current_tool: str | None = None
    tool_call_count = 0
    response_text: list[str] = []
    t0 = time.monotonic()

    async for event in agent.stream_async(prompt):

        # ── Live text tokens — buffer them, don't print raw markdown ─────────
        if "data" in event:
            response_text.append(event["data"])

        # ── Tool call starting — show which AWS API Claude is invoking ────────
        elif "current_tool_use" in event:
            tool_name = event["current_tool_use"].get("name", "")
            if tool_name and tool_name != current_tool:
                current_tool = tool_name
                tool_call_count += 1
                console.print(f"  [dim]⚙  {tool_name}[/dim]", highlight=False)

        # ── Final event — render the buffered response as rich markdown ───────
        elif "result" in event:
            elapsed = time.monotonic() - t0
            full_text = "".join(response_text).strip()

            console.print()
            console.rule("[bold cyan]Agent[/bold cyan]", style="cyan")
            if full_text:
                console.print(Markdown(full_text))
            console.rule(
                f"[dim]{tool_call_count} AWS API call{'s' if tool_call_count != 1 else ''}  ·  {elapsed:.1f}s[/dim]",
                style="dim",
            )
            console.print()


def print_banner():
    console.print()
    console.rule("[bold cyan]AWS Security Agent 🔒[/bold cyan]", style="cyan")
    console.print(f"  [dim]Model :[/dim]  [cyan]{MODEL_ID}[/cyan]")
    console.print(f"  [dim]Region:[/dim]  [cyan]{REGION}[/cyan]")
    console.rule(style="cyan")
    console.print("  [dim]Commands:[/dim]  [bold]scan[/bold]  ·  [bold]fix[/bold]  ·  [bold]report[/bold]  ·  [bold]quit[/bold]")
    console.print()


async def repl(agent: Agent) -> None:
    """
    Async REPL loop.
    Uses run_in_executor for blocking input() so the async event loop stays alive.
    """
    loop = asyncio.get_event_loop()

    while True:
        try:
            user_input = await loop.run_in_executor(
                None, lambda: console.input("[bold green]You>[/bold green] ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            return

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Bye.[/dim]")
            return

        prompt = SHORTCUTS.get(user_input.lower(), user_input)

        try:
            await stream_response(agent, prompt)
        except KeyboardInterrupt:
            console.print("\n  [dim](interrupted)[/dim]\n")
        except Exception as exc:
            console.print(f"\n[red]Error:[/red] {exc}\n")


async def run_session(read_only: bool) -> None:
    """
    Open one MCP server subprocess and run the async REPL inside it.
    The MCP server stays alive for the whole session — no cold start per turn.
    """
    console.print("  Starting AWS API MCP Server…")

    mcp_client = MCPClient(lambda: stdio_client(mcp_server_params(read_only)))

    with mcp_client:
        agent = make_agent(mcp_client)
        print()
        await repl(agent)


def main():
    print_banner()
    asyncio.run(run_session(read_only=False))


if __name__ == "__main__":
    main()
