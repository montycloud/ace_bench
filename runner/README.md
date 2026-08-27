# runner/

The evaluation pipeline: provisions a portable view of the AWS environment, runs scenarios
against any agent, scores results, judges fidelity, and generates reports.

- **`run.py`** — entry point; runs a scenario end to end against a chosen agent
- **`provisioner.py`** — reads deployed CloudFormation stack outputs → `benchmark/env_manifest.json`
- **`resolver.py`** — resolves gold-label `{{stack:OutputKey}}` handles to live resource IDs
- **`loader.py`** — loads scenario definitions; exposes agent-agnostic `task` + `output_contract`
- **`contracts.py`** — generic (unbranded) L1/L2 output contracts
- **`capture.py`** — parses an agent's raw response and tool-call trajectory
- **`evaluator.py`** — scores a run against gold labels (Tools/Answer/Safety/Output; Tools gated on observability)
- **`llm_judge.py`** — LLM-as-judge pass evaluating response fidelity (grounding/honesty)
- **`report.py`** — aggregate per-scenario reports across runs
- **`reeval.py`** — re-scores existing captured results without re-invoking the agent
- **`tools/catalog.py`** — the fixed, read-only AWS tool catalog offered to agents
- **`agents/`** — per-agent adapters behind the `AgentAdapter` interface (`toolloop`, `bedrock`)
- **`result/`** — JSON run outputs, one subfolder per agent (auto-populated by `run.py`)

## Typical flow

```bash
python -m runner.provisioner --region us-east-1                 # after deploy.sh
python -m runner.run <scenario_id> --agent toolloop --region us-east-1
```

See the root [README](../README.md) for the full quickstart.
