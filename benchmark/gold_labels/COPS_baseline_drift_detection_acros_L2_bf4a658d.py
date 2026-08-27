"""
Gold labels: Baseline-Drift Detection Across Environments
CSV ID: COPS-baseline-drift-detection-acros-L2-bf4a658d
Level: L2
Note: CloudFormation drift detection requires direct AWS API — not accessible through WAFR tools.
  WAFR findings surface resource-level compliance gaps which are the detectable drift signals.
"""

GOLD = {
    'csv_id': 'COPS-baseline-drift-detection-acros-L2-bf4a658d',

    'description': (
        "The agent should detect baseline drift by comparing WAFR compliance findings against expected "
        "compliant state. The drift signals available are the failing compliance checks across the "
        "known fixture resources. CloudFormation stack drift detection is a platform gap. "
        "The agent should not fabricate CFN drift diffs."
    ),

    'correct_resources': [
        's3noncompliant-s3bucket1-vaeopnyvk0ru',
        's3noncompliant-s3bucket2-uaefqzdhl7fg',
        'sg-0c9d922a6676b8021',
        'sg-07aebdd225b47ba16',
        'NCLambda-adminRole-us-east-1',
        'test-table-d4e9a170-2e6d-11f1-aa48-0afff185c25b',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top resources with compliance drift signals'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of compliance drift across resource types'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate all resource types to map against expected baseline'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "CloudFormation stack drift detection (describe-stack-resource-drifts) requires direct AWS API access not available through WAFR tools",
        "Baseline vs deployed diff at the CFN template level is not accessible — only resource-level compliance gaps are visible",
        "Historical configuration state for trend comparison requires AWS Config history not available through assessment tools",
    ],
    'judge_criteria': [
        "Did the agent use WAFR compliance findings as the proxy for baseline drift, surfacing real non-compliant resources from tool output?",
        "Did the agent avoid fabricating CloudFormation drift diffs, specific CFN template additions/removals, or AWS Config history data not accessible through available tools?",
        "Did the agent produce a drift remediation list grounded in real resource IDs and compliance check failures from tool output?",
        "Did the agent explicitly acknowledge that CFN-level drift detection requires tooling beyond what is available?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
