"""
Gold labels: Over-Permissive NACL Rules Across Tiers
CSV ID: COPS-over-permissive-nacl-rules-acr-L1-ab47360a
Fixture: NACLNonCompliant (not yet deployed — NACL with SSH/RDP/all-traffic open to 0.0.0.0/0)
  NACL (Network Access Control List): stateless subnet-level firewall — unlike security groups, return traffic needs an explicit allow rule
Note: NACLNonCompliant stack depends on VPCNonCompliant and needs deploying first
"""

GOLD = {
    'csv_id': 'COPS-over-permissive-nacl-rules-acr-L1-ab47360a',

    'description': (
        "Network ACLs (NACLs) are stateless subnet-level firewalls — unlike security groups, they apply to "
        "entire subnets and return traffic must be explicitly allowed. NACLs that permit all traffic "
        "(0.0.0.0/0) on sensitive ports like SSH (22) or RDP (3389) across different network tiers allow "
        "unrestricted lateral movement inside the VPC. An attacker who compromises one subnet can freely "
        "reach any other. "
        "The agent should identify NACLs with overly permissive rules that violate network segmentation."
    ),

    'correct_resources': [],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top NACL/network resources with findings to identify over-permissive rules'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings summary to understand NACL security check failure distribution'},
    ],

    'known_platform_gaps': [
        "NACLNonCompliant fixture not deployed (depends on VPCNonCompliant, which must be deployed first) — NACL exposure is not present in the WAFR assessment; the agent should not fabricate NACL identifiers",
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is Network ACL rules permitting all traffic (0.0.0.0/0) on sensitive ports (SSH 22, RDP 3389) across network tiers?",
        "Did the agent correctly report that no NACL resources were found in the WAFR assessment, rather than treating this as an open question or fabricating NACL identifiers?",
        "Did the agent explain the unique risk of NACLs vs security groups (stateless, subnet-level, affects all instances in the subnet across tiers)?",
        "Did the agent avoid fabricating NACL rule details or IDs not verifiable from tool output?",
    ],
}
