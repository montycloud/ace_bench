# benchmark/gold_labels/

Gold labels used to score agent runs — one `.py` file per scenario, named
`{CSV_ID}.py` (e.g. `COPS_kms_keys_with_rotation_disable_L1_f8c2675f.py`).

Each file exports a `GOLD` dict:

| Field | Meaning |
|-------|---------|
| `csv_id` | Matches the scenario ID in `benchmark/scenarios/` |
| `description` | What the scenario tests and what the agent should identify |
| `correct_resources` | Resources the agent must flag — as **`{{stack:OutputKey}}` handles** |
| `should_not_flag` | Compliant resources the agent must NOT flag (safety check) |
| `expected_tools` | Agent-agnostic, AWS-native tools (from `runner/tools/catalog.py`) a well-behaved agent should call, with rationale |
| `judge_criteria` | Free-text criteria for the LLM judge |

## Account-agnostic resource handles

Gold labels **must not hardcode physical AWS IDs** (`sg-0abc…`, generated bucket names) —
those change in every customer account. Instead reference resources by a stable handle that
`runner/resolver.py` expands against `benchmark/env_manifest.json` at scoring time:

```python
'correct_resources': ['{{wafr-nc-kms:WartestkmsKeyId}}'],   # <stack>:<CloudFormation OutputKey>
'should_not_flag':   ['{{wafr-comp-kms:WartestkmsKeyId}}'],
'expected_tools': [
    {'tool': 'get_kms_key_rotation',
     'params': {'key_id': '{{wafr-nc-kms:WartestkmsKeyId}}'},
     'reason': 'Confirm automatic rotation is disabled'},
],
```

The handle is `{{<stack-name>:<OutputKey>}}` (or the short `{{<OutputKey>}}` when unique).
CloudFormation **output keys are template-defined and identical across accounts** — only the
values differ — so the same gold label scores correctly in any account once the manifest is
generated (`python -m runner.provisioner --region <r>`). Plain strings without `{{…}}` are
treated as literals and passed through unchanged.

`COPS_kms_keys_with_rotation_disable_L1_f8c2675f.py` is the reference example of the
agent-agnostic format written inline.

## The agnostic overlay

All **34 toolloop-runnable** scenarios are migrated to the agnostic format via a single
centralized file, [`agnostic_overlay.py`](agnostic_overlay.py), rather than editing every
label in place. `runner/loader.py::load_gold` merges the overlay's
`correct_resources` / `should_not_flag` / `expected_tools` on top of each base label; the
base keeps its legacy `expected_tool_calls` and original IDs (used by historical
re-eval), so the merge is non-breaking.

The overlay's `{{stack:OutputKey}}` handles are validated against the CFN template outputs
(all keys resolve), but should be re-checked against a **real manifest on first deploy** —
if `runner.run` prints `_unresolved` handles for a scenario, correct its OutputKey in the
overlay. The 6 cost/usage-history scenarios (`loader.TOOLLOOP_EXCLUSIONS`) are excluded and
keep their legacy labels only.

## Which tools to expect

`expected_tools` are drawn from the fixed read-only catalog in `runner/tools/catalog.py`
(e.g. `list_kms_keys`, `get_kms_key_rotation`, `describe_security_groups`,
`describe_flow_logs`, `describe_metric_filters`). The Tools pillar is scored only for agents
whose trace is observable (the `toolloop` adapter); it is skipped for black-box agents.

Consumed by [runner/evaluator.py](../../runner/evaluator.py) to score each run across the
Tools, Answer, Safety, and Output pillars.
