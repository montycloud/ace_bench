"""
Gold labels: Critical Metrics Without Alarm Coverage
CSV ID: COPS-critical-metrics-without-alarm-L1-b35f5df1
Fixture: LogMetricsNonCompliant — 2 alarms exist with no SNS actions (silent alarms)
"""

GOLD = {
    'csv_id': 'COPS-critical-metrics-without-alarm-L1-b35f5df1',

    'description': (
        "CloudWatch Alarms monitor metrics and can trigger SNS notifications to alert on-call teams when "
        "a threshold is crossed. If an alarm exists but has no SNS action attached, it fires silently — "
        "the threshold is breached but nobody gets paged. This is a common misconfiguration: alarms are "
        "created but the notification wiring is forgotten. "
        "The agent should surface alarms that are monitoring critical metrics but have no notification actions configured."
    ),

    'correct_resources': [
        # Metric filter names from LogMetricsNonCompliant fixture — these appear in WAFR as failing
        # "alarm exist" checks because their associated alarms have no SNS actions configured
        'NonMFASignInLogsMetricFilterNC-iD6CVapxFVRk',
        'ConfigChangesLogsMetricFilterNC-utPQ1meP3L0Z',
        'S3ChangesLogsMetricFilterNC-IldAMGdF8rAX',
    ],

    'should_not_flag': [
        # synthetic IDs the agent hallucinates — not real resources in the assessment
        'check-9577', 'check-4953', 'check-8082', 'check-7413', 'check-9147',
    ],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top resources/checks by findings count to surface alarms without SNS actions'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get overall findings status counts to understand scale of alarm coverage gaps'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is CloudWatch Alarms with no SNS notification actions configured (silent alarms), not just alarms being absent entirely?",
        "Did the agent identify specific alarm or metric filter names — or, if tools could not surface them, explicitly acknowledge that limitation rather than reporting synthetic check IDs like 'check-9577'?",
        "Did the agent avoid hallucinating synthetic check IDs (e.g., 'check-9577', 'check-4953') as real resource identifiers?",
        "Did the agent recommend adding SNS notification actions to existing silent alarms rather than just suggesting new alarms be created?",
    ],
}
