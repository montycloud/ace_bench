"""
Re-evaluate saved run results against current gold labels without re-running the agent.

Usage:
    python -m runner.reeval              # re-eval all latest runs
    python -m runner.reeval <csv_id>     # re-eval one scenario
"""

import sys
import json
import glob
from pathlib import Path

from runner.loader    import load_gold, load_scenarios
from runner.evaluator import evaluate

RESULTS_DIR = Path(__file__).parent / 'result'
INDEX_FILE  = Path(__file__).parent.parent / 'dashboard' / 'public' / 'data' / 'index.json'


def _latest_per_scenario() -> dict[str, Path]:
    latest = {}
    for f in RESULTS_DIR.rglob('*.json'):
        try:
            d = json.loads(f.read_text())
            sid = d.get('scenario_id', '')
            if not sid:
                continue
            if sid not in latest or d['timestamp'] > json.loads(latest[sid].read_text())['timestamp']:
                latest[sid] = f
        except Exception:
            continue
    return latest


def reeval_file(path: Path) -> dict:
    record = json.loads(path.read_text())
    sid    = record['scenario_id']
    try:
        gold = load_gold(sid)
    except ValueError:
        print(f"  [skip] {sid} — scenario not found")
        return record

    if not gold:
        print(f"  [skip] {sid} — no gold labels")
        return record

    # rebuild captured dict from saved record
    captured = {
        'scenario_id':       sid,
        'response':          record.get('response', ''),
        'parsed_json':       record.get('details', {}).get('output', {}).get('valid_json') and
                             _extract_parsed_json(record),
        'tools_used':        list({tc['tool'] for tc in record.get('tool_calls', []) if tc.get('tool')}),
        'tool_calls':        record.get('tool_calls', []),
        'found_in_response': record['details']['answer'].get('found_in_response', []),
        'found_in_tools':    record['details']['answer'].get('found_in_tools', []),
        'found_anywhere':    (record['details']['answer'].get('found_in_response', []) +
                              record['details']['answer'].get('found_in_tools', [])),
        'missed':            record['details']['answer'].get('missed', []),
        'raw_tool_results':  [tc.get('output', '') for tc in record.get('tool_calls', [])],
        'token_usage':       record.get('token_usage', {}),
    }

    # re-parse JSON from response if needed
    if captured['parsed_json'] is None:
        from runner.capture import _parse_response_json
        captured['parsed_json'] = _parse_response_json(captured['response'])

    # re-run answer capture with updated gold
    from runner.capture import capture as _capture
    agent_result = {
        'response':         captured['response'],
        'tool_calls':       [{'name': tc['tool'], 'input': tc.get('input'), 'output': tc.get('output')}
                             for tc in record.get('tool_calls', [])],
        'raw_tool_results': captured['raw_tool_results'],
    }
    captured = _capture(agent_result, sid, gold)
    captured['scenario_id'] = sid

    # Historical saved runs use the legacy day2 trace — keep legacy tool scoring (see run.py reeval).
    new_eval = evaluate(captured, gold, native_tools=False)

    old_total = record['total_score']
    new_total = new_eval['total_score']
    delta     = new_total - old_total
    sign      = '+' if delta >= 0 else ''
    print(f"  {sid}")
    print(f"    {old_total:.0%} → {new_total:.0%}  ({sign}{delta:.0%})")

    # update record in place
    record['total_score'] = new_eval['total_score']
    record['scores']      = new_eval['scores']
    record['details']     = new_eval['details']
    record['prompt']['version'] = record['prompt'].get('version', '?') + '*'  # mark as re-evaled
    if gold.get('description') and isinstance(record.get('scenario'), dict):
        record['scenario']['description'] = gold['description']

    path.write_text(json.dumps(record, indent=2))
    return record


def _extract_parsed_json(record: dict):
    from runner.capture import _parse_response_json
    return _parse_response_json(record.get('response', ''))


def _update_index(records: list[dict]):
    index = json.loads(INDEX_FILE.read_text()) if INDEX_FILE.exists() else {'runs': []}
    by_id = {r['id']: r for r in index['runs']}
    for rec in records:
        rid = rec['id']
        if rid in by_id:
            by_id[rid]['total_score'] = rec['total_score']
            by_id[rid]['scores']      = rec['scores']
    index['runs'] = list(by_id.values())
    INDEX_FILE.write_text(json.dumps(index, indent=2))


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    latest = _latest_per_scenario()

    if target:
        # find the scenario ID
        matches = {sid: p for sid, p in latest.items() if target in sid}
        if not matches:
            print(f"No saved results found for: {target}")
            return
        to_run = matches
    else:
        to_run = latest

    print(f"\nRe-evaluating {len(to_run)} scenario(s) against current gold labels...\n")
    updated = []
    for sid, path in sorted(to_run.items()):
        updated.append(reeval_file(path))

    _update_index(updated)
    print(f"\nDone. {len(updated)} result(s) updated in place.")


if __name__ == '__main__':
    main()
