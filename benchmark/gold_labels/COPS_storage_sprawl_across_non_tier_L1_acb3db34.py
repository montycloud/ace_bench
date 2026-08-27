"""
Gold labels: Storage Sprawl Across Non-Tiered Buckets
CSV ID: COPS-storage-sprawl-across-non-tier-L1-acb3db34
Fixture: S3NonCompliant — buckets with no lifecycle policies or intelligent tiering
"""

GOLD = {
    'csv_id': 'COPS-storage-sprawl-across-non-tier-L1-acb3db34',

    'description': (
        "S3 charges for every GB stored. Without lifecycle policies, objects stay in the most expensive "
        "storage class (Standard) indefinitely — even old logs, archives, and data nobody accesses anymore. "
        "Lifecycle policies automatically transition objects to cheaper tiers (Infrequent Access, Glacier) "
        "after a set period, or delete them entirely. Buckets without these policies silently accumulate "
        "storage costs over time with no automatic cleanup. "
        "The agent should identify S3 buckets contributing to storage sprawl by lacking lifecycle policies."
    ),

    'correct_resources': [
        's3noncompliant-s3bucket1-vaeopnyvk0ru',
        's3noncompliant-s3bucket2-uaefqzdhl7fg',
        'wartestncs3bucketnc03-REDACTED-ACCOUNT-us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top resources/checks by findings count — S3 buckets without lifecycle policies surface here'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings status counts to understand scope of S3 lifecycle/tiering gaps'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate S3 resource types in assessment to identify buckets contributing to storage sprawl'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is missing S3 lifecycle policies that would auto-transition or expire objects (not just general storage cost concerns)?",
        "Did the agent identify specific S3 bucket names lacking lifecycle configuration?",
        "Did the agent recommend concrete lifecycle policy actions (e.g., transitioning to Infrequent Access or Glacier after N days, expiring old objects)?",
        "Did the agent avoid fabricating bucket names or lifecycle policy status not verifiable from tool output?",
    ],
}
