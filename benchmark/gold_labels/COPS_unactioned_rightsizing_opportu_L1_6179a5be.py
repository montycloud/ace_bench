"""
Gold labels: Unactioned Rightsizing Opportunities From Compute Optimizer
CSV ID: COPS-unactioned-rightsizing-opportu-L1-6179a5be
Fixture: ComputeOptimizerNonCompliant (disables Compute Optimizer — no recommendations available)
Note: Despite fixture disabling Compute Optimizer, the agent found 8 real live recommendations via
  get_saving_opportunities (a tool not seen in other scenarios). 4 EC2 instances flagged for
  t3.micro→t4g.micro (Graviton) and 4 EBS volumes for gp2→gp3. The agent says 'recommendation',
  'compute optimizer', 'EC2' but not 'rightsizing' or 'utilization' specifically.
"""

GOLD = {
    'csv_id': 'COPS-unactioned-rightsizing-opportu-L1-6179a5be',

    'description': (
        "AWS Compute Optimizer continuously analyzes EC2 and EBS usage patterns and generates rightsizing "
        "recommendations — for example, migrating from an Intel t3.micro to a Graviton-based t4g.micro "
        "(same price, better performance) or upgrading an EBS gp2 volume to gp3 (cheaper and faster). "
        "When these recommendations sit unactioned for weeks, it represents pure avoidable waste. "
        "The agent should surface aged Compute Optimizer recommendations and propose a sequenced action plan "
        "prioritized by savings potential and implementation effort."
    ),

    'correct_resources': [
        # EC2 instances with Graviton migration recommendations
        'i-01baa59f318a3c59e',
        'i-06286d41ae1218d5e',
        'i-0ee5fa3508cede8a2',
        'i-0aa58fe2d137a2f9f',
        # EBS volumes with gp2→gp3 upgrade recommendations
        'vol-028f30f6b745e2ae5',
        'vol-03fc1ecf1ea302655',
        'vol-0497bec1f1285d97f',
        'vol-05ced2e45c102a69e',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'get_saving_opportunities', 'params': {}, 'reason': 'Purpose-built tool for Compute Optimizer recommendations — fetches EC2/EBS rightsizing data'},
    ],
    'judge_criteria': [
        "Did the agent use get_saving_opportunities or a similar tool to retrieve actual Compute Optimizer recommendations rather than guessing at recommendations?",
        "Did the agent identify specific EC2 instance IDs and/or EBS volume IDs with rightsizing recommendations, as returned by tool output?",
        "Did the agent explain the nature of the recommendations (e.g., instance type migration, storage class upgrade) rather than just noting a generic cost gap?",
        "Did the agent avoid fabricating instance IDs, volume IDs, or recommendation details not present in tool output?",
    ],
}
