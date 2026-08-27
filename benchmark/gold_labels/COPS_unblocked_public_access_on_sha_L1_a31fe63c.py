"""
Gold labels for: Unblocked Public Access on Shared Data Buckets
CSV ID: COPS-unblocked-public-access-on-sha-L1-a31fe63c
Fixture: S3NonCompliant stack (pre-deployed)
"""

GOLD = {
    'csv_id': 'COPS-unblocked-public-access-on-sha-L1-a31fe63c',

    'description': (
        "S3 has an account-level and bucket-level 'Block Public Access' setting that overrides any bucket "
        "policy or ACL that would make objects publicly readable. Without this setting, a single misconfigured "
        "bucket policy — added by a developer for testing or by mistake — can accidentally expose sensitive "
        "data to the entire internet. This has been the root cause of many high-profile data breaches. "
        "The agent should identify S3 buckets where Block Public Access is not fully enabled."
    ),

    'correct_resources': [
        's3noncompliant-s3bucket1-vaeopnyvk0ru',
        's3noncompliant-s3bucket2-uaefqzdhl7fg',
        'wartestncs3bucketnc03-REDACTED-ACCOUNT-us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top S3 resources by findings count — where specific bucket names surface from assessment data'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings status counts to understand scope of S3 Block Public Access failures'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is S3 Block Public Access being disabled or not fully configured (not just misconfigured bucket policies in isolation)?",
        "Did the agent identify specific S3 bucket names where Block Public Access is not enabled?",
        "Did the agent avoid fabricating bucket names or public access status details not verifiable from tool output?",
        "Did the agent avoid flagging unrelated S3 findings (e.g., encryption, versioning) as the primary public access issue?",
    ],
}
