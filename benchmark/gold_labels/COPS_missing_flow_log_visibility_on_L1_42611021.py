"""
Gold labels: Missing Flow Log Visibility on Production VPCs
CSV ID: COPS-missing-flow-log-visibility-on-L1-42611021
Fixture: VPCNonCompliant (VPC with no flow logs enabled)

Note: The agent cannot return actual VPC IDs — it explicitly states
"Actual VPC IDs and detailed configuration require direct AWS API access."
It uses inferred account-prefixed IDs (vpc-REDACTED-ACCOUNT-01).
correct_resources uses the actual VPC IDs confirmed in WAFR.
"""

GOLD = {
    'csv_id': 'COPS-missing-flow-log-visibility-on-L1-42611021',

    'description': (
        "VPC Flow Logs capture metadata about network traffic in your AWS network — source IP, destination, port, "
        "protocol, and whether the traffic was allowed or denied. Without flow logs, there is no visibility into "
        "what is communicating inside your VPC: you cannot detect lateral movement, unexpected connections to "
        "sensitive resources, or data exfiltration attempts. Flow logs are essential for security investigations "
        "and network anomaly detection. "
        "The agent should identify VPCs that have flow logs disabled."
    ),

    'correct_resources': [
        # Actual VPC IDs confirmed in WAFR failing "Enable Flow Logs for VPC Subnets"
        'vpc-0574311ac28d9b744',
        'vpc-098106e3fda1f9ba5',
        'vpc-0a9630bfd89f3d25c',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top VPC resources with findings to identify those missing flow log configuration'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings summary to understand VPC flow log check failure counts and scope'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is VPC Flow Logs being disabled on production VPCs (not just a general network visibility concern)?",
        "Did the agent identify specific VPC IDs — or, if tools could not surface actual VPC IDs, did it explicitly acknowledge that rather than fabricating IDs like 'vpc-REDACTED-ACCOUNT-01'?",
        "Did the agent explain why flow logs matter (network forensics, lateral movement detection, anomaly detection)?",
        "Did the agent avoid hallucinating VPC IDs or flow log configuration details not present in tool output?",
    ],
}
