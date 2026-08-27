"""
Gold labels: CloudWatch Log Groups Without Retention
CSV ID: COPS-cloudwatch-log-groups-without-L1-fedcd002
Fixture: CloudWatchNonCompliant (not yet deployed — log group testloggroup with no retention policy)
Note: WAFR scan flags 20 log groups across the account with no retention set.
  Assessment returns check-level summary strings, not specific log group names — testloggroup is a
  platform gap signal. The agent says 'retention' but not 'expiration'.
"""

GOLD = {
    'csv_id': 'COPS-cloudwatch-log-groups-without-L1-fedcd002',

    'description': (
        "CloudWatch Log Groups store application, audit, and debug logs. Without a retention policy, "
        "logs accumulate indefinitely — racking up storage costs and violating compliance requirements "
        "that mandate logs be purged after a set period. Every log group should have an expiry configured "
        "(e.g., 90 days for debug logs, longer for audit trails). "
        "The agent should identify log groups with no retention policy and recommend tiered retention settings."
    ),

    'correct_resources': [
        # WAFR surfaces ~30 log groups failing "CloudWatch Logs Retention Configuration"
        # The assessment does not return specific log group names for retention checks.
        # The agent's correct response is identifying the account-level gap, not a specific log group.
        'REDACTED-ACCOUNT/us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top resources/checks to identify log groups flagged for missing retention policy'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings summary to understand CloudWatch log retention check failure counts'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is CloudWatch Log Groups with no retention policy (not just missing encryption or other log group settings)?",
        "Did the agent identify specific log group names — or, if tools could not surface individual log group names, did it explicitly acknowledge that limitation rather than fabricating log group names?",
        "Did the agent recommend tiered retention settings appropriate to log type (e.g., shorter for debug logs, longer for audit/compliance logs)?",
        "Did the agent avoid inventing specific log group names or retention status details not verifiable from tool output?",
    ],
}
