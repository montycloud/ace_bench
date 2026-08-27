"""
ToolLoopAdapter — evaluate a third-party agent that ACE Bench drives through its
own read-only AWS tool catalog.

This is the default agent-agnostic path. The customer provides two things:
  1. AWS credentials (env / profile) — held by the harness, used to execute tools.
  2. An agent endpoint (HTTP)         — the agent under test.

The harness runs a standard tool-use loop:

    ┌─ POST {endpoint} { session_id, messages, tools, resource_inventory }
    │      agent replies with EITHER
    │        { "type": "tool_use",  "tool_calls": [ {id,name,input}, ... ] }
    │        { "type": "final",     "response": "<final answer text>" }
    │  ← harness executes each tool_call against AWS (catalog.execute_tool),
    │    appends { role: "tool", tool_call_id, content } to messages, and re-POSTs
    └─ … until the agent returns "final" or MAX_TURNS is hit.

Because the harness sees every tool call, ``observable_tools = True`` and the
Tools pillar is scored. The wire contract above is intentionally close to the
common LLM tool-calling shape; ``_parse_agent_reply`` is tolerant of minor
variations and is the single place to adapt to a different agent protocol.

Endpoint + auth come from the environment:
    AGENT_ENDPOINT   — URL the harness POSTs to        (required)
    AGENT_AUTH_TOKEN — optional bearer token
"""

from __future__ import annotations
import os
import time
import json
import requests

from runner.agents.base import AgentInput, RunResult, ToolCall
from runner.tools.catalog import tool_specs, execute_tool

MAX_TURNS = 20
HTTP_TIMEOUT = 120


class ToolLoopAdapter:
    name = "toolloop"
    observable_tools = True
    native_tools = True   # score against gold['expected_tools'] (AWS-native)

    def __init__(self, region: str, endpoint: str | None = None, auth_token: str | None = None, session=None):
        self.region = region
        self.endpoint = endpoint or os.getenv("AGENT_ENDPOINT", "")
        self.auth_token = auth_token or os.getenv("AGENT_AUTH_TOKEN", "")
        if not self.endpoint:
            raise ValueError("No agent endpoint. Set AGENT_ENDPOINT in .env or pass endpoint=.")
        # Harness-held session — the ONLY thing that ever touches the customer account.
        # A session may be injected (e.g. a mock for local testing without real AWS).
        if session is not None:
            self._session = session
        else:
            import boto3
            self._session = boto3.Session(region_name=region)

    # ── AgentAdapter contract ────────────────────────────────────────────────
    def build_input(self, scenario: dict, gold: dict, env: dict) -> AgentInput:
        inventory = [
            {"service": r["service"], "id": r["id"], "compliance": r["compliance"]}
            for r in env.get("resources", []) if r.get("id")
        ]
        return AgentInput(
            scenario_id=scenario["csv_id"],
            task=scenario.get("task") or scenario.get("objective_clean", ""),
            output_contract=scenario.get("output_contract", ""),
            tools=tool_specs(),
            resource_inventory=inventory,
            account_id=env.get("account_id", ""),
            region=env.get("region", self.region),
        )

    def run(self, agent_input: AgentInput) -> RunResult:
        t0 = time.time()
        messages = [{"role": "user", "content": agent_input.as_prompt()}]
        tool_calls: list[ToolCall] = []
        raw_results: list = []
        final_text = ""

        for _ in range(MAX_TURNS):
            reply = self._post(agent_input, messages)
            kind, payload = self._parse_agent_reply(reply)

            if kind == "final":
                final_text = payload
                break

            # tool_use: execute each requested call, feed results back
            tool_messages = []
            for call in payload:
                name = call.get("name", "")
                cid = call.get("id", name)
                params = call.get("input", call.get("arguments", {})) or {}
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except Exception:
                        params = {}
                output = execute_tool(self._session, name, params)
                tool_calls.append(ToolCall(tool=name, input=params, output=output))
                raw_results.append(output)
                tool_messages.append({"role": "tool", "tool_call_id": cid, "name": name, "content": output})

            messages.append({"role": "assistant", "tool_calls": payload})
            messages.extend(tool_messages)
        else:
            final_text = final_text or "[max turns reached without a final answer]"

        return RunResult(
            response=final_text,
            tool_calls=tool_calls,
            raw_tool_results=raw_results,
            elapsed=round(time.time() - t0, 1),
        )

    # ── wire protocol (adapt here for a different agent) ─────────────────────
    def _post(self, agent_input: AgentInput, messages: list) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        body = {
            "session_id": agent_input.scenario_id,
            "messages": messages,
            "tools": [t.to_public() for t in agent_input.tools],
            "resource_inventory": agent_input.resource_inventory,
            "region": agent_input.region,
        }
        r = requests.post(self.endpoint, headers=headers, json=body, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _parse_agent_reply(reply: dict) -> tuple[str, object]:
        """Normalize an agent reply to ('final', text) or ('tool_use', [calls]).
        Tolerant of the common shapes so most agents work without changes."""
        # explicit type
        rtype = (reply.get("type") or "").lower()
        calls = reply.get("tool_calls") or reply.get("tool_use") or []
        if rtype == "final" or (not calls and rtype in ("", "message", "final")):
            text = reply.get("response") or reply.get("content") or reply.get("output") or ""
            if isinstance(text, list):  # content-blocks style
                text = " ".join(b.get("text", "") for b in text if isinstance(b, dict))
            if text or not calls:
                return "final", text
        return "tool_use", calls
