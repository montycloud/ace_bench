"""
Gold labels: AWS Health Event Impact Mapping Across Workloads
CSV ID: COPS-aws-health-event-impact-mappin-L2-9bb50cb2
Level: L2
Note: AWS Health events are time-based — no persistent resource IDs.
  EventBridge and SNS routing config not accessible through WAFR tools.
"""

GOLD = {
    'csv_id': 'COPS-aws-health-event-impact-mappin-L2-9bb50cb2',

    'description': (
        "The agent should assess AWS Health event routing capability from available tool data. "
        "Active Health events may not be present — The agent should acknowledge this and produce "
        "a routing plan based on what resources it CAN enumerate (EC2, RDS, Lambda etc.) "
        "rather than fabricating event impact data."
    ),

    'correct_resources': [],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate resource types to scope Health event impact surface'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand overall assessment scope for impact mapping'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "AWS Health event data is not accessible through WAFR assessment tools — events are time-based not persistent resources",
        "EventBridge rule configuration and SNS routing targets not accessible through available tools",
        "Resource-to-workload tag mapping requires tag data not surfaced by WAFR assessment tools",
        "Blast-radius and customer impact estimation require application topology data not available",
    ],
    'judge_criteria': [
        "Did the agent correctly identify that AWS Health event data is not accessible through available tools and state this explicitly?",
        "Did the agent use available resource inventory to scope the potential impact surface rather than fabricating specific Health event data?",
        "Did the agent produce a routing plan recommendation (EventBridge → SNS → owner) even without direct access to current Health event state?",
        "Did the agent avoid fabricating specific Health event IDs, affected resource lists, or customer impact assessments not present in tool output?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
