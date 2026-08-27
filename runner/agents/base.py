"""
Agent-agnostic adapter interface.

Every agent ACE Bench evaluates — whether it drives AWS through tools the harness
offers, or is a black box that already holds its own AWS access — plugs in behind
this one contract. The runner (``runner.run``) knows nothing about any specific
agent; it only speaks ``AgentAdapter``.

Two built-in adapter shapes:

  ToolLoopAdapter   (observable_tools=True)
      The harness owns the AWS credentials, offers the agent a fixed catalog of
      read-only tools + a live resource inventory, executes each tool call the
      agent requests, and records the full trace. Because the trace is visible,
      the Tools pillar is scored against the gold label's expected_tools.

  BlackBoxAdapter   (observable_tools=False)
      The agent has its own AWS access and its own tools. The harness sends the
      scenario and reads back the final answer only. Tool calls are not
      observable, so the Tools pillar is skipped (Answer / Safety / Output /
      LLM-judge still apply). The Bedrock adapters are of this shape.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ToolSpec:
    """A single tool offered to the agent (name + JSON-schema input)."""
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)

    def to_public(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


@dataclass
class AgentInput:
    """Everything an agent needs to attempt a scenario — no fixture paths, no
    assessment IDs, nothing account-specific except what the manifest resolved."""
    scenario_id: str
    task: str                       # the natural-language objective
    output_contract: str            # required JSON output schema, as text
    tools: list[ToolSpec] = field(default_factory=list)      # offered catalog
    resource_inventory: list[dict] = field(default_factory=list)  # from manifest
    account_id: str = ""
    region: str = ""

    def as_prompt(self) -> str:
        """Flatten to a single prompt for agents that take plain text."""
        parts = [self.task.strip(), "", self.output_contract.strip()]
        if self.resource_inventory:
            parts += ["", "Resources available in this environment:"]
            for r in self.resource_inventory:
                parts.append(f"  - {r.get('service','')}: {r.get('id','')} ({r.get('compliance','')})")
        if self.tools:
            parts += ["", "Tools available to you:"]
            for t in self.tools:
                parts.append(f"  - {t.name}: {t.description}")
        return "\n".join(parts)


@dataclass
class ToolCall:
    tool: str
    input: dict | str | None = None
    output: str | None = None


@dataclass
class RunResult:
    """Normalized agent output that the evaluator scores. `tool_calls` is empty
    for black-box agents (observable_tools=False)."""
    response: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_tool_results: list = field(default_factory=list)
    elapsed: float | None = None
    trace: list = field(default_factory=list)

    def to_capture_dict(self) -> dict:
        return {
            "response": self.response,
            "tool_calls": [
                {"name": tc.tool, "tool": tc.tool, "input": tc.input, "output": tc.output}
                for tc in self.tool_calls
            ],
            "raw_tool_results": self.raw_tool_results,
            "elapsed": self.elapsed,
        }


@runtime_checkable
class AgentAdapter(Protocol):
    name: str
    observable_tools: bool

    def build_input(self, scenario: dict, gold: dict, env: dict) -> AgentInput:
        """Assemble the AgentInput for a scenario from the resolved env manifest."""
        ...

    def run(self, agent_input: AgentInput) -> RunResult:
        """Drive the agent to completion and return a normalized RunResult."""
        ...
