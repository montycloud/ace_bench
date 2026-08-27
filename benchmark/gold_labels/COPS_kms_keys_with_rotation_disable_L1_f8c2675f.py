"""
Gold labels: KMS Keys With Rotation Disabled and Unbounded Access
CSV ID: COPS-kms-keys-with-rotation-disable-L1-f8c2675f
Fixture: KMSCMKNonCompliant (not yet deployed — 2 KMS keys with rotation disabled, Principal:* policy)
  KMS (Key Management Service): AWS service for customer-managed encryption keys
  CMK (Customer Master Key): a KMS key you own and control — rotation means AWS generates a new key version annually
Note: LogMetricsNonCompliant stack also has a KMS key (1e007832-6f44-4c5c-bc87-6a9bdddf4d28) with rotation disabled
"""

GOLD = {
    'csv_id': 'COPS-kms-keys-with-rotation-disable-L1-f8c2675f',

    'description': (
        "AWS KMS customer-managed keys (CMKs) encrypt data across S3, RDS, Lambda, and other services. "
        "Key rotation automatically generates a new cryptographic key version each year — if a key is ever "
        "compromised, rotation limits how much historical data is at risk. Without rotation, the same key "
        "material is used indefinitely. A KMS key policy with Principal:* grants any AWS principal access "
        "to the key, effectively making encryption useless. "
        "The agent should identify KMS keys with rotation disabled and overly permissive key policies."
    ),

    # Resources are referenced by stable {{stack:OutputKey}} handles resolved against
    # benchmark/env_manifest.json at scoring time — never by account-specific IDs.
    'correct_resources': [
        '{{wafr-nc-kms:WartestkmsKeyId}}',    # KMSCMKNonCompliant — rotation disabled
        '{{wafr-nc-kms:WartestkmsKeyId1}}',   # KMSCMKNonCompliant — Principal:* key policy
    ],

    'should_not_flag': [
        '{{wafr-comp-kms:WartestkmsKeyId}}',  # KMSCMKCompliant — rotation enabled, scoped policy
    ],

    # Agent-agnostic, AWS-native tools from runner/tools/catalog.py. Scored only for
    # agents whose tool trace is observable (e.g. the toolloop adapter).
    'expected_tools': [
        {'tool': 'list_kms_keys', 'params': {}, 'reason': 'Enumerate customer-managed KMS keys in the account'},
        {'tool': 'get_kms_key_rotation', 'params': {'key_id': '{{wafr-nc-kms:WartestkmsKeyId}}'}, 'reason': 'Confirm automatic key rotation is disabled on the flagged key'},
        {'tool': 'get_kms_key_policy', 'params': {'key_id': '{{wafr-nc-kms:WartestkmsKeyId1}}'}, 'reason': 'Inspect the key policy for an over-permissive Principal:* grant'},
    ],

    'known_platform_gaps': [
        "KMSCMKNonCompliant fixture not yet deployed — dbc1e4f2-8170-42e7-8e60-0eee19653591 is not in the WAFR assessment; the agent should not fabricate this key ID",
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is KMS customer-managed keys with automatic key rotation disabled?",
        "Did the agent identify specific KMS key IDs — or, if tools could not surface specific key IDs, explicitly acknowledge that rather than fabricating key IDs?",
        "Did the agent also address the overly permissive key policy issue (Principal:* allowing any principal to use the key)?",
        "Did the agent avoid fabricating KMS key IDs (specifically the undeployed dbc1e4f2 KMSCMKNonCompliant key) or rotation/policy details not verifiable from tool output?",
    ],
}
