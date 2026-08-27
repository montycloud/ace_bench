"""
Capture and structure the agent's response for evaluation.

Takes the raw output from the agent adapter and extracts:
  - final response text
  - parsed JSON output (findings[], improvement_plan[], summary)
  - tool calls (name, input, output)
  - resources found in findings[].resource_id
"""

import re
import json
from datetime import datetime


def _parse_response_json(response: str) -> dict | None:
    """Extract and parse the JSON block from the agent's response."""
    # try to find a ```json ... ``` block first
    match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # try to find a bare { ... } block
    match = re.search(r'(\{.*\})', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def capture(agent_result: dict, scenario_id: str, gold: dict = None) -> dict:
    response         = agent_result.get('response', '')
    tool_calls       = agent_result.get('tool_calls', [])
    raw_tool_results = agent_result.get('raw_tool_results', [])

    tools_used = list(dict.fromkeys(
        t['name'] for t in tool_calls if t.get('name')
    ))

    # parse structured JSON from the agent's response
    parsed_json = _parse_response_json(response)

    # extract resource_ids from findings[]
    correct_resources = (gold or {}).get('correct_resources', [])
    found_in_response = []
    found_in_tools    = []

    if parsed_json:
        # L1: check findings[].resource_id
        findings = parsed_json.get('findings', [])
        reported_ids = [f.get('resource_id', '') for f in findings if f.get('resource_id')]
        found_in_response = [r for r in correct_resources if r in reported_ids]

    # also scan full response text — catches L2 schema where IDs appear in free-text fields
    found_in_response = list(dict.fromkeys(
        found_in_response + [r for r in correct_resources if r in response]
    ))

    # scan tool results for resource names (tool data is unstructured)
    all_tool_text  = ' '.join(str(r) for r in raw_tool_results)
    found_in_tools = [r for r in correct_resources if r in all_tool_text]

    found_anywhere = list(set(found_in_response + found_in_tools))
    missed         = [r for r in correct_resources if r not in found_anywhere]

    est_tokens = len(response.split()) * 4 // 3

    return {
        'scenario_id':       scenario_id,
        'timestamp':         datetime.utcnow().isoformat(),
        'response':          response,
        'parsed_json':       parsed_json,
        'tools_used':        tools_used,
        'tool_calls':        [
            {
                'tool':   t.get('name', ''),
                'input':  t.get('input'),
                'output': t.get('output'),
            }
            for t in tool_calls
        ],
        'found_in_response': found_in_response,
        'found_in_tools':    found_in_tools,
        'found_anywhere':    found_anywhere,
        'missed':            missed,
        'raw_tool_results':  raw_tool_results,
        'token_usage': {
            'estimated': est_tokens,
            'note':      'estimated from response length; exact count not available via WebSocket',
        },
    }


def print_capture(captured: dict):
    print(f"\n── Capture: {captured['scenario_id']} ──\n")
    print(f"  Tools used    : {', '.join(captured['tools_used']) or 'none'}")
    print(f"  Tool calls    : {len(captured['tool_calls'])}")
    json_ok = '✓' if captured.get('parsed_json') else '✗ (no valid JSON)'
    print(f"  JSON output   : {json_ok}")
    print(f"  Found in resp : {captured['found_in_response']}")
    print(f"  Found in tools: {captured['found_in_tools']}")
    print(f"  Missed        : {captured['missed']}")
    print(f"  Est. tokens   : {captured['token_usage']['estimated']}")
