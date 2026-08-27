"""
Gold labels: Serverless Event-Path Reliability Review
CSV ID: COPS-serverless-event-path-reliabil-L2-ffc06f96
Level: L2
Fixture: LambdaNonCompliant
Note: Tools surface resource inventory (counts by type) but cannot access Lambda DLQ,
  retry policy, or concurrency configuration. This is a fundamental platform gap.
  The agent should enumerate what it CAN see and explicitly acknowledge what it cannot.
"""

GOLD = {
    'csv_id': 'COPS-serverless-event-path-reliabil-L2-ffc06f96',

    'description': (
        "The agent should assess serverless event-path reliability by examining what tools can surface. "
        "Available: resource inventory (Lambda count, SQS queues, SNS topics, DynamoDB tables). "
        "Not available: Lambda DLQ configuration, retry policies, concurrency limits, idempotency settings. "
        "The agent should enumerate the gap clearly rather than fabricating configuration details."
    ),

    'correct_resources': [],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate serverless resource types and counts in the assessment'},
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top Lambda/serverless resources with findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of reliability findings across serverless resources'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Lambda function DLQ configuration, retry policies, reserved/provisioned concurrency, "
        "and timeout settings are not accessible through available WAFR assessment tools",
        "SQS queue DLQ linkage and EventBridge retry policies are not surfaced at resource level",
        "Individual Lambda function names may not surface from WAFR checks — only counts and type summaries",
    ],
    'judge_criteria': [
        "Did the agent correctly identify that detailed Lambda configuration (DLQ, retry policies, concurrency) is not accessible through available tools, and state this explicitly in platform_gaps?",
        "Did the agent avoid fabricating account-level resource IDs (e.g. 'lambda-REDACTED-ACCOUNT', 's3-REDACTED-ACCOUNT') that do not correspond to real resource identifiers?",
        "Did the agent enumerate what it could actually verify from tool output — resource type counts, WAFR findings, assessment data?",
        "Did the agent's plan address reliability gaps in a way that is grounded in what was observable, rather than fabricating specific configuration findings it could not verify?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
