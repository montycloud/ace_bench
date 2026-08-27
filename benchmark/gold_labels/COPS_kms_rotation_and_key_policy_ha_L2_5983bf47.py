"""
Gold labels: KMS Rotation and Key-Policy Hardening Roadmap
CSV ID: COPS-kms-rotation-and-key-policy-ha-L2-5983bf47
Level: L2
WAFR resources: 1e007832-6f44-4c5c-bc87-6a9bdddf4d28 confirmed with rotation disabled
Note: KMSCMKNonCompliant fixture (dbc1e4f2) not yet deployed — not in WAFR
"""

GOLD = {
    'csv_id': 'COPS-kms-rotation-and-key-policy-ha-L2-5983bf47',

    'description': (
        "The agent should identify KMS keys with rotation disabled from WAFR findings. "
        "The LogMetricsNonCompliant fixture KMS key (1e007832) is confirmed in WAFR. "
        "The KMSCMKNonCompliant fixture is not deployed — The agent should not fabricate its key ID. "
        "The plan should cover rotation enablement and key policy scoping."
    ),

    'correct_resources': [
        '1e007832-6f44-4c5c-bc87-6a9bdddf4d28',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface KMS resources with rotation findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of KMS rotation check failures'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate KMS resource types in assessment'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "KMSCMKNonCompliant fixture not yet deployed — dbc1e4f2-8170-42e7-8e60-0eee19653591 is not in the WAFR assessment",
        "Specific key policy Principal:* details are not accessible through WAFR assessment tools — only rotation status surfaces",
        "Multi-region replica considerations and re-wrap windows require direct KMS API access",
    ],
    'judge_criteria': [
        "Did the agent identify at least one real KMS key ID from tool output with rotation disabled (specifically 1e007832-6f44-4c5c-bc87-6a9bdddf4d28)?",
        "Did the agent avoid fabricating the KMSCMKNonCompliant fixture key ID (dbc1e4f2) which is not present in the WAFR assessment?",
        "Did the agent produce a hardening roadmap covering rotation enablement and key policy scoping grounded in what tools surfaced?",
        "Did the agent explicitly acknowledge that key policy details (Principal:* statements) require tooling beyond what WAFR assessment tools provide?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
