"""
Gold labels: Network Tiering and Egress Control Uplift
CSV ID: COPS-network-tiering-and-egress-con-L2-c4df527d
Level: L2
WAFR resources: VPCs without flow logs, SGs open to 0.0.0.0/0 confirmed in WAFR
Note: NACLNonCompliant not deployed
"""

GOLD = {
    'csv_id': 'COPS-network-tiering-and-egress-con-L2-c4df527d',

    'description': (
        "The agent should assess VPC network topology and security group configuration from WAFR findings "
        "and produce a network tiering and egress control plan. VPCs without flow logs and SGs with "
        "unrestricted inbound are confirmed in WAFR. NACLs are not deployed."
    ),

    'correct_resources': [
        'vpc-0574311ac28d9b744',
        'vpc-098106e3fda1f9ba5',
        'vpc-0a9630bfd89f3d25c',
        'sg-0c9d922a6676b8021',
        'sg-07aebdd225b47ba16',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top VPC/network resources with findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of network configuration gaps'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate network resource types in assessment'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "NACLNonCompliant fixture not deployed — NACL rule details not in WAFR assessment",
        "VPC endpoint configuration, subnet CIDR blocks, and route table details not accessible through WAFR assessment tools",
        "NAT Gateway placement and AZ-level egress topology not surfaced by available tools",
        "Three-tier topology migration cutover evidence requires direct AWS networking API access",
    ],
    'judge_criteria': [
        "Did the agent identify real VPC IDs and/or security group IDs from tool output as the primary network exposure findings?",
        "Did the agent avoid fabricating NACL IDs or NACL rule details that are not present in the WAFR assessment?",
        "Did the agent propose a network tiering plan (edge/app/data tiers) grounded in the actual network resources it found?",
        "Did the agent acknowledge that VPC endpoint configuration and subnet-level details require tooling beyond what WAFR assessment tools provide?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
