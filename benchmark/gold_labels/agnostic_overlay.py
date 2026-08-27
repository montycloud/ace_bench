"""
Agent-agnostic overlay for the gold labels.

Each base gold label under benchmark/gold_labels/ still carries its original
`correct_resources` (physical IDs from the original internal account) and legacy
`expected_tool_calls` (day2 tools) — kept intact for re-scoring historical runs.
This overlay layers the **agent-agnostic** versions of
three fields on top, and `runner.loader.load_gold` merges them in:

    correct_resources  →  {{stack:OutputKey}} handles resolved against the manifest
    should_not_flag    →  compliant {{...}} handles (where a clear counterpart exists)
    expected_tools     →  AWS-native tools from runner/tools/catalog.py

Only keys present in an entry override the base; everything else (description,
judge_criteria, …) is untouched.

⚠️  Resource handles are INFERRED from each scenario's fixture mapping and the CFN
    template Outputs. They must be validated against a real manifest on first deploy
    (`python -m runner.provisioner`): if a scenario reports `_unresolved` handles,
    correct the OutputKey here. Tool lists are high-confidence and need no deploy.

The 6 cost/usage-history scenarios (see loader.TOOLLOOP_EXCLUSIONS) are intentionally
absent — they are excluded from the toolloop suite and keep their legacy labels.
"""

# Common tool bundles (names from runner/tools/catalog.py)
_S3_PUB = [
    {'tool': 'list_s3_buckets', 'reason': 'Enumerate buckets in the account'},
    {'tool': 'get_s3_public_access', 'reason': 'Check Block Public Access on each bucket'},
]
_S3_ENC = [
    {'tool': 'list_s3_buckets', 'reason': 'Enumerate buckets in the account'},
    {'tool': 'get_s3_encryption', 'reason': 'Check default encryption on each bucket'},
]
_KMS = [
    {'tool': 'list_kms_keys', 'reason': 'Enumerate customer-managed KMS keys'},
    {'tool': 'get_kms_key_rotation', 'reason': 'Confirm automatic rotation status'},
    {'tool': 'get_kms_key_policy', 'reason': 'Inspect key policy for over-permissive grants'},
]
_SG = [{'tool': 'describe_security_groups', 'reason': 'Inspect inbound rules for 0.0.0.0/0 exposure'}]
_NACL = [{'tool': 'describe_network_acls', 'reason': 'Inspect NACL rules for over-permissive entries'}]
_VPC_FLOW = [
    {'tool': 'describe_vpcs', 'reason': 'Enumerate VPCs'},
    {'tool': 'describe_flow_logs', 'reason': 'Detect VPCs without flow logging'},
]
_LAMBDA = [
    {'tool': 'list_lambda_functions', 'reason': 'Enumerate Lambda functions'},
    {'tool': 'get_lambda_function', 'reason': 'Inspect DLQ / timeout configuration'},
]
_LOGS = [{'tool': 'describe_log_groups', 'reason': 'Inspect log group retention/encryption'}]
_METRIC = [{'tool': 'describe_metric_filters', 'reason': 'Inspect CloudWatch Logs metric filters'}]
_ALARMS = [{'tool': 'describe_cloudwatch_alarms', 'reason': 'Inspect alarms and their SNS actions'}]
_SQS = [
    {'tool': 'list_sqs_queues', 'reason': 'Enumerate SQS queues'},
    {'tool': 'get_sqs_queue_attributes', 'reason': 'Inspect encryption / redrive policy'},
]
_DDB = [{'tool': 'describe_dynamodb_table', 'reason': 'Inspect PITR / encryption'}]
_ECR = [
    {'tool': 'describe_ecr_repositories', 'reason': 'Inspect scan-on-push / tag immutability'},
    {'tool': 'get_ecr_repository_policy', 'reason': 'Detect public repository policy'},
]
_APIGW = [
    {'tool': 'list_api_gateways', 'reason': 'Enumerate REST APIs'},
    {'tool': 'get_api_gateway_stages', 'reason': 'Inspect throttling / cache encryption per stage'},
]
_BUDGETS = [{'tool': 'describe_budgets', 'reason': 'Inspect budgets and notification thresholds'}]
_IAM = [{'tool': 'list_iam_roles', 'reason': 'Detect roles with wildcard (Action:*) policies'}]


OVERLAY = {
    # ── L1 assessment ────────────────────────────────────────────────────────
    'COPS-unblocked-public-access-on-sha-L1-a31fe63c': {
        'correct_resources': ['{{wafr-nc-s3:S3Bucket1Name}}', '{{wafr-nc-s3:S3Bucket2Name}}', '{{wafr-nc-s3:S3Bucket3Arn}}'],
        'expected_tools': _S3_PUB,
    },
    'COPS-over-privileged-roles-with-wil-L1-77c958c4': {
        'correct_resources': ['{{wafr-nc-lambda:FailingLambdaExecRole}}'],
        'expected_tools': _IAM,
    },
    'COPS-unrestricted-inbound-access-on-L1-6235afe3': {
        'correct_resources': ['{{wafr-nc-vpc:SecurityGroupID1}}', '{{wafr-nc-vpc:SecurityGroupID2}}'],
        'should_not_flag': ['{{wafr-nc-securitygroup:DefaultSecurityGroupId}}'],
        'expected_tools': _SG,
    },
    'COPS-over-permissive-nacl-rules-acr-L1-ab47360a': {
        'correct_resources': ['{{wafr-nc-nacl:NACLID1}}', '{{wafr-nc-nacl:NACLID2}}'],
        'should_not_flag': ['{{wafr-comp-nacl:NACLID}}'],
        'expected_tools': _NACL,
    },
    'COPS-missing-default-encryption-on-L1-c65ec63a': {
        'correct_resources': ['{{wafr-nc-dynamodb:DynamoDBTableId}}', '{{wafr-nc-sqs:MyQueueName}}',
                              '{{wafr-nc-s3:S3Bucket1Name}}', '{{wafr-nc-s3:S3Bucket2Name}}', '{{wafr-nc-s3:S3Bucket3Arn}}'],
        'expected_tools': _S3_ENC + _SQS + _DDB,
    },
    'COPS-kms-keys-with-rotation-disable-L1-f8c2675f': {
        'correct_resources': ['{{wafr-nc-kms:WartestkmsKeyId}}', '{{wafr-nc-kms:WartestkmsKeyId1}}'],
        'should_not_flag': ['{{wafr-comp-kms:WartestkmsKeyId}}'],
        'expected_tools': _KMS,
    },
    'COPS-lambda-functions-without-dead-L1-5e6f89f2': {
        'correct_resources': ['{{wafr-nc-lambda:FailingLambdaArn}}', '{{wafr-nc-lambda:TimeoutLambdaArn}}', '{{wafr-nc-lambda:HelloWorldFunction2Arn}}'],
        'expected_tools': _LAMBDA,
    },
    'COPS-missing-detective-metric-filte-L1-de40af00': {
        'correct_resources': ['{{wafr-nc-logmetrics:NonMFASignInLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:ConfigChangesLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:S3ChangesLogsMetricFilterNC}}'],
        'expected_tools': _METRIC,
    },
    'COPS-missing-flow-log-visibility-on-L1-42611021': {
        'correct_resources': ['{{wafr-nc-vpc:VPCID}}'],
        'expected_tools': _VPC_FLOW,
    },
    'COPS-critical-metrics-without-alarm-L1-b35f5df1': {
        'correct_resources': ['{{wafr-nc-logmetrics:NonMFASignInLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:ConfigChangesLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:S3ChangesLogsMetricFilterNC}}'],
        'expected_tools': _ALARMS + _METRIC,
    },
    'COPS-detective-control-baseline-mis-L1-7c75d427': {
        # account-level detective control gap — no single fixture resource
        'correct_resources': [],
        'expected_tools': _METRIC,
    },
    'COPS-cloudwatch-log-groups-without-L1-fedcd002': {
        'correct_resources': ['{{wafr-nc-cloudwatch:LogGroupName}}'],
        'expected_tools': _LOGS,
    },
    'COPS-point-in-time-recovery-disable-L1-952c1416': {
        'correct_resources': ['{{wafr-nc-dynamodb:DynamoDBTableId}}'],
        'expected_tools': _DDB,
    },
    'COPS-public-container-images-in-pri-L1-813626da': {
        'correct_resources': ['{{wafr-nc-ecr:ECRRepositoryId}}'],
        'expected_tools': _ECR,
    },
    'COPS-spend-budgets-without-notifica-L1-573baf91': {
        # BudgetsNonCompliant exposes no resource outputs — account-level check
        'correct_resources': [],
        'expected_tools': _BUDGETS,
    },
    'COPS-storage-sprawl-across-non-tier-L1-acb3db34': {
        'correct_resources': ['{{wafr-nc-s3:S3Bucket1Name}}', '{{wafr-nc-s3:S3Bucket2Name}}', '{{wafr-nc-s3:S3Bucket3Arn}}'],
        'expected_tools': [{'tool': 'list_s3_buckets', 'reason': 'Enumerate buckets to assess storage sprawl'}],
    },
    'COPS-tag-compliance-drift-on-revenu-L1-532a6305': {
        'correct_resources': [],
        'expected_tools': [{'tool': 'list_s3_buckets', 'reason': 'Enumerate resources to assess tag coverage'}],
    },
    'COPS-unthrottled-api-endpoints-with-L1-cbfd2507': {
        'correct_resources': ['{{wafr-nc-apigateway:apiGatewayId}}', '{{wafr-nc-apigateway:ApiGatewayStageId}}',
                              '{{wafr-nc-apigateway:apiGatewayStageCacheNonEncryptId}}'],
        'expected_tools': _APIGW,
    },

    # ── L2 planning ──────────────────────────────────────────────────────────
    'COPS-audit-evidence-readiness-postu-L2-92fd3942': {
        'correct_resources': ['{{wafr-nc-logmetrics:NonMFASignInLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:ConfigChangesLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:S3ChangesLogsMetricFilterNC}}'],
        'expected_tools': _METRIC + _LOGS,
    },
    'COPS-aws-health-event-impact-mappin-L2-9bb50cb2': {
        'correct_resources': [],
        'expected_tools': [{'tool': 'list_lambda_functions', 'reason': 'Enumerate workloads for impact mapping'}],
    },
    'COPS-baseline-drift-detection-acros-L2-bf4a658d': {
        'correct_resources': ['{{wafr-nc-s3:S3Bucket1Name}}', '{{wafr-nc-s3:S3Bucket2Name}}',
                              '{{wafr-nc-vpc:SecurityGroupID1}}', '{{wafr-nc-vpc:SecurityGroupID2}}',
                              '{{wafr-nc-lambda:FailingLambdaExecRole}}', '{{wafr-nc-dynamodb:DynamoDBTableId}}'],
        'expected_tools': _S3_PUB + _SG + _IAM + _DDB,
    },
    'COPS-blast-radius-review-of-interne-L2-1eb31509': {
        'correct_resources': ['{{wafr-nc-vpc:SecurityGroupID1}}', '{{wafr-nc-vpc:SecurityGroupID2}}',
                              '{{wafr-nc-s3:S3Bucket1Name}}', '{{wafr-nc-s3:S3Bucket2Name}}',
                              '{{wafr-nc-apigateway:ApiGatewayStageId}}'],
        'expected_tools': _SG + _S3_PUB + _APIGW,
    },
    'COPS-executive-wafr-review-six-pill-L2-614af9b6': {
        'correct_resources': [],
        'expected_tools': _S3_PUB + _KMS + _SG,  # broad sweep across pillars
    },
    'COPS-incident-readiness-mapping-for-L2-7b2bcfef': {
        'correct_resources': ['{{wafr-nc-logmetrics:NonMFASignInLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:ConfigChangesLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:S3ChangesLogsMetricFilterNC}}'],
        'expected_tools': _ALARMS + _METRIC,
    },
    'COPS-kms-rotation-and-key-policy-ha-L2-5983bf47': {
        'correct_resources': ['{{wafr-nc-kms:WartestkmsKeyId}}', '{{wafr-nc-kms:WartestkmsKeyId1}}'],
        'should_not_flag': ['{{wafr-comp-kms:WartestkmsKeyId}}'],
        'expected_tools': _KMS,
    },
    'COPS-multi-account-portfolio-health-L2-31144309': {
        'correct_resources': [],
        'expected_tools': _S3_PUB,
    },
    'COPS-network-tiering-and-egress-con-L2-c4df527d': {
        'correct_resources': ['{{wafr-nc-vpc:VPCID}}', '{{wafr-nc-vpc:SecurityGroupID1}}', '{{wafr-nc-vpc:SecurityGroupID2}}'],
        'expected_tools': _VPC_FLOW + _SG,
    },
    'COPS-observability-baseline-uplift-L2-637c29d9': {
        'correct_resources': ['{{wafr-nc-logmetrics:NonMFASignInLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:ConfigChangesLogsMetricFilterNC}}',
                              '{{wafr-nc-logmetrics:S3ChangesLogsMetricFilterNC}}'],
        'expected_tools': _METRIC + _LOGS + _ALARMS,
    },
    'COPS-preventive-control-guardrail-u-L2-5c06ddd1': {
        'correct_resources': ['{{wafr-nc-lambda:FailingLambdaExecRole}}'],
        'expected_tools': _IAM,
    },
    'COPS-refactor-wildcard-policies-int-L2-d485fab8': {
        'correct_resources': ['{{wafr-nc-lambda:FailingLambdaExecRole}}'],
        'expected_tools': _IAM,
    },
    'COPS-rto-and-rpo-convergence-across-L2-76e47be0': {
        'correct_resources': ['{{wafr-nc-dynamodb:DynamoDBTableId}}'],
        'expected_tools': _DDB,
    },
    'COPS-serverless-event-path-reliabil-L2-ffc06f96': {
        'correct_resources': [],
        'expected_tools': _LAMBDA + _SQS,
    },
    'COPS-unify-encryption-posture-acros-L2-34cc7d74': {
        'correct_resources': ['{{wafr-nc-s3:S3Bucket1Name}}', '{{wafr-nc-s3:S3Bucket2Name}}', '{{wafr-nc-s3:S3Bucket3Arn}}',
                              '{{wafr-nc-dynamodb:DynamoDBTableId}}', '{{wafr-nc-sqs:MyQueueName}}'],
        'expected_tools': _S3_ENC + _DDB + _SQS,
    },
    'COPS-wafr-critical-and-high-finding-L2-e24003d9': {
        'correct_resources': [],
        'expected_tools': _S3_PUB + _KMS + _SG,  # surface findings across services
    },
}
