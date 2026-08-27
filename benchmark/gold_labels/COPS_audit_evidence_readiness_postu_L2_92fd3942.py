"""
Gold labels: Audit-Evidence Readiness Posture
CSV ID: COPS-audit-evidence-readiness-postu-L2-92fd3942
Level: L2
WAFR resources: LogMetricFilter resources and account-level CloudTrail/Config gaps confirmed
"""

GOLD = {
    'csv_id': 'COPS-audit-evidence-readiness-postu-L2-92fd3942',

    'description': (
        "The agent should score audit evidence readiness by checking CloudTrail, Config, Security Hub, "
        "and log metric filter status from WAFR findings. LogMetricFilter resources with misconfigured "
        "patterns are confirmed in WAFR. CloudTrail log file integrity and Security Hub conformance "
        "pack scores require tooling beyond what is available."
    ),

    'correct_resources': [
        'NonMFASignInLogsMetricFilterNC-iD6CVapxFVRk',
        'ConfigChangesLogsMetricFilterNC-utPQ1meP3L0Z',
        'S3ChangesLogsMetricFilterNC-IldAMGdF8rAX',
        'REDACTED-ACCOUNT/us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top audit-relevant resources with findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of audit control gaps'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate audit-relevant resource types'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "CloudTrail log file integrity verification status not accessible through WAFR assessment tools",
        "Security Hub CIS and PCI conformance pack scores not directly surfaced through available tools",
        "AWS Config aggregator and cross-account recorder status require Organizations access not available",
        "CIS/PCI control mapping requires Security Hub conformance pack data not accessible through current tools",
    ],
    'judge_criteria': [
        "Did the agent identify real audit evidence gaps from tool output — metric filter misconfigurations, CloudTrail/Config/GuardDuty status, or log retention failures?",
        "Did the agent surface specific LogMetricFilter or account-level resource identifiers from tool output rather than fabricating check control IDs?",
        "Did the agent produce an audit readiness scorecard covering what it could verify, with explicit Red/Amber/Green status grounded in tool evidence?",
        "Did the agent acknowledge that CloudTrail integrity verification, Security Hub conformance pack scores, and CIS/PCI control mapping require tooling beyond what is available?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
