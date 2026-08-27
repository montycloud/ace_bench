"""
Gold labels: Efficiency Review for Request-Driven Workloads
CSV ID: COPS-efficiency-review-for-request-L2-30d1c7a0
Level: L2
WAFR resources: API Gateway stages (xgkoo1ofg2) confirmed with throttling/WAF failures
Note: p50/p95/p99 latency and cost-per-request metrics not accessible through WAFR tools
"""

GOLD = {
    'csv_id': 'COPS-efficiency-review-for-request-L2-30d1c7a0',

    'description': (
        "The agent should identify request-driven workload efficiency gaps from WAFR findings "
        "— specifically API Gateway stages missing throttling and WAF. Real API Gateway stages "
        "are confirmed in WAFR. Latency metrics and cost-per-request require CloudWatch access "
        "not available through current tools."
    ),

    'correct_resources': [
        'xgkoo1ofg2/UnEncryptCache',
        'xgkoo1ofg2/UnEncryptCache1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top API Gateway resources with efficiency findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of performance efficiency gaps'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate request-driven resource types'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "p50/p95/p99 latency percentiles not accessible through WAFR assessment tools — require CloudWatch GetMetricStatistics",
        "Cost-per-request calculation requires CloudWatch metrics and Cost Explorer data not available through current tools",
        "Error budget burn rate requires SLO definition data not stored in WAFR",
        "Lambda memory tuning recommendations require CloudWatch Logs Insights access not available",
        "DAX and connection pooling configuration details not surfaced through WAFR assessment tools",
    ],
    'judge_criteria': [
        "Did the agent identify the API Gateway stages from tool output as the primary request-driven workload with efficiency gaps?",
        "Did the agent avoid fabricating latency percentiles, cost-per-request figures, or error budget burn rates not accessible through available tools?",
        "Did the agent produce efficiency improvement recommendations grounded in what tools actually surfaced (throttling gaps, WAF absence)?",
        "Did the agent explicitly acknowledge that CloudWatch metrics for latency and cost-per-request analysis are not accessible through available tools?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
