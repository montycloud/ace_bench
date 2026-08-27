"""
Gold labels: Observability Baseline Uplift for Production Workloads
CSV ID: COPS-observability-baseline-uplift-L2-637c29d9
Level: L2
WAFR resources: LogMetricFilter resources and account-level CloudWatch findings confirmed
"""

GOLD = {
    'csv_id': 'COPS-observability-baseline-uplift-L2-637c29d9',

    'description': (
        "The agent should identify telemetry gaps from WAFR findings — log retention missing, "
        "metric filters misconfigured, alarms without SNS actions — and produce a per-workload "
        "observability uplift plan. Real LogMetricFilter resources are confirmed in WAFR."
    ),

    'correct_resources': [
        'NonMFASignInLogsMetricFilterNC-iD6CVapxFVRk',
        'ConfigChangesLogsMetricFilterNC-utPQ1meP3L0Z',
        'S3ChangesLogsMetricFilterNC-IldAMGdF8rAX',
        'REDACTED-ACCOUNT/us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top monitoring resources with findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of observability gaps'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate monitoring resource types'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Specific CloudWatch alarm SNS action configuration not accessible through WAFR assessment tools",
        "Individual CloudWatch log group names with missing retention policies not surfaced — only aggregate counts available",
        "CloudWatch dashboard definitions and SLI/SLO configurations require direct AWS API access",
        "Ticketing integration details are outside available tool scope",
    ],
    'judge_criteria': [
        "Did the agent identify real observability gaps from tool output — specifically log retention failures, metric filter issues, or alarm coverage gaps?",
        "Did the agent surface specific LogMetricFilter or account-level resource identifiers from tool output rather than fabricating alarm or filter names?",
        "Did the agent produce a structured uplift plan covering the telemetry gaps it could verify (log retention, alarm coverage, metric filters)?",
        "Did the agent acknowledge what it could not assess — specific alarm SNS targets, SLI definitions, dashboard content — rather than fabricating those details?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
