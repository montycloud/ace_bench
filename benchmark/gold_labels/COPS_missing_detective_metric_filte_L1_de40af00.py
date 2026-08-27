"""
Gold labels: Missing Detective Metric Filters for Account Events
CSV ID: COPS-missing-detective-metric-filte-L1-de40af00
Fixture: LogMetricsNonCompliant — metric filters exist but have typos/broken patterns
  - CloudtrailChnagesLogsMetricFilterNC: pattern uses 'Trail' instead of 'CreateTrail'
"""

GOLD = {
    'csv_id': 'COPS-missing-detective-metric-filte-L1-de40af00',

    'description': (
        "AWS CloudTrail records every API call in your account. Metric filters can watch CloudTrail logs "
        "and trigger CloudWatch alarms on specific events — for example, root account login, unauthorized API calls, "
        "or security group changes. A typo or wrong pattern in a metric filter means it never matches, "
        "so critical security events go completely undetected. "
        "The agent should identify metric filters that are misconfigured or missing for key account-level events."
    ),

    'correct_resources': [
        # Actual LogMetricsNonCompliant fixture resources confirmed in WAFR
        'NonMFASignInLogsMetricFilterNC-iD6CVapxFVRk',
        'ConfigChangesLogsMetricFilterNC-utPQ1meP3L0Z',
        'S3ChangesLogsMetricFilterNC-IldAMGdF8rAX',
    ],

    'should_not_flag': [
        # synthetic IDs the agent hallucinates — not real resources in the assessment
        'security_check_0', 'security_check_1', 'security_check_2', 'security_check_3',
        'security_check_4', 'security_check_5', 'security_check_6', 'security_check_7',
        'security_check_8', 'security_check_9', 'security_check_10', 'security_check_11',
        'security_check_12', 'security_check_13', 'security_check_14', 'security_check_15',
        'security_check_16', 'security_check_17', 'security_check_18', 'security_check_19',
        'service_amazon_sqs', 'service_aws_cloudtrail', 'service_amazon_sns',
        'service_amazon_s3', 'service_amazon_ec2',
    ],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface the real metric-filter resources failing detective-control checks, matching sibling scenarios on the same fixture'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Retrieve the underlying findings rather than relying only on account-level security-service overview tools'},
    ],
    'judge_criteria': [
        "Did the agent identify that metric filters for key CloudTrail events are missing or misconfigured (wrong filter patterns/typos), not just absent?",
        "Did the agent identify specific metric filter names — or, if tools could not surface specific names, explicitly acknowledge that rather than inventing synthetic IDs like 'security_check_0'?",
        "Did the agent explain which events should be monitored (e.g., root login, unauthorized API calls, IAM changes, security group modifications)?",
        "Did the agent avoid hallucinating synthetic resource IDs like 'security_check_N' or 'service_amazon_*' as real assessment findings?",
    ],
}
