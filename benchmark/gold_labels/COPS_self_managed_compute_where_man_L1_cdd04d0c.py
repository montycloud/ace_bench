"""
Gold labels: Self-Managed Compute Where Managed Services Fit
CSV ID: COPS-self-managed-compute-where-man-L1-cdd04d0c
Fixture: LambdaNonCompliant — assesses whether Lambda functions are over-engineered
or whether self-managed compute (EC2) is used where Lambda/managed services would fit
"""

GOLD = {
    'csv_id': 'COPS-self-managed-compute-where-man-L1-cdd04d0c',

    'description': (
        "EC2 instances require you to manage patching, scaling, capacity planning, and OS maintenance. "
        "AWS Lambda and other managed services handle all of that automatically. When a workload is simple "
        "enough to run as a Lambda function — short-lived, event-driven, stateless — running it on EC2 "
        "instead adds unnecessary operational overhead and cost. "
        "The agent should identify cases where self-managed compute (EC2) is used where a managed serverless "
        "service like Lambda would be more appropriate."
    ),

    'correct_resources': [
        # EC2 instances that are candidates for migration to managed/serverless services
        'i-01baa59f318a3c59e',
        'i-0ee5fa3508cede8a2',
        'i-06286d41ae1218d5e',
        'i-0aa58fe2d137a2f9f',
    ],

    'should_not_flag': [
        # Lambda functions already exist and are not the subject of this scenario
        'nc-lambda-func-to-ad9c2340-2e6d-11f1-ba55-0e4a2ef2e90f',
        'nc-lambda-func-ad9c2340-2e6d-11f1-ba55-0e4a2ef2e90f',
    ],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top resources/checks to surface Lambda functions and assess managed vs self-managed compute usage'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings status counts to understand scope of sustainability/compute efficiency gaps'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate resource types to compare EC2 vs Lambda/managed service presence in account'},
    ],
    'judge_criteria': [
        "Did the agent identify specific compute resources (Lambda functions or EC2 workloads) that are candidates for migration to managed/serverless alternatives?",
        "Did the agent correctly avoid recommending EC2-to-Lambda migration for workloads that are clearly stateful, long-running, or otherwise unsuitable for Lambda?",
        "Did the agent avoid fabricating Lambda function names or EC2 instance details not present in tool output?",
        "Did the agent provide actionable reasoning for why the identified workloads are better suited to managed services (reduced operational overhead, auto-scaling, no patching)?",
    ],
}
