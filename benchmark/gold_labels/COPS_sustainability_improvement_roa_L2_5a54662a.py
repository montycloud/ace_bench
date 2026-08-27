"""
Gold labels: Sustainability Improvement Roadmap
CSV ID: COPS-sustainability-improvement-roa-L2-5a54662a
Level: L2
WAFR resources: EC2 instances eligible for Graviton migration confirmed via get_saving_opportunities
"""

GOLD = {
    'csv_id': 'COPS-sustainability-improvement-roa-L2-5a54662a',

    'description': (
        "The agent should build a sustainability roadmap using Compute Optimizer recommendations "
        "(Graviton migration for EC2, gp3 for EBS) and storage lifecycle gaps as sustainability levers. "
        "The EC2 and EBS resources are confirmed via get_saving_opportunities. "
        "Carbon intensity data by region is not accessible."
    ),

    'correct_resources': [
        'i-01baa59f318a3c59e',
        'i-06286d41ae1218d5e',
        'i-0ee5fa3508cede8a2',
        'i-0aa58fe2d137a2f9f',
        'vol-028f30f6b745e2ae5',
        'vol-03fc1ecf1ea302655',
        'vol-0497bec1f1285d97f',
        'vol-05ced2e45c102a69e',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'get_saving_opportunities', 'params': {}, 'reason': 'Retrieve Compute Optimizer recommendations for Graviton/gp3 as sustainability levers'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate compute resource types for sustainability assessment'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand sustainability-related findings in assessment'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Carbon intensity data by AWS region is not accessible through available tools",
        "Power consumption metrics and carbon-per-request calculations require tooling outside current scope",
        "Managed service migration sustainability scoring requires application architecture data not available",
        "AWS Customer Carbon Footprint Tool data not accessible through current toolset",
    ],
    'judge_criteria': [
        "Did the agent use get_saving_opportunities to retrieve actual Graviton migration and gp3 upgrade opportunities as sustainability levers?",
        "Did the agent identify specific EC2 instance IDs and EBS volume IDs from tool output rather than fabricating resource names?",
        "Did the agent produce a sustainability roadmap scored by expected carbon/efficiency impact grounded in what tools surfaced?",
        "Did the agent acknowledge that carbon intensity by region, power consumption metrics, and carbon footprint data are not accessible through available tools?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
