"""
Gold labels: WAFR Critical and High Finding Triage Sprint Plan
CSV ID: COPS-wafr-critical-and-high-finding-L2-e24003d9
Level: L2
Note: The WAFR assessment has 313 Critical/High findings and 1,276 total failures.
  The agent must use get_findings_summary and list_assessment_top_entities to surface these —
  NOT report the assessment as PENDING/incomplete which is a tool usage failure.
"""

GOLD = {
    'csv_id': 'COPS-wafr-critical-and-high-finding-L2-e24003d9',

    'description': (
        "The WAFR assessment contains hundreds of Critical and High findings across all six pillars. "
        "The agent must use the right tools to surface them — get_findings_summary, list_assessment_top_entities, "
        "list_assessment_resources. Reporting the assessment as PENDING or 0/57 questions answered is a "
        "tool usage failure, not a platform gap. The sprint plan should triage findings by severity and pillar."
    ),

    'correct_resources': [],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get Critical/High finding counts by pillar and severity'},
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top resources and checks with most failures for sprint prioritization'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate resource types with findings to scope the sprint plan'},
        {'tool': 'get_findings_summary', 'params': {'summary_type': 'severity_breakdown'}, 'reason': 'Retrieve the Critical/High severity breakdown needed to build the triage sprint plan, not just a generic findings call'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Individual resource-level remediation details (exact config changes needed) may require "
        "direct AWS API access beyond what WAFR assessment tools surface",
    ],
    'judge_criteria': [
        "Did the agent use get_findings_summary or equivalent tools to surface actual Critical and High findings — NOT report the assessment as PENDING or incomplete?",
        "Did the agent identify findings across multiple WAFR pillars grounded in tool output rather than fabricating pillar-level status?",
        "Did the agent produce a structured sprint plan with prioritized remediation items tied to specific findings from tool output?",
        "Did the agent avoid fabricating specific finding IDs, check titles, or resource names not present in tool output?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
