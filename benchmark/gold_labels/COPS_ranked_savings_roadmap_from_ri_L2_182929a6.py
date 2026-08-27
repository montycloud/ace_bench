"""
Gold labels: Ranked Savings Roadmap From Rightsizing and Storage Tiering
CSV ID: COPS-ranked-savings-roadmap-from-ri-L2-182929a6
Level: L2
Fixture: ComputeOptimizerNonCompliant
Note: get_saving_opportunities returns real EC2/EBS IDs with savings figures.
  ElastiCache RI recommendations surface as type-level entries with no specific resource ID.
"""

GOLD = {
    'csv_id': 'COPS-ranked-savings-roadmap-from-ri-L2-182929a6',

    'description': (
        "The agent should use get_saving_opportunities to retrieve actual Compute Optimizer recommendations "
        "and produce a ranked savings roadmap. EC2 Graviton migration and EBS gp2→gp3 upgrades are "
        "verifiable from tool output. ElastiCache RI recommendations exist but have no specific resource ID — "
        "The agent should acknowledge this rather than fabricating IDs."
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
        {'tool': 'get_saving_opportunities', 'params': {}, 'reason': 'Purpose-built tool for Compute Optimizer recommendations — returns EC2/EBS resource IDs with savings amounts'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "ElastiCache Reserved Instance recommendations surface as type-level entries with no specific resource ID — "
        "The agent should describe the opportunity without fabricating an ID",
        "Service-level Cost Explorer breakdowns are not accessible through available tools — "
        "only aggregate monthly spend is available",
    ],
    'judge_criteria': [
        "Did the agent use get_saving_opportunities or equivalent to retrieve actual rightsizing recommendations from tool output?",
        "Did the agent identify specific EC2 instance IDs and EBS volume IDs with savings amounts as returned by tool output?",
        "Did the agent avoid fabricating resource IDs for recommendations (e.g. ElastiCache RIs) where no specific ID exists in tool output?",
        "Did the agent produce a ranked prioritization of savings opportunities with estimated savings amounts grounded in tool output?",
        "Did the agent explicitly acknowledge what cost signals were not accessible through available tools (e.g. service-level breakdown)?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
