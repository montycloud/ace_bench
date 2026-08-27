"""
Gold labels: Preventive-Control Guardrail Uplift
CSV ID: COPS-preventive-control-guardrail-u-L2-5c06ddd1
Level: L2
WAFR resources: NCLambda-adminRole-us-east-1 is the primary resource needing guardrails
Note: SCP and permission boundary configuration not accessible through WAFR tools
"""

GOLD = {
    'csv_id': 'COPS-preventive-control-guardrail-u-L2-5c06ddd1',

    'description': (
        "The agent should identify gaps in preventive controls from WAFR findings and propose "
        "SCPs, permission boundaries, Config rules, and IAM Access Analyzer deployment. "
        "The wildcard IAM role is the primary confirmed finding. SCP and PB configuration "
        "details are not accessible through WAFR tools."
    ),

    'correct_resources': [
        'NCLambda-adminRole-us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top IAM/security resources with findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of preventive control gaps'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "SCP configuration requires AWS Organizations access not available through current tools",
        "AWS Config rule enablement status not directly surfaced through WAFR assessment tools",
        "IAM Access Analyzer findings require separate Security Hub or Access Analyzer API access",
        "Permission boundary attachment status for individual roles not accessible through WAFR tools",
    ],
    'judge_criteria': [
        "Did the agent identify the IAM wildcard policy finding from tool output as a primary gap requiring preventive guardrails?",
        "Did the agent propose a guardrail bundle (SCPs, permission boundaries, Config rules) grounded in the violations it found?",
        "Did the agent acknowledge that SCP configuration, Config rule status, and IAM Access Analyzer findings require tooling beyond what WAFR assessment tools provide?",
        "Did the agent avoid fabricating SCP document content, Config rule ARNs, or Access Analyzer findings not present in tool output?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
