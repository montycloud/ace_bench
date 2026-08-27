"""
Gold labels: Unrestricted Inbound Access on Management Ports
CSV ID: COPS-unrestricted-inbound-access-on-L1-6235afe3
Fixture: VPCNonCompliant (2 SGs open to 0.0.0.0/0 — SSH port 22, RDP port 3389, all traffic)
  SG (Security Group): stateful EC2-level firewall — return traffic is automatically allowed, unlike NACLs
"""

GOLD = {
    'csv_id': 'COPS-unrestricted-inbound-access-on-L1-6235afe3',

    'description': (
        "Security groups are virtual firewalls attached to EC2 instances and other AWS resources. "
        "A rule allowing inbound traffic from 0.0.0.0/0 (the entire internet) on port 22 (SSH) or "
        "port 3389 (RDP) exposes the instance to brute-force attacks, credential stuffing, and exploitation "
        "of any SSH/RDP vulnerabilities — from anyone on the internet, at all times. "
        "These management ports should only be reachable from trusted IPs (e.g., a VPN or bastion host). "
        "The agent should identify security groups with unrestricted inbound rules on management ports."
    ),

    'correct_resources': [
        # WAFR confirms only these two SG IDs fail "Restrict access to remote server ports (tcp3389 and tcp22)"
        'sg-0c9d922a6676b8021',
        'sg-07aebdd225b47ba16',
    ],

    'should_not_flag': [
        'default',
    ],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top resources/checks by findings count to surface non-compliant security groups'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate SecurityGroup resource types in assessment to identify exposed instances'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings status counts to understand scope of unrestricted inbound access violations'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is unrestricted inbound access (0.0.0.0/0 or ::/0) on sensitive management ports such as 22 (SSH) or 3389 (RDP)?",
        "Did the agent identify specific security group IDs — or, if tools could not surface them, explicitly acknowledge that rather than fabricating security group names?",
        "Did the agent avoid inventing resource IDs, evidence, or findings it could not verify from tool output?",
        "Did the agent avoid flagging out-of-scope resources or making claims not supported by the assessment data?",
    ],
}
