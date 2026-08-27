"""
Gold labels: Incident-Readiness Mapping for Critical Alarms
CSV ID: COPS-incident-readiness-mapping-for-L2-7b2bcfef
Level: L2
WAFR resources: LogMetricFilter resources with silent alarms (no SNS actions) confirmed
"""

GOLD = {
    'csv_id': 'COPS-incident-readiness-mapping-for-L2-7b2bcfef',

    'description': (
        "The agent should identify critical alarms that fire silently (no SNS action) from WAFR findings "
        "and produce an incident readiness plan. The LogMetricsNonCompliant metric filters are confirmed "
        "in WAFR as failing alarm checks. Runbook linkage and on-call routing are platform gaps."
    ),

    'correct_resources': [
        'NonMFASignInLogsMetricFilterNC-iD6CVapxFVRk',
        'ConfigChangesLogsMetricFilterNC-utPQ1meP3L0Z',
        'S3ChangesLogsMetricFilterNC-IldAMGdF8rAX',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top alarm/monitoring resources with findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of alarm coverage and notification gaps'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Runbook linkage per alarm is not accessible through WAFR assessment tools",
        "On-call escalation targets and SNS subscription destinations are not surfaced by available tools",
        "Incident management platform integration (PagerDuty, OpsGenie) requires tooling outside WAFR scope",
        "Specific alarm threshold values and evaluation periods not accessible through assessment tools",
    ],
    'judge_criteria': [
        "Did the agent identify the specific alarm/metric filter resources from tool output that lack SNS notification actions?",
        "Did the agent produce an incident readiness plan that maps alarms to remediation actions grounded in what tools surfaced?",
        "Did the agent explicitly acknowledge that runbook linkage, on-call targets, and SNS destinations are not accessible through available tools?",
        "Did the agent avoid fabricating alarm names, SNS topic ARNs, or runbook URLs not present in tool output?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
