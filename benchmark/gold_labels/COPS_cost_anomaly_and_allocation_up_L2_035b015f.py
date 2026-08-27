"""
Gold labels: Cost Anomaly and Allocation Uplift Across Business Units
CSV ID: COPS-cost-anomaly-and-allocation-up-L2-035b015f
Level: L2
Note: Cost Anomaly Detection and tag activation are account-level — no specific resource IDs.
  Only aggregate cost data is accessible through available tools.
"""

GOLD = {
    'csv_id': 'COPS-cost-anomaly-and-allocation-up-L2-035b015f',

    'description': (
        "The agent should identify cost anomaly detection gaps and tag allocation deficiencies "
        "from available tool data. No specific resource IDs exist for anomaly monitors — "
        "this is an account-level configuration gap. The agent should acknowledge what cost signals "
        "are accessible vs what requires additional tooling."
    ),

    'correct_resources': [],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of cost-related findings'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate resource types for tag coverage assessment'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Cost Anomaly Detection monitor status is not accessible through WAFR assessment tools",
        "Cost allocation tag activation status not surfaced by available tools",
        "CUR (Cost and Usage Report) data and BU chargeback report templates require Cost Explorer access not available in current toolset",
        "Linked account breakdown requires AWS Organizations access not available through assessment tools",
        "Service-level cost breakdown is not accessible through get_cost tool — only aggregate monthly totals",
    ],
    'judge_criteria': [
        "Did the agent correctly identify that Cost Anomaly Detection monitor status and tag activation are not accessible through available tools, and state this explicitly?",
        "Did the agent use available cost data (aggregate monthly spend, resource inventory) to ground its recommendations rather than fabricating anomaly monitor details?",
        "Did the agent produce a concrete enablement plan covering what it could recommend (anomaly monitor setup, mandatory tag keys) even without direct tool access to current state?",
        "Did the agent avoid fabricating specific anomaly monitor names, CUR report schemas, or BU chargeback details not present in tool output?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
