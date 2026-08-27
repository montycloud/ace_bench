"""
Gold labels: Executive WAFR Review — Six-Pillar Summary
CSV ID: COPS-executive-wafr-review-six-pill-L2-614af9b6
Level: L2
Note: The WAFR assessment has 313 Critical/High findings and 1,276 total failures across
  all six pillars. The agent can surface pillar-level finding counts and top entities.
  The executive summary should reflect actual assessment data, not report PENDING status.
"""

GOLD = {
    'csv_id': 'COPS-executive-wafr-review-six-pill-L2-614af9b6',

    'description': (
        "The agent should produce an executive WAFR summary across all six pillars using "
        "get_findings_summary, list_assessment_top_entities, and related tools to surface "
        "actual finding counts and severity distributions. The assessment is NOT pending — "
        "it has hundreds of findings. The 90-day roadmap should prioritize by pillar risk."
    ),

    'correct_resources': [],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get finding counts and severity distribution across all pillars'},
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top resources and checks for executive-level risk callouts'},
        {'tool': 'get_assessment', 'params': {}, 'reason': 'Get assessment metadata and overall status'},
        {'tool': 'get_findings_summary', 'params': {'summary_type': 'severity_breakdown'}, 'reason': 'Retrieve the severity breakdown needed for the six-pillar executive summary, not just a generic findings call'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "Pillar-weighted risk scores are not directly computed by tools — The agent must derive "
        "relative risk from finding counts and severity distributions",
        "Executive HTML artifact generation is not possible through available tools",
    ],
    'judge_criteria': [
        "Did the agent produce a six-pillar summary covering all WAFR pillars with actual finding data from tool output — NOT report the assessment as PENDING or unanswered?",
        "Did the agent surface actual finding counts or severity distributions per pillar grounded in tool output?",
        "Did the agent produce a 90-day roadmap with prioritized actions tied to the highest-risk findings?",
        "Did the agent acknowledge what it could not produce (e.g. HTML artifact, exact pillar scores) rather than fabricating them?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
