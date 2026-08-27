"""
Gold labels: Multi-Account Portfolio Health Rollup
CSV ID: COPS-multi-account-portfolio-health-L2-31144309
Level: L2
Note: Only single account (REDACTED-ACCOUNT) visible through available tools.
  Multi-account portfolio requires AWS Organizations access not available.
"""

GOLD = {
    'csv_id': 'COPS-multi-account-portfolio-health-L2-31144309',

    'description': (
        "The agent should produce a portfolio health rollup from available assessment data. "
        "Only a single account (REDACTED-ACCOUNT) is accessible through current tools — "
        "The agent should acknowledge this as a platform gap and produce the best single-account "
        "summary it can rather than fabricating multi-account data."
    ),

    'correct_resources': [
        'REDACTED-ACCOUNT/us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get finding counts by pillar and severity for available account'},
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top offending resources within accessible account'},
        {'tool': 'get_assessment', 'params': {}, 'reason': 'Get assessment metadata and overall health status'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Multi-account portfolio data requires AWS Organizations access not available through current tools",
        "Only account REDACTED-ACCOUNT is accessible — cross-account rollup is not possible",
        "Trend vs last review data requires historical assessment snapshots not available through current tools",
        "Top-5 offending workloads across accounts requires multi-account aggregation not supported",
    ],
    'judge_criteria': [
        "Did the agent correctly acknowledge that only a single account is accessible and multi-account portfolio data is a platform gap?",
        "Did the agent produce a meaningful single-account health summary from available assessment data rather than refusing to answer?",
        "Did the agent surface pillar-level finding counts or top resources grounded in actual tool output?",
        "Did the agent avoid fabricating multi-account data, cross-account trends, or workload health scores from other accounts?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
