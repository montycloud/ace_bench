"""
Gold labels: Spend Budgets Without Notification Thresholds
CSV ID: COPS-spend-budgets-without-notifica-L1-573baf91
Fixture: BudgetsNonCompliant (not yet deployed — budget with no notification actions)
Note: The agent says 'budget', 'notification', 'threshold', 'alert' but not 'spend'.
  Synthetic check IDs and out-of-scope resources appear in some runs.
"""

GOLD = {
    'csv_id': 'COPS-spend-budgets-without-notifica-L1-573baf91',

    'correct_resources': [],

    'description': (
        "AWS Budgets lets you set spending limits on your account or specific services and receive alerts "
        "when thresholds are crossed. A budget with no notification thresholds configured is functionally "
        "useless — costs can exceed the budget limit and nobody gets alerted until the monthly bill arrives. "
        "This is a common FinOps gap where budgets are created for visibility but the alert wiring is forgotten. "
        "The agent should identify AWS Budgets that exist but have no notification actions configured."
    ),
    'should_not_flag': [
        # synthetic check-level IDs
        'AWS_BUDGET_ACCOUNT_LEVEL',
        'AWS_SNS_BUDGET_NOTIFICATIONS',
        'AWS_COST_ANOMALY_DETECTION',
        'CHECK_49577',
        'CHECK_24953',
        # out-of-scope resources pulled into response
        's3noncompliant-s3bucket1-vaeopnyvk0ru',
        's3noncompliant-s3bucket2-uaefqzdhl7fg',
        'REDACTED-ACCOUNT/us-east-1',
        'i-01baa59f318a3c59e',
        'vol-028f30f6b745e2ae5',
    ],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top checks/resources — budget notification gaps surface as check-level findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings status counts to understand scope of budget notification configuration gaps'},
    ],

    'judge_criteria': [
        "Did the agent identify that the issue is AWS Budgets configured without notification thresholds or alert actions (not just budgets being absent)?",
        "Did the agent identify specific budget names — or, if the fixture is not deployed and tools cannot surface them, explicitly acknowledge that rather than fabricating budget names?",
        "Did the agent avoid hallucinating out-of-scope resources (S3 buckets, EC2 instances, etc.) as budget violation findings?",
        "Did the agent distinguish between a budget existing and a budget being correctly configured with cost alert notifications?",
    ],
}
