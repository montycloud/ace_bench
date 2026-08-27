"""
Gold labels: Tag Compliance Drift on Revenue-Impacting Workloads
CSV ID: COPS-tag-compliance-drift-on-revenu-L1-532a6305
Fixtures: S3NonCompliant, DynamoDBNonCompliant, LambdaNonCompliant — resources with missing/inconsistent tags
Platform gap: Assessment tools have no tag compliance capability. The agent correctly identifies this
  and returns empty findings. correct_resources is empty — tag data is not accessible through any
  available tool, so there is nothing verifiable for the agent to identify.
"""

GOLD = {
    'csv_id': 'COPS-tag-compliance-drift-on-revenu-L1-532a6305',

    'description': (
        "AWS resource tags are key-value labels (e.g., Environment=prod, Owner=team-payments, CostCenter=42) "
        "used for cost attribution, ownership tracking, and automation. Resources missing required tags cannot "
        "be attributed to a team or workload in the monthly bill, making FinOps and chargeback impossible. "
        "Tag drift happens when resources are created without tags, or tags are removed over time. "
        "This scenario focuses on revenue-impacting workloads where ownership attribution is critical. "
        "The agent should identify resources with missing or inconsistent tags."
    ),

    'correct_resources': [],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Attempt to retrieve resource-level tag data from the WAFR assessment'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Check whether tag compliance findings are surfaced by the assessment'},
    ],

    'judge_criteria': [
        "Did the agent correctly identify that the WAFR assessment tools have no tag compliance capability, and explicitly acknowledge this rather than fabricating tag violation findings?",
        "If the agent could not find tag violations, did it clearly explain this is a platform/tooling gap (missing tag compliance checks) rather than reporting the account as compliant on tagging?",
        "Did the agent recommend a concrete path to implementing tag compliance (e.g., AWS Config tag compliance rules, Organizations tag policies)?",
        "Did the agent avoid fabricating resource IDs with tag violations not verifiable from tool output?",
    ],
}
