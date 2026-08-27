"""
Gold labels: Point-in-Time Recovery Disabled on Transactional Tables
CSV ID: COPS-point-in-time-recovery-disable-L1-952c1416
Fixture: DynamoDBNonCompliant (PITR disabled on test table)
  PITR (Point-In-Time Recovery): DynamoDB feature that keeps a continuous 35-day backup — lets you restore to any second in that window

Note: The agent's WAFR tools cannot surface specific DynamoDB table names — they return
aggregate counts and check titles. The response contains PITR/backup question titles
from the assessment. correct_resources reflects what actually appears in the agent's output.
"""

GOLD = {
    'csv_id': 'COPS-point-in-time-recovery-disable-L1-952c1416',

    'description': (
        "DynamoDB Point-in-Time Recovery (PITR) maintains a continuous backup of your table for 35 days, "
        "letting you restore to any second in that window. Without PITR, if data is accidentally deleted, "
        "corrupted by a bug, or modified by a bad deployment, recovery depends entirely on manual snapshots — "
        "which may not exist or may be hours old. For transactional tables storing orders, payments, or "
        "user data, PITR is the safety net that prevents data loss from becoming a business incident. "
        "The agent should identify DynamoDB tables with PITR disabled."
    ),

    'correct_resources': [
        # All 4 DynamoDB tables confirmed in WAFR failing "Enable DynamoDB table point-in-time recovery"
        'test-table-d4e9a170-2e6d-11f1-aa48-0afff185c25b',  # DynamoDBNonCompliant fixture table
        'mybookstore-Cart',
        'mybookstore-Books',
        'mybookstore-Orders',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top DynamoDB resources by finding count to identify tables with PITR disabled'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings summary to understand backup/PITR check failure scope across the assessment'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'List WAFR reliability pillar questions to find the PITR/backup question and its choices'},
        {'tool': 'get_question', 'params': {}, 'reason': 'Get full question detail including choices and improvement plan for the backup/PITR question'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is DynamoDB Point-in-Time Recovery (PITR) being disabled on transactional tables?",
        "Did the agent identify specific DynamoDB table names — or, if tools could not surface table names, explicitly acknowledge that limitation rather than fabricating table names?",
        "Did the agent explain the recovery capability PITR provides (continuous 35-day backup, restore to any second in that window)?",
        "Did the agent avoid fabricating DynamoDB table names or PITR status details not present in tool output?",
    ],
}
