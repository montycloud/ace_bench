"""
Gold labels: Detective-Control Baseline Missing in Active Regions
CSV ID: COPS-detective-control-baseline-mis-L1-7c75d427
Fixture: VPCNonCompliant — VPC without GuardDuty/Config/SecurityHub properly enabled
Platform gap: Assessment returns 0 resources for GuardDuty/Config/SecurityHub checks — these
  services aren't surfaced as resource types in the WAFR assessment. vpc-0a9630bfd89f3d25c is
  aspirational and signals the platform gap to MontyCloud.
"""

GOLD = {
    'csv_id': 'COPS-detective-control-baseline-mis-L1-7c75d427',

    'description': (
        "AWS Config, GuardDuty, and Security Hub are foundational detective controls that continuously monitor "
        "your account for misconfigurations and threats. Config records every resource configuration change. "
        "GuardDuty uses machine learning to detect threats like unusual API calls or cryptocurrency mining. "
        "Security Hub aggregates findings from multiple services into a single security score. "
        "If any of these are disabled in active regions, you have blind spots — incidents happen and you only "
        "find out after the fact. The agent should identify regions where these detective controls are not enabled."
    ),

    'correct_resources': [
        # GuardDuty/Config/SecurityHub are not surfaced as named resource IDs in the WAFR assessment —
        # the platform returns account-level summary entries (REDACTED-ACCOUNT/us-east-1).
        # The agent's correct response is to identify the SERVICE gaps, not specific resource names.
        'REDACTED-ACCOUNT/us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top checks/resources — used to look for GuardDuty/Config/SecurityHub gaps'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate all resource types in assessment to check for detective control coverage'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings status counts to understand scope of detective control gaps'},
    ],
    'judge_criteria': [
        "Did the agent identify which specific detective controls are missing or not properly configured (GuardDuty, AWS Config, Security Hub)?",
        "Did the agent identify affected regions or scope — or, if tools could not surface specific resource IDs for detective controls, explicitly acknowledge that rather than fabricating service enablement status?",
        "Did the agent avoid fabricating GuardDuty detector IDs, Config recorder names, or Security Hub status details not verifiable from tool output?",
        "Did the agent avoid treating the absence of tool-visible resources as proof that detective controls are enabled?",
    ],
}
