"""
Gold labels: RTO and RPO Convergence Across Critical Data Stores
CSV ID: COPS-rto-and-rpo-convergence-across-L2-76e47be0
Level: L2
WAFR resources: DynamoDB tables confirmed failing PITR check in WAFR
"""

GOLD = {
    'csv_id': 'COPS-rto-and-rpo-convergence-across-L2-76e47be0',

    'description': (
        "The agent should identify DynamoDB tables without PITR enabled from WAFR findings and produce "
        "an RTO/RPO convergence plan. All four DynamoDB tables are confirmed failing the PITR check. "
        "S3 versioning and replication status are not directly accessible through WAFR tools."
    ),

    'correct_resources': [
        'test-table-d4e9a170-2e6d-11f1-aa48-0afff185c25b',
        'mybookstore-Cart',
        'mybookstore-Books',
        'mybookstore-Orders',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top DynamoDB resources failing PITR checks'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of backup and recovery gaps'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Find WAFR reliability questions covering PITR and backup, and retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "S3 versioning and cross-region replication status not directly accessible through WAFR assessment tools",
        "Actual backup test history and demonstrable recovery capability require direct AWS API access",
        "RDS is not present in this account — do not fabricate RDS recovery findings",
        "Declared vs demonstrable RTO/RPO comparison requires workload-level documentation not available in WAFR tools",
    ],
    'judge_criteria': [
        "Did the agent identify the DynamoDB tables from tool output that are failing the PITR check?",
        "Did the agent produce an RTO/RPO convergence plan covering the data stores it could verify from tool output?",
        "Did the agent avoid fabricating RDS findings or S3 versioning status not present in tool output?",
        "Did the agent acknowledge that demonstrable recovery capability (backup test history, actual RTO measurement) requires tooling beyond what is available?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
