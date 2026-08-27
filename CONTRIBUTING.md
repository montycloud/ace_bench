# Contributing

## Fixing a gold label

1. Edit the relevant file in `benchmark/gold_labels/{scenario_id}.py`.
2. Re-run the affected scenarios to confirm the scores change as expected:
   ```bash
   python -m runner.run <scenario_id> --agent <agent>
   ```

## Adding a new scenario

1. Add a row to `benchmark/scenarios/CloudOps_Scenario_Pack.xlsx` (source of truth) — see
   [docs/SCENARIO_SCHEMA.md](docs/SCENARIO_SCHEMA.md) for column meanings — and update
   `benchmark/scenarios/CloudOps_Scenario_Master.csv` to match.
2. Add a `benchmark/gold_labels/{scenario_id}.py` file with the gold labels:
   `correct_resources`, `should_not_flag`, `expected_tools`, and `judge_criteria`.
3. If the scenario needs new AWS resources, add a CloudFormation template under
   `benchmark/fixtures/compliant/` and/or `benchmark/fixtures/non_compliant/`
   (see [benchmark/fixtures/README.md](benchmark/fixtures/README.md)).
4. Run the scenario against at least one agent to confirm it evaluates correctly.

## Style

Match the style of the file you are editing. For the dashboard (`dashboard/`), run
`npm run lint` before committing frontend changes.
