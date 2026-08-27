"""
Gold labels: Lambda Functions Without Dead-Letter Handling
CSV ID: COPS-lambda-functions-without-dead-L1-5e6f89f2
Fixture: LambdaNonCompliant — nc-lambda functions have no DLQ (Dead-Letter Queue) configured
  DLQ: an SQS queue that catches failed Lambda invocations after all retries — without one, errors silently disappear
"""

GOLD = {
    'csv_id': 'COPS-lambda-functions-without-dead-L1-5e6f89f2',

    'description': (
        "AWS Lambda functions process events asynchronously. When a function fails after all retries, "
        "the failed event is discarded unless a Dead-Letter Queue (DLQ) — an SQS queue — is configured. "
        "Without a DLQ, failed invocations silently disappear: no retry, no alert, no audit trail. "
        "This is a common reliability gap in event-driven architectures where silent failures are hard to detect. "
        "The agent should identify Lambda functions that have no DLQ configured."
    ),

    'correct_resources': [
        'nc-lambda-func-to-ad9c2340-2e6d-11f1-ba55-0e4a2ef2e90f',
        'nc-lambda-func-ad9c2340-2e6d-11f1-ba55-0e4a2ef2e90f',
        'HelloWorldFunction2',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top resources/checks by findings count to surface Lambda functions without DLQ'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings status counts to understand scale of Lambda dead-letter configuration gaps'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is Lambda functions missing a Dead-Letter Queue (DLQ) configuration for failed async invocations?",
        "Did the agent identify specific Lambda function names — or, if tools could not surface function names, explicitly acknowledge that rather than fabricating names?",
        "Did the agent explain the consequence of missing DLQs (failed events silently discarded, no retry or audit trail)?",
        "Did the agent avoid fabricating Lambda function names or DLQ status details not present in tool output?",
    ],
}
