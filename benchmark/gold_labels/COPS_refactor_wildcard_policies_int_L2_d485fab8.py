"""
Gold labels: Refactor Wildcard Policies Into Scoped Workload Roles
CSV ID: COPS-refactor-wildcard-policies-int-L2-d485fab8
Level: L2
WAFR resources: NCLambda-adminRole-us-east-1 confirmed with Action:* Resource:* policy
"""

GOLD = {
    'csv_id': 'COPS-refactor-wildcard-policies-int-L2-d485fab8',

    'description': (
        "The agent should identify IAM roles with wildcard policies (Action:*) from WAFR findings "
        "and produce a scoped policy replacement plan. The LambdaNonCompliant fixture role "
        "NCLambda-adminRole-us-east-1 is confirmed in WAFR. The plan should propose least-privilege "
        "replacements grounded in what tools actually surface, not fabricated policy documents."
    ),

    'correct_resources': [
        'NCLambda-adminRole-us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top IAM resources with findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of IAM privilege violations'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Individual policy ARNs and their exact Action/Resource statements are not directly accessible through WAFR assessment tools — only check-level findings surface",
        "CloudTrail observed access patterns required for scoped policy generation are not accessible through available tools",
        "PermissionBoundary and aws:SourceVpce condition details require direct IAM API access",
    ],
    'judge_criteria': [
        "Did the agent identify NCLambda-adminRole-us-east-1 or the IAM wildcard policy check as the primary finding from tool output?",
        "Did the agent produce a scoped policy replacement plan grounded in actual WAFR findings rather than generic IAM advice?",
        "Did the agent avoid fabricating specific policy ARNs, CloudTrail access patterns, or condition keys not present in tool output?",
        "Did the agent explicitly acknowledge that detailed policy scoping (CloudTrail access history, exact action lists) requires tooling beyond what is available?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
