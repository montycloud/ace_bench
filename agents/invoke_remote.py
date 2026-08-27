#!/usr/bin/env python3
"""
invoke_remote.py — Interactive CLI for any deployed AWS Bedrock Agent.

Reads AGENT_URL and AGENT_TOKEN from .env (written by deploy.sh).
Prompts you to select which agent to talk to if multiple are deployed.
Streams responses live with rich terminal rendering.

Usage:
    python3 invoke_remote.py              # interactive agent selection
    python3 invoke_remote.py --env .env.soa   # use a specific agent directly
"""

import argparse
import json
import os
import sys
import time

import requests
from rich.console import Console
from rich.markdown import Markdown

console = Console(highlight=False)

# ── Agent registry ────────────────────────────────────────────────────────────
AGENTS = {
    "s3soa": {
        "name": "S3 Security Optimization Agent (s3soa)",
        "emoji": "🔒",
        "env_file": ".env.s3soa",
        "shortcuts": {
            "scan": (
                "Scan all S3 buckets for security issues: public access settings, "
                "bucket ACLs, missing encryption, absent logging, and bucket policies. "
                "Show a findings table with ID, bucket, issue, severity, and recommended fix."
            ),
            "fix": (
                "Remediate all the S3 security findings you discovered. "
                "For each finding, tell me exactly what API call you will make, "
                "then wait for my confirmation before proceeding."
            ),
            "report": (
                "Produce a final S3 security report in markdown covering all findings, "
                "what was remediated, remaining open items, and next steps."
            ),
        },
    },
    "soa": {
        "name": "Storage Optimization Agent (soa)",
        "emoji": "💾",
        "env_file": ".env.soa",
        "shortcuts": {
            "scan": (
                "Scan my AWS account for storage waste: unattached EBS volumes, "
                "stale snapshots older than 90 days, orphaned AMIs, and idle volumes. "
                "Show a findings table with estimated monthly cost for each item."
            ),
            "fix": (
                "Clean up all the storage waste you found. "
                "For each item, tell me exactly what you will delete and the cost saving, "
                "then wait for my confirmation before proceeding."
            ),
            "report": (
                "Produce a storage optimization report in markdown covering all findings, "
                "total estimated monthly savings, what was cleaned up, and next steps."
            ),
        },
    },
    "eoa": {
        "name": "EC2 Optimization Agent (eoa)",
        "emoji": "⚡",
        "env_file": ".env.eoa",
        "shortcuts": {
            "scan": (
                "Analyze all running EC2 instances over the last 14 days. "
                "Identify underutilized instances (avg CPU < 10%), recommend right-sized "
                "alternatives, and show projected monthly savings per instance."
            ),
            "fix": (
                "Right-size all the underutilized EC2 instances you identified. "
                "For each instance, tell me the exact type change and savings, "
                "then wait for my confirmation before stopping and resizing."
            ),
            "report": (
                "Produce an EC2 optimization report in markdown covering all findings, "
                "total projected monthly savings, what was resized, and next steps."
            ),
        },
    },
    "poa": {
        "name": "Processor Optimization Agent (poa)",
        "emoji": "🔧",
        "env_file": ".env.poa",
        "shortcuts": {
            "scan": (
                "Inventory all running EC2 instances by processor architecture "
                "(Intel x86_64, AMD x86_64, Graviton arm64). "
                "Identify instances eligible for Graviton migration and show projected savings."
            ),
            "fix": (
                "Migrate eligible instances to Graviton. "
                "For each instance, tell me the exact type change (e.g. m5.large → m6g.large) "
                "and savings, then wait for my confirmation before proceeding."
            ),
            "report": (
                "Produce a processor optimization report in markdown covering the current "
                "architecture inventory, migration candidates, projected savings, and next steps."
            ),
        },
    },
}


def load_env(env_file: str) -> tuple[str, str]:
    """Load AGENT_URL and AGENT_TOKEN from an env file."""
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip()
    url   = os.environ.get("AGENT_URL",   "").rstrip("/")
    token = os.environ.get("AGENT_TOKEN", "")
    return url, token


def select_agent() -> tuple[str, dict]:
    """Interactive agent selection menu. Returns (agent_key, agent_config)."""
    console.print()
    console.rule("[bold cyan]AWS Bedrock Agents[/bold cyan]", style="cyan")
    console.print()
    console.print("  Select an agent:")
    console.print()

    keys = list(AGENTS.keys())
    for i, key in enumerate(keys, 1):
        cfg = AGENTS[key]
        env_exists = "✓" if os.path.exists(cfg["env_file"]) else "○"
        console.print(f"  [bold]{i})[/bold] {cfg['emoji']}  {cfg['name']}  [dim]({key})[/dim]  [green]{env_exists}[/green]")

    console.print()
    console.print("  [dim]✓ = deployed (.env file found)   ○ = not yet deployed[/dim]")
    console.print()

    while True:
        try:
            raw = console.input("  Enter number or agent name: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            sys.exit(0)

        if raw.isdigit() and 1 <= int(raw) <= len(keys):
            key = keys[int(raw) - 1]
            return key, AGENTS[key]
        elif raw in AGENTS:
            return raw, AGENTS[raw]
        else:
            console.print(f"  [red]Invalid selection.[/red] Enter 1-{len(keys)} or {'/'.join(keys)}.")


def call_agent_streaming(url: str, token: str, prompt: str, messages: list) -> list:
    """
    POST to /chat → get jobId → poll /result/{jobId} until done.
    Prints live reasoning steps as the agent works. Returns updated messages.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    updated_messages = messages

    # Step 1: Submit job
    try:
        resp = requests.post(
            f"{url}/chat",
            headers=headers,
            json={"prompt": prompt, "messages": messages},
            timeout=(30, 30),
        )
        resp.raise_for_status()
        data = resp.json()
        job_id = data.get("jobId")
        if not job_id:
            console.print(f"\n[red]Error:[/red] {data}\n")
            return messages
    except requests.HTTPError as exc:
        console.print(f"\n[red]HTTP {exc.response.status_code}:[/red] {exc.response.text[:300]}\n")
        return messages
    except requests.RequestException as exc:
        console.print(f"\n[red]Request error:[/red] {exc}\n")
        return messages

    # Step 2: Poll — print steps live as they arrive
    seen_steps: list[str] = []
    t0 = time.monotonic()

    while time.monotonic() - t0 < 600:
        time.sleep(3)
        try:
            resp = requests.get(
                f"{url}/result/{job_id}",
                headers=headers,
                timeout=(10, 10),
            )
            resp.raise_for_status()
            result = resp.json()
            status = result.get("status", "pending")

            # Print new steps as they arrive
            for step in result.get("progress", []):
                if step not in seen_steps:
                    seen_steps.append(step)
                    console.print(f"  [dim]→ {step}[/dim]")

            if status == "pending":
                continue

            if status == "error":
                console.print(f"\n[red]Something went wrong:[/red] {result.get('error')}\n")
                return messages

            if status == "done":
                response_text    = result.get("response", "")
                updated_messages = result.get("messages", messages)
                agent_elapsed    = result.get("elapsed", round(time.monotonic() - t0, 1))

                console.print()
                console.rule("[bold cyan]Agent[/bold cyan]", style="cyan")
                if response_text:
                    console.print(Markdown(response_text))
                console.rule(
                    f"[dim]{len(seen_steps)} step{'s' if len(seen_steps) != 1 else ''}  ·  {agent_elapsed:.1f}s[/dim]",
                    style="dim",
                )
                console.print()
                return updated_messages

        except requests.RequestException:
            pass  # silent retry

    console.print(f"\n[yellow]This is taking longer than expected. Please try again.[/yellow]\n")
    return messages


def prompt_for_credentials(agent_key: str, cfg: dict) -> tuple[str, str]:
    """
    Load URL and token from the .env file written by deploy.sh.
    Only prompt if the file is missing or incomplete.
    """
    url, token = load_env(cfg["env_file"])

    if url and token:
        # Both present — use them silently, no prompt needed
        return url, token

    # File missing or incomplete — ask the user
    console.print()
    if not url:
        console.print(f"  [yellow]No .env file found for {agent_key}.[/yellow]")
        console.print(f"  Run [bold]./deploy.sh --agent {agent_key}[/bold] first, or enter manually:")
        console.print()
        url   = console.input("  [bold]Agent URL[/bold]: ").strip().rstrip("/")
    token = console.input("  [bold]Bearer token[/bold]: ").strip()
    return url, token


def print_agent_banner(agent_key: str, cfg: dict, url: str):
    console.print()
    console.rule(f"[bold cyan]{cfg['emoji']}  {cfg['name']}[/bold cyan]", style="cyan")
    console.print(f"  [dim]Endpoint:[/dim]  [cyan]{url}[/cyan]")
    console.rule(style="cyan")
    console.print("  [dim]Commands:[/dim]  [bold]scan[/bold]  ·  [bold]fix[/bold]  ·  [bold]report[/bold]  ·  [bold]quit[/bold]")
    console.print()


def main():
    parser = argparse.ArgumentParser(description="AWS Bedrock Agent CLI")
    parser.add_argument("--env", default="", help="Path to .env file (e.g. .env.soa). Skips agent selection menu.")
    args = parser.parse_args()

    # If --env passed, infer agent from filename; otherwise show menu
    if args.env:
        url, token = load_env(args.env)
        basename = os.path.basename(args.env).lstrip(".")
        agent_key = basename.replace("env.", "").replace("env", "")
        cfg = AGENTS.get(agent_key, {
            "name": "Agent", "emoji": "🤖", "env_file": args.env,
            "shortcuts": {"scan": "Scan my AWS account.", "fix": "Fix all findings.", "report": "Generate a report."},
        })
        if not url or not token:
            console.print()
            if not url:
                url = console.input("  [bold]Agent URL[/bold]: ").strip().rstrip("/")
            if not token:
                token = console.input("  [bold]Bearer token[/bold]: ").strip()
    else:
        agent_key, cfg = select_agent()
        url, token = prompt_for_credentials(agent_key, cfg)

    if not url or not token:
        console.print(f"\n[red]ERROR:[/red] No URL or token provided.")
        sys.exit(1)

    print_agent_banner(agent_key, cfg, url)
    messages: list = []

    while True:
        try:
            user_input = console.input("[bold green]You>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Bye.[/dim]")
            break

        prompt = cfg["shortcuts"].get(user_input.lower(), user_input)
        messages = call_agent_streaming(url, token, prompt, messages)


if __name__ == "__main__":
    main()
