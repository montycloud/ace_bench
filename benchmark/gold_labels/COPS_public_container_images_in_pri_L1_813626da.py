"""
Gold labels: Public Container Images in Private Pipelines
CSV ID: COPS-public-container-images-in-pri-L1-813626da
Fixture: ECRNonCompliant (not yet deployed — ECR repo with Principal:* pull policy)
  ECR (Elastic Container Registry): AWS managed Docker image registry — Principal:* means anyone can pull images
"""

GOLD = {
    'csv_id': 'COPS-public-container-images-in-pri-L1-813626da',

    'description': (
        "ECR (Elastic Container Registry) is AWS's managed Docker image registry. Container images in private "
        "pipelines should never be publicly accessible — they often contain proprietary application code, "
        "internal tooling, or dependencies that could help an attacker understand your systems. "
        "A repository policy with Principal:* means anyone on the internet can pull your images without "
        "authentication. The agent should identify ECR repositories with public access enabled or "
        "overly permissive pull policies."
    ),

    'correct_resources': [],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top ECR/container resources with findings to identify publicly exposed repositories'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings summary to understand ECR public access check failure distribution'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate ECR resources directly to get specific repository names from the assessment'},
    ],

    'known_platform_gaps': [
        "ECRNonCompliant fixture (my-public-repo) not yet deployed — not present in the WAFR assessment; the agent should not fabricate this repository name",
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is ECR repositories with public access enabled or overly permissive pull policies (Principal:*)?",
        "Did the agent correctly report that no public ECR repository was found in the WAFR assessment, rather than fabricating a repository name like 'my-public-repo'?",
        "Did the agent avoid fabricating ECR repository names or policy details not present in tool output?",
        "Did the agent avoid flagging non-ECR resources as container image violations?",
    ],
}
