"""
Gold labels: Over-Privileged Roles with Wildcard Actions
CSV ID: COPS-over-privileged-roles-with-wil-L1-77c958c4
Fixture: LambdaNonCompliant (NCLambda-adminRole-us-east-1 has Action:* Resource:*)

Note: The agent's WAFR tools return check names not specific role names for IAM resources.
The check "Ensure AWS IAM Policies Allow Only the Required Privileges for Each Role"
is what appears in the assessment findings. correct_resources reflects this.
"""

GOLD = {
    'csv_id': 'COPS-over-privileged-roles-with-wil-L1-77c958c4',

    'description': (
        "IAM roles define what actions AWS services and code can perform. A role with Action:* (wildcard) "
        "in its policy grants unlimited permissions — any code running under that role can create, delete, "
        "or modify anything in the account. The principle of least privilege requires granting only the "
        "specific permissions needed, nothing more. Wildcard policies are a critical misconfiguration "
        "that turns a compromised Lambda function or EC2 instance into a full account takeover. "
        "The agent should identify IAM roles or policies with overly broad wildcard action grants."
    ),

    'correct_resources': [
        # LambdaNonCompliant fixture role confirmed in WAFR — has Action:* Resource:* policy
        'NCLambda-adminRole-us-east-1',
    ],

    'should_not_flag': [],

    'expected_tool_calls': [
        {'tool': 'list_assessment_top_entities', 'params': {}, 'reason': 'Find top checks/resources by findings count — IAM privilege checks surface here'},
        {'tool': 'get_findings_summary', 'params': {}, 'reason': 'Get overall findings status to understand scope of IAM privilege violations'},
    ],
    'judge_criteria': [
        "Did the agent identify that the issue is IAM roles or policies with wildcard actions (Action:* or overly broad permissions) violating least privilege?",
        "Did the agent identify specific IAM role or policy names — or, if tools could not surface role names, explicitly acknowledge that rather than fabricating names?",
        "Did the agent avoid fabricating IAM role names, policy ARNs, or permission details not verifiable from tool output?",
        "Did the agent recommend scoping down permissions to least privilege (specifying exact actions and resources needed rather than wildcards)?",
    ],
}
