"""
Agent adapter registry.

`get_adapter(name, region=...)` returns an object satisfying the AgentAdapter
contract in runner.agents.base. The runner (runner.run) only ever talks to this
registry — it has no per-agent branching.

Adapter shapes:
  toolloop            agent-agnostic; harness offers the AWS tool catalog and
                      records the trace (observable Tools pillar). Needs
                      AGENT_ENDPOINT + AWS credentials.
  s3soa/soa/eoa/poa   black-box Bedrock agents (own AWS access, trace unobservable)
"""

BEDROCK_CODES = ("s3soa", "soa", "eoa", "poa")


def list_agents() -> list[str]:
    return ["toolloop", *BEDROCK_CODES]


def get_adapter(name: str, *, region: str = "us-east-1", **kwargs):
    if name == "toolloop":
        from runner.agents.toolloop import ToolLoopAdapter
        return ToolLoopAdapter(region=region, **kwargs)
    if name in BEDROCK_CODES:
        from runner.agents.bedrock import BedrockAdapter
        return BedrockAdapter(agent_code=name)
    raise ValueError(f"Unknown agent: {name}. Choose from: {', '.join(list_agents())}")
