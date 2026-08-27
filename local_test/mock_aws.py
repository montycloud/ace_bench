"""
Mock AWS session for local, offline testing of the ToolLoop pipeline.

Lets us exercise the REAL code paths — adapter tool-loop, catalog dispatch,
capture, resolver, evaluator — with a real LLM (via Ollama) making real tool-call
decisions, without deploying any CloudFormation fixtures or touching an AWS account.

The canned data mirrors the KMSCMKNonCompliant / KMSCMKCompliant fixtures:
  nc-key-1  rotation DISABLED           (correct_resources)
  nc-key-2  rotation disabled + Principal:* key policy   (correct_resources)
  comp-key-1  rotation enabled, scoped policy            (should_not_flag)

`MOCK_MANIFEST` is the matching env manifest the resolver expands gold handles
against, so `{{wafr-nc-kms:WartestkmsKeyId}}` → "nc-key-1", etc.
"""

import json

MOCK_MANIFEST = {
    "schema_version": 1,
    "account_id": "000000000000",
    "region": "us-east-1",
    "stack_count": 2,
    "resource_count": 3,
    "stacks": [],
    "resources": [
        {"key": "wafr-nc-kms:WartestkmsKeyId", "output_key": "WartestkmsKeyId",
         "id": "nc-key-1", "stack": "wafr-nc-kms", "service": "KMS", "compliance": "non_compliant"},
        {"key": "wafr-nc-kms:WartestkmsKeyId1", "output_key": "WartestkmsKeyId1",
         "id": "nc-key-2", "stack": "wafr-nc-kms", "service": "KMS", "compliance": "non_compliant"},
        {"key": "wafr-comp-kms:WartestkmsKeyId", "output_key": "WartestkmsKeyId",
         "id": "comp-key-1", "stack": "wafr-comp-kms", "service": "KMS", "compliance": "compliant"},
    ],
}

_ROTATION = {"nc-key-1": False, "nc-key-2": False, "comp-key-1": True}
_POLICY = {
    "nc-key-2": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": "*", "Action": "kms:*", "Resource": "*"}]},
    "nc-key-1": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::000000000000:root"}, "Action": "kms:*", "Resource": "*"}]},
    "comp-key-1": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::000000000000:root"}, "Action": "kms:*", "Resource": "*"}]},
}


class _MockClient:
    def __init__(self, service):
        self.service = service

    # --- KMS ---
    def list_keys(self, **kw):
        return {"Keys": [{"KeyId": k, "KeyArn": f"arn:aws:kms:us-east-1:000000000000:key/{k}"}
                         for k in _ROTATION]}

    def get_key_rotation_status(self, KeyId=None, **kw):
        if KeyId not in _ROTATION:
            raise Exception(f"NotFoundException: key {KeyId}")
        return {"KeyRotationEnabled": _ROTATION[KeyId], "KeyId": KeyId}

    def get_key_policy(self, KeyId=None, PolicyName="default", **kw):
        if KeyId not in _POLICY:
            raise Exception(f"NotFoundException: key {KeyId}")
        return {"PolicyName": PolicyName, "Policy": json.dumps(_POLICY[KeyId])}

    def describe_key(self, KeyId=None, **kw):
        return {"KeyMetadata": {"KeyId": KeyId, "Enabled": True}}

    # --- STS ---
    def get_caller_identity(self, **kw):
        return {"Account": "000000000000", "Arn": "arn:aws:iam::000000000000:user/local-test"}

    # --- anything else: empty, so other catalog tools degrade gracefully ---
    def __getattr__(self, name):
        def _empty(**kw):
            return {}
        return _empty


class MockSession:
    """Drop-in stand-in for boto3.Session — only .client() is used by the catalog."""
    def __init__(self, region_name="us-east-1"):
        self.region_name = region_name

    def client(self, service, **kw):
        return _MockClient(service)
