"""
Bedrock agent adapter for ACE Bench.

Covers 4 domain-specific agents, each backed by an AWS API Gateway + Bedrock Agents setup:
  s3soa  — S3 Security Optimization
  soa    — Storage Optimization
  eoa    — EC2 Optimization
  poa    — Processor Optimization

These agents call real AWS APIs directly (not the WAFR assessment layer).
Because the API does not expose tool call details, the tools pillar score is not applicable.

Usage:
    from runner.agents.bedrock import ask, build_prompt, enrich_gold
    result = ask(prompt, agent_code='s3soa')
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

AGENT_CONFIGS = {
    "s3soa": {
        "name": "S3 Security Optimization",
        "url_env": "BEDROCK_AGENT_URL_S3SOA",
        "token_env": "BEDROCK_AGENT_TOKEN_S3SOA",
    },
    "soa": {
        "name": "Storage Optimization",
        "url_env": "BEDROCK_AGENT_URL_SOA",
        "token_env": "BEDROCK_AGENT_TOKEN_SOA",
    },
    "eoa": {
        "name": "EC2 Optimization",
        "url_env": "BEDROCK_AGENT_URL_EOA",
        "token_env": "BEDROCK_AGENT_TOKEN_EOA",
    },
    "poa": {
        "name": "Processor Optimization",
        "url_env": "BEDROCK_AGENT_URL_POA",
        "token_env": "BEDROCK_AGENT_TOKEN_POA",
    },
}

# Compact single-line output contracts — curly braces break the backend's prompt parser
OUTPUT_CONTRACT_L1 = (
    "Return your answer as JSON with keys: "
    "summary (string), "
    "findings (array — each item has resource_id, resource_type, check, severity, evidence), "
    "improvement_plan (array — each item has resource_id, action, priority, effort). "
    "One object per resource. Output only valid JSON."
)

OUTPUT_CONTRACT_L2 = (
    "Return your answer as JSON with keys: "
    "summary (string), "
    "observations (array — each item has area, finding, evidence, severity), "
    "platform_gaps (array of strings describing what could not be assessed), "
    "plan (array — each item has action, scope, priority, effort, rationale). "
    "Output only valid JSON."
)


def enrich_gold(gold: dict) -> dict:
    """No tool call enrichment for Bedrock agents — tools are not observable."""
    return gold


def build_prompt(scenario: dict, gold: dict) -> str:
    """Build the full prompt to send to the agent for a scenario.

    Uses success_criteria (the concrete "what to check" definition) rather than
    objective_raw. The benchmark objective contains fixture-scoped instructions
    ("capture all must-find items from env:fx/...") that, once the fixture refs
    are stripped, leave an open-ended sweep directive that causes Bedrock agents
    to exhaust their orchestration context (max_tokens). success_criteria is
    specific about what to look for without driving unbounded investigation.
    """
    level = scenario.get("level", 1)
    contract = OUTPUT_CONTRACT_L1 if level == 1 else OUTPUT_CONTRACT_L2
    task = scenario.get("success_criteria", "") or scenario.get("objective_clean", "")
    return f"{task} {contract}"


def ask(
    prompt: str, agent_code: str, messages: list = None, timeout: int = 600
) -> dict:
    """
    Submit a prompt to a Bedrock agent and poll until done.

    Args:
        prompt:     the full prompt to send
        agent_code: one of 's3soa', 'soa', 'eoa', 'poa'
        messages:   optional conversation history for multi-turn
        timeout:    max seconds to wait for completion

    Returns:
        dict with keys:
            response         — final response text
            tool_calls       — always [] (not exposed by API)
            raw_tool_results — always [] (not exposed by API)
            elapsed          — wall-clock seconds from API response
            progress         — list of progress step strings
            messages         — updated conversation history
    """
    cfg = AGENT_CONFIGS[agent_code]
    url = os.getenv(cfg["url_env"], "")
    token = os.getenv(cfg["token_env"], "")
    if not url:
        raise ValueError(
            f"No URL found for {agent_code} — set {cfg['url_env']} in .env"
        )
    if not token:
        raise ValueError(
            f"No token found afor {agent_code} — set {cfg['token_env']} in .env"
        )

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Submit
    r = requests.post(
        f"{url}/chat",
        headers=headers,
        json={"prompt": prompt, "messages": messages or []},
        timeout=30,
    )
    r.raise_for_status()
    job_id = r.json().get("jobId")
    if not job_id:
        raise RuntimeError(f"No jobId in response: {r.text[:200]}")

    # Poll
    seen_steps: list = []
    t0 = time.monotonic()

    while time.monotonic() - t0 < timeout:
        time.sleep(3)
        try:
            poll = requests.get(f"{url}/result/{job_id}", headers=headers, timeout=10)
            if not poll.ok:
                continue
            data = poll.json()
        except Exception:
            continue

        for step in data.get("progress") or []:
            if isinstance(step, str) and step not in seen_steps:
                seen_steps.append(step)
                print(f"  → {step}")

        status = data.get("status", "pending")

        if status == "done":
            return {
                "response": data.get("response", ""),
                "tool_calls": [],
                "raw_tool_results": [],
                "elapsed": data.get("elapsed", round(time.monotonic() - t0, 1)),
                "progress": seen_steps,
                "messages": data.get("messages") or messages or [],
            }

        if status == "error":
            raise RuntimeError(f"Agent error: {data.get('error', 'unknown')}")

        print(f"  [{status}]")

    raise TimeoutError(f"Agent did not respond within {timeout}s")


# ── AgentAdapter wrapper ────────────────────────────────────────────────────────
class BedrockAdapter:
    """Black-box adapter: the Bedrock agents hold their own AWS access and do not
    expose tool calls, so the Tools pillar is not scored."""

    observable_tools = False
    native_tools = False  # trace unobservable; Tools pillar skipped regardless

    def __init__(self, agent_code: str):
        if agent_code not in AGENT_CONFIGS:
            raise ValueError(f"Unknown bedrock agent: {agent_code}")
        self.agent_code = agent_code
        self.name = agent_code

    def build_input(self, scenario: dict, gold: dict, env: dict):
        from runner.agents.base import AgentInput
        prompt = build_prompt(scenario, gold)
        return AgentInput(scenario_id=scenario["csv_id"], task=prompt, output_contract="")

    def run(self, agent_input):
        from runner.agents.base import RunResult
        result = ask(agent_input.task, agent_code=self.agent_code)
        return RunResult(
            response=result.get("response", ""),
            tool_calls=[],
            raw_tool_results=[],
            elapsed=result.get("elapsed"),
        )
