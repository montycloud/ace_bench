"""
Gold labels: Missing Default Encryption on Shared Data Stores
CSV ID: COPS-missing-default-encryption-on-L1-c65ec63a
Fixtures: DynamoDBNonCompliant (SSE disabled), SQSNonCompliant (no encryption), SNSNonCompliant (no KMS)
  SSE (Server-Side Encryption): storage service encrypts data at rest using its own managed key
  KMS (Key Management Service): AWS service for customer-managed encryption keys — stronger than default SSE
"""

GOLD = {
    'csv_id': 'COPS-missing-default-encryption-on-L1-c65ec63a',

    'description': (
        "AWS data stores — DynamoDB tables, SQS queues, SNS topics, S3 buckets — should encrypt data at rest. "
        "Server-side encryption (SSE) means the storage service encrypts data automatically using a managed key. "
        "Stronger setups use customer-managed KMS keys, giving you control over key rotation and access policy. "
        "Without encryption, data is stored in plaintext — a serious risk if the underlying storage is ever accessed "
        "outside of normal AWS access controls. "
        "The agent should identify shared data stores with encryption disabled or using insufficiently strong key management."
    ),

    'correct_resources': [
        'test-table-d4e9a170-2e6d-11f1-aa48-0afff185c25b',
        'warf-test-sqs-queue-non-compliant',
        'war-test-a493',
        's3noncompliant-s3bucket1-vaeopnyvk0ru',
        's3noncompliant-s3bucket2-uaefqzdhl7fg',
        'wartestncs3bucketnc03-REDACTED-ACCOUNT-us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top resources by finding count to identify unencrypted data stores'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings summary to understand encryption check failures across DynamoDB, SQS, S3'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate resources directly to get specific resource IDs for unencrypted stores'},
    ],
    'judge_criteria': [
        "Did the agent identify encryption gaps across multiple data store types (DynamoDB, SQS, S3, or SNS) rather than just one service?",
        "Did the agent identify specific resource names (table names, queue names, bucket names) with encryption disabled or using insufficient key management?",
        "Did the agent avoid fabricating resource names not present in tool output?",
        "Did the agent distinguish between no encryption and weak encryption (default SSE vs customer-managed KMS keys)?",
    ],
}
