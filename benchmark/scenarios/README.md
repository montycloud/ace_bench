# benchmark/scenarios/

Scenario registry for the benchmark.

- **`CloudOps_Scenario_Pack.xlsx`** — source of truth: all 40 scenario definitions
  (20 L1 assessment + 20 L2 planning) across AWS security, reliability, cost, governance,
  and observability. Loaded by `runner/loader.py`, which exposes an agent-agnostic `task`
  and `output_contract` per scenario (no agent name, no assessment ID, no account number).
- **`CloudOps_Scenario_Master.csv`** — flattened CSV export of the same scenarios.

See [docs/SCENARIO_SCHEMA.md](../../docs/SCENARIO_SCHEMA.md) for column/field definitions.
