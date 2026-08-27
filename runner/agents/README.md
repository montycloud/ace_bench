# runner/agents/

Adapters that translate a scenario into a call against a specific agent and normalize its
response for scoring. Every adapter satisfies the `AgentAdapter` interface in `base.py`, so
the runner has **no per-agent branching** — it goes through `get_adapter()` in `__init__.py`.

- **`base.py`** — the `AgentAdapter` contract: `AgentInput`, `RunResult`, `ToolCall`, `ToolSpec`
- **`toolloop.py`** — **agent-agnostic** adapter. The harness holds AWS credentials, offers the
  read-only tool catalog + resource inventory, drives the agent's HTTP endpoint through a
  tool-use loop, and records the full trace (`observable_tools = True`). Default path.
- **`bedrock.py`** — black-box adapter for the Bedrock agents (`s3soa`, `soa`, `eoa`, `poa`);
  they hold their own AWS access and do not expose tool calls (`observable_tools = False`).

## Adding an adapter

Implement `name`, `observable_tools`, `build_input(scenario, gold, env)` and
`run(agent_input) -> RunResult`, then register it in `__init__.py::get_adapter`. Set
`observable_tools = False` if the agent's tool trace is not visible — the Tools pillar is then
skipped automatically and only Answer/Safety/Output/Judge apply.

See the root [README](../../README.md) for agent codes and required credentials.
