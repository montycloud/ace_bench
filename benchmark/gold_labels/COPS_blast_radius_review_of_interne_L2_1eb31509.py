"""
Gold labels: Blast-Radius Review of Internet-Facing Assets
CSV ID: COPS-blast-radius-review-of-interne-L2-1eb31509
Level: L2
WAFR resources: SGs open to 0.0.0.0/0, S3 public buckets, API Gateway stages confirmed
Note: ECR my-public-repo not deployed; NACLNonCompliant not deployed
"""

GOLD = {
    'csv_id': 'COPS-blast-radius-review-of-interne-L2-1eb31509',

    'description': (
        "The agent should trace internet-facing exposure across security groups, S3 public access, "
        "and API Gateway from WAFR findings, then assess downstream blast radius. "
        "Real exposures are confirmed in WAFR. ECR and NACL fixtures are not deployed."
    ),

    'correct_resources': [
        'sg-0c9d922a6676b8021',
        'sg-07aebdd225b47ba16',
        's3noncompliant-s3bucket1-vaeopnyvk0ru',
        's3noncompliant-s3bucket2-uaefqzdhl7fg',
        'xgkoo1ofg2/UnEncryptCache',
        'xgkoo1ofg2/UnEncryptCache1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Surface top internet-facing resources with findings'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Understand scope of public exposure findings'},
        {'tool': 'list_assessment_resources', 'params': {}, 'reason': 'Enumerate exposed resource types'},
        {'tool': 'list_questions', 'params': {}, 'reason': 'Retrieve WA Tool questions that must be answered as part of this L2 planning deliverable'},
        {'tool': 'answer_question', 'params': {}, 'reason': 'Submit WA Tool answers grounded in the assessment findings surfaced'},
    ],

    'known_platform_gaps': [
        "ECR my-public-repo not deployed — not present in WAFR assessment",
        "NACLNonCompliant fixture not deployed — NACL exposure not in WAFR",
        "Downstream blast radius graph (IAM trust chains, KMS key sharing) requires direct AWS API access beyond WAFR tools",
        "Public subnet routing and NAT configuration not accessible through assessment tools",
    ],
    'judge_criteria': [
        "Did the agent identify the real internet-facing exposures from tool output — specifically the open security groups, public S3 buckets, or unprotected API Gateway stages?",
        "Did the agent avoid fabricating ECR or NACL exposure findings that are not present in the WAFR assessment?",
        "Did the agent rate blast-radius severity for each identified exposure and sequence containment actions?",
        "Did the agent acknowledge that downstream blast radius graph construction (IAM trust chains, shared KMS keys) requires tooling beyond what is available?",
        "Did the agent retrieve WA Tool questions (list_questions) and submit answers via answer_question, grounded in the assessment findings it surfaced?",
    ],
}
