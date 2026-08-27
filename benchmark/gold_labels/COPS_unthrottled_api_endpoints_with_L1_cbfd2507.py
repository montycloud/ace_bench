"""
Gold labels: Unthrottled API Endpoints Without Edge Protection
CSV ID: COPS-unthrottled-api-endpoints-with-L1-cbfd2507
Fixture: ApiGatewayNonCompliant (not yet deployed — API without throttling or WAF)
"""

GOLD = {
    'csv_id': 'COPS-unthrottled-api-endpoints-with-L1-cbfd2507',

    'correct_resources': [
        # ApiGatewayNonCompliant fixture stages confirmed in WAFR failing throttling + WAF checks
        'xgkoo1ofg2/UnEncryptCache',
        'xgkoo1ofg2/UnEncryptCache1',
        '/restapis/xgkoo1ofg2/stages/UnEncryptCache',
        '/restapis/xgkoo1ofg2/stages/UnEncryptCache1',
    ],

    'description': (
        "API Gateway exposes your backend services to the internet via HTTP endpoints. Without throttling "
        "limits, a single client or bad actor can flood your API with requests — crashing downstream services "
        "or running up Lambda costs. Without WAF (Web Application Firewall) integration, there's no protection "
        "against common attacks like SQL injection, XSS, or bot traffic. Edge-hardening means configuring "
        "throttling, WAF, and logging at every API stage. "
        "The agent should identify API Gateway stages missing throttling limits and edge protection."
    ),

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top resources/checks by findings count — API Gateway edge-hardening gaps surface here'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get findings status counts to understand scope of API Gateway throttling/WAF gaps'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate API Gateway resource types in assessment to identify unprotected stages'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is API Gateway stages missing throttling limits and/or WAF integration?",
        "Did the agent identify specific API Gateway resource names or stage identifiers — or, if tools could only return type summaries, explicitly acknowledge that rather than fabricating stage names?",
        "Did the agent address both throttling and WAF protection gaps (not just one of the two)?",
        "Did the agent avoid fabricating API Gateway resource identifiers or configuration details not present in tool output?",
    ],
}
