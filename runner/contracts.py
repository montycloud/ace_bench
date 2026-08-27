"""
Generic, agent-agnostic output contracts.

These replace the legacy, agent-branded system contexts + contracts that used to live in
loader.py. They contain no agent name, no day2 assessment ID,
and no AWS account number — anything account-specific reaches the agent only
through the resolved environment manifest.

L1 = assessment (find misconfigured resources). L2 = planning (synthesize findings
into a prioritized plan).
"""

SYSTEM_CONTEXT = (
    "You are a CloudOps assessment agent. Complete the full investigation in a single "
    "run without pausing for confirmation. Use only the read-only tools provided to you; "
    "do not attempt to modify any resource. Ground every finding in tool output — never "
    "fabricate resource IDs or details you did not observe."
)

OUTPUT_CONTRACT_L1 = """
Complete your full investigation first, then return your final answer as valid JSON matching this schema exactly.
"findings" and "improvement_plan" MUST be arrays — one object per resource.

{
  "summary": "one paragraph executive summary of what was found",
  "findings": [
    {
      "resource_id": "exact AWS resource id or name (not ARN)",
      "resource_type": "S3 | KMS | Lambda | SecurityGroup | CloudWatch Alarm | ...",
      "check": "the specific compliance check that failed",
      "severity": "Critical | High | Medium | Low",
      "evidence": "cited data from tool output supporting this finding"
    }
  ],
  "improvement_plan": [
    {
      "resource_id": "exact resource id matching a finding above",
      "action": "specific remediation step",
      "priority": "High | Medium | Low",
      "effort": "Small | Medium | Large"
    }
  ]
}"""

OUTPUT_CONTRACT_L2 = """
Complete your full investigation first, then return your final answer as valid JSON matching this schema exactly.
"observations" and "plan" MUST be arrays. If you cannot verify something from tool output, say so in "platform_gaps".

{
  "summary": "one paragraph: what was investigated, what the tools surfaced, and the key risks found",
  "observations": [
    {
      "area": "service or domain area (e.g. IAM, Lambda, S3, VPC, Cost)",
      "finding": "what was found — grounded in tool output, not inferred",
      "evidence": "direct citation from tool output (tool name and specific data)",
      "severity": "Critical | High | Medium | Low"
    }
  ],
  "platform_gaps": [
    "specific description of what could not be assessed and why"
  ],
  "plan": [
    {
      "action": "specific recommendation",
      "scope": "which resources or service areas this applies to",
      "priority": "High | Medium | Low",
      "effort": "Small | Medium | Large",
      "rationale": "why this action — tied to an observation above"
    }
  ]
}"""


def output_contract(level: int) -> str:
    return OUTPUT_CONTRACT_L2 if level == 2 else OUTPUT_CONTRACT_L1
