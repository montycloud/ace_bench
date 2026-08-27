"""
Gold labels: Unify Encryption Posture Across Shared Data Stores
CSV ID: COPS-unify-encryption-posture-acros-L2-34cc7d74
Level: L2
WAFR resources: S3 buckets, DynamoDB test-table, SQS queue confirmed with encryption gaps
"""

GOLD = {
    'csv_id': 'COPS-unify-encryption-posture-acros-L2-34cc7d74',

    'description': (
        "The agent should surface encryption gaps across S3, DynamoDB, SQS, and SNS from WAFR findings "
        "and produce a tiered encryption plan (SSE-S3, SSE-KMS AWS-managed, SSE-KMS CMK). "
        "Real resources with encryption failures are confirmed in WAFR."
    ),

    'correct_resources': [
        's3noncompliant-s3bucket1-vaeopnyvk0ru',
        's3noncompliant-s3bucket2-uaefqzdhl7fg',
        'wartestncs3bucketnc03-REDACTED-ACCOUNT-us-east-1',
        'test-table-d4e9a170-2e6d-11f1-aa48-0afff185c25b',
        'warf-test-sqs-queue-non-compliant',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top resources with encryption failures'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of encryption gaps across services'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate resource types with encryption findings'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "SNS topic war-test-a493 encryption status may not surface as a specific named resource in WAFR tools",
        "EBS volume encryption status requires direct AWS API access beyond WAFR assessment tools",
        "CMK provisioning templates and key-policy JSON cannot be generated from WAFR tool output alone",
    ],
    'judge_criteria': [
        "Did the agent identify encryption gaps across multiple data store types (S3, DynamoDB, SQS) grounded in WAFR findings?",
        "Did the agent identify specific resource names from tool output rather than fabricating resource identifiers?",
        "Did the agent produce a tiered encryption plan distinguishing SSE-S3, AWS-managed KMS, and customer-managed KMS?",
        "Did the agent avoid fabricating CMK IDs, key policy templates, or encryption status details not verifiable from tool output?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
