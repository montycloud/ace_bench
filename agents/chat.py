#!/usr/bin/env python3
"""
AWS Bedrock Agents — Chat Client
Works on Windows, Mac, and Linux. No setup needed.

Usage:
    python3 chat.py     (Mac / Linux)
    python chat.py      (Windows)

Requirements: Python 3.8+
Download Python: https://www.python.org/downloads/
  → Windows: tick "Add Python to PATH" during install
"""

# ── Auto-install dependencies ─────────────────────────────────────────────────
import subprocess, sys

def _pip(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    import requests
except ImportError:
    print("Setting up (first run only)…")
    _pip("requests")
    import requests

try:
    from rich.console import Console
    from rich.markdown import Markdown
except ImportError:
    _pip("rich")
    from rich.console import Console
    from rich.markdown import Markdown

import time

# ── Agents — update URLs/tokens here if they change ──────────────────────────
AGENTS = {
    "1": {
        "name":  "S3 Security Optimization",
        "code":  "s3soa",
        "emoji": "🔒",
        "url":   "https://r7a9uuotv0.execute-api.us-east-1.amazonaws.com",
    },
    "2": {
        "name":  "Storage Optimization",
        "code":  "soa",
        "emoji": "💾",
        "url":   "https://7xu2wfcu9e.execute-api.us-east-1.amazonaws.com",
    },
    "3": {
        "name":  "EC2 Optimization",
        "code":  "eoa",
        "emoji": "⚡",
        "url":   "https://uuopi1wnhb.execute-api.us-east-1.amazonaws.com",
    },
    "4": {
        "name":  "Processor Optimization",
        "code":  "poa",
        "emoji": "🔧",
        "url":   "https://6s96jq1q2k.execute-api.us-east-1.amazonaws.com",
    },
}

console = Console(highlight=False)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def ask(url: str, token: str, prompt: str, messages: list) -> list:
    """Submit a prompt, show live steps, return updated conversation."""

    # 1. Submit
    try:
        r = requests.post(
            f"{url}/chat",
            headers=_headers(token),
            json={"prompt": prompt, "messages": messages},
            timeout=30,
        )
    except requests.RequestException as e:
        console.print(f"\n[red]Connection error:[/red] {e}\n")
        return messages

    if r.status_code == 401:
        console.print("\n[red]Unauthorized — check your token.[/red]\n")
        return messages
    if not r.ok:
        console.print(f"\n[red]Error {r.status_code}:[/red] {r.text[:200]}\n")
        return messages

    try:
        job_id = r.json().get("jobId")
    except Exception:
        console.print(f"\n[red]Unexpected response:[/red] {r.text[:200]}\n")
        return messages

    if not job_id:
        console.print(f"\n[red]No job ID returned.[/red] {r.text[:200]}\n")
        return messages

    # 2. Poll — print steps live as they arrive
    seen: list = []
    t0 = time.monotonic()
    first_output = False

    # Simple dots animation using sys.stdout (works on Windows + Mac)
    import threading, sys as _sys
    stop_dots = threading.Event()

    def _dots():
        frames = [".  ", ".. ", "..."]
        i = 0
        while not stop_dots.is_set():
            _sys.stdout.write(f"\r  {frames[i % 3]}")
            _sys.stdout.flush()
            i += 1
            time.sleep(0.5)
        _sys.stdout.write("\r       \r")
        _sys.stdout.flush()

    dots_thread = threading.Thread(target=_dots, daemon=True)
    dots_thread.start()

    while time.monotonic() - t0 < 600:
        time.sleep(3)

        try:
            poll = requests.get(f"{url}/result/{job_id}",
                                headers=_headers(token), timeout=10)
            if not poll.ok:
                continue
            data = poll.json()
            if not isinstance(data, dict):
                continue
        except Exception:
            continue

        # Print new steps as they arrive
        for step in data.get("progress") or []:
            if isinstance(step, str) and step not in seen:
                if not first_output:
                    stop_dots.set()  # kill dots on first real output
                    first_output = True
                seen.append(step)
                console.print(f"  [dim]→ {step}[/dim]")

        status = data.get("status", "pending")

        if status == "done":
            stop_dots.set()
            response = data.get("response", "")
            elapsed  = data.get("elapsed", round(time.monotonic() - t0, 1))
            console.print()
            console.rule("[bold cyan]Agent[/bold cyan]", style="cyan")
            if response:
                console.print(Markdown(str(response)))
            console.rule(
                f"[dim]{len(seen)} step{'s' if len(seen) != 1 else ''}  ·  {elapsed:.1f}s[/dim]",
                style="dim",
            )
            console.print()
            updated = data.get("messages")
            return updated if isinstance(updated, list) else messages

        if status == "error":
            stop_dots.set()
            err = data.get("error") or "Unknown error"
            console.print(f"\n[red]Agent error:[/red] {err}\n")
            return messages

    stop_dots.set()
    console.print("\n[yellow]Timed out. Please try again.[/yellow]\n")
    return messages


def main():
    console.print()
    console.rule("[bold cyan]AWS Bedrock Agents[/bold cyan]", style="cyan")
    console.print()
    console.print("  Select an agent:\n")

    for k, a in AGENTS.items():
        console.print(f"  {k})  {a['emoji']}  {a['name']}  [dim]({a['code']})[/dim]")

    console.print()

    while True:
        choice = console.input("  Enter number [1-4]: ").strip()
        if choice in AGENTS:
            break
        console.print("  [red]Please enter 1, 2, 3, or 4.[/red]")

    agent = AGENTS[choice]
    url   = agent["url"]

    console.print()
    token = console.input("  Bearer token: ").strip()
    if not token:
        console.print("[red]Token is required.[/red]")
        sys.exit(1)

    console.print()
    console.print(f"  [green]✓[/green] Connected to {agent['emoji']}  {agent['name']} ({agent['code']})")
    console.print(f"  [dim]Type [bold]quit[/bold] to exit.[/dim]")
    console.rule(style="cyan")
    console.print()

    messages: list = []

    while True:
        try:
            user_input = console.input("[bold green]You>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q", "bye"):
            console.print("[dim]Bye.[/dim]")
            break

        messages = ask(url, token, user_input, messages)


if __name__ == "__main__":
    main()
