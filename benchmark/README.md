# benchmark/

The shareable benchmark itself: scenario definitions, gold labels, and the AWS fixtures used
to evaluate CloudOps agents.

- **`scenarios/`** — the scenario registry (40 CloudOps scenarios, source-of-truth spreadsheet + flattened CSV)
- **`gold_labels/`** — one Python file per scenario defining the correct resources, expected tool calls, and scoring criteria
- **`fixtures/`** — CloudFormation stacks that create the compliant/non-compliant AWS resources scenarios are evaluated against, plus the deploy/teardown script
- **[`COVERAGE.md`](COVERAGE.md)** — which CFN template backs which scenario, and which scenarios we **cannot** check from a fresh deploy (26 checkable · 8 account-level · 6 excluded)

See the root [README](../README.md) and [docs/SCENARIO_SCHEMA.md](../docs/SCENARIO_SCHEMA.md) for how these pieces fit together.
