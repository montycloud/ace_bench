# local_test/ — offline end-to-end check

Runs the **real** ACE Bench ToolLoop pipeline (adapter loop → tool catalog dispatch →
capture → resolver → evaluator) against a **local Ollama model**, with a **mock AWS layer**
so you need no AWS account and no deployed fixtures. Use it to confirm the wiring works
before deploying real fixtures or evaluating a real agent.

```
run_local.py ──starts──> agent_bridge.py ──HTTP──> Ollama (tool-calling model)
     │                         (implements the ToolLoop wire contract)
     └── ToolLoopAdapter(session = MockSession)  ──> mock_aws.py (canned KMS fixtures)
             │
             └── capture → resolver (MOCK_MANIFEST) → evaluator → pillar scores
```

## Prerequisites
- Python deps installed (`pip install -r ../requirements.txt`)
- A local Ollama with a **tool-capable** model. Either:
  - **Host install:** `ollama serve` already running on `localhost:11434`, or
  - **Docker:** `docker compose up -d` in this folder, then
    `docker compose exec ollama ollama pull llama3.2:3b`

## Run
```bash
# from the repo root
python -m local_test.run_local
# or a specific scenario / model
OLLAMA_MODEL=llama3.2:3b python -m local_test.run_local COPS-kms-keys-with-rotation-disable-L1-f8c2675f
```

## What a passing run looks like
The harness drives the model through a multi-call tool loop, then prints pillar scores.
Scores reflect the **model's** quality, not the harness — a small 3B model will typically
score well on Answer (it finds the right keys from tool output) but poorly on Output
(malformed JSON) and Safety (over-flagging). That the scores *discriminate* is the point:
it proves capture, resolution against the manifest, and all four pillars are wired correctly.

## Files
| File | Role |
|------|------|
| `run_local.py` | One-command orchestrator (starts the bridge, runs a scenario, prints scores) |
| `agent_bridge.py` | Translates the ToolLoop contract ↔ Ollama `/api/chat` tool calling |
| `mock_aws.py` | Mock boto3 session + matching manifest (KMS compliant/non-compliant fixtures) |
| `docker-compose.yml` | Optional containerized Ollama |

---

## Full run against LocalStack (real CFN → fake AWS)

`run_local.py` uses a canned mock AWS layer. To exercise the **real** AWS path — actual
CloudFormation-deployed fixtures, the real provisioner manifest, real boto3 catalog calls —
against a fake AWS running in Docker (**LocalStack**), use:

```bash
bash local_test/run_mock_localstack.sh
# or a specific scenario:
bash local_test/run_mock_localstack.sh COPS-missing-default-encryption-on-L1-c65ec63a
```

It (1) starts a community LocalStack container on `:4566`, (2) deploys the
LocalStack-compatible fixture stacks via CloudFormation (`wafr-nc-dynamodb`, `wafr-nc-sqs`,
`wafr-comp-kms` — the templates without Lambda-backed custom resources), (3) runs
`runner.provisioner` to snapshot real stack outputs into `env_manifest.json`, and (4) drives
the `toolloop` adapter (Ollama model as the agent) through the read-only catalog against
LocalStack, then scores the result.

Requirements: Docker, the `skynet` conda env (with `boto3`, `awscli-local`, `localstack`),
and Ollama serving a tool-capable model (default `qwen3.5:9b`). LocalStack **Community** only
covers a subset of services — scenarios needing S3-express, WAF, Budgets, Compute Optimizer,
or Lambda-backed custom resources are not reproducible offline; their gold handles are
reported as `_unresolved` and scored as missed, which is the intended, honest behavior.

**Verified end to end** (Aug 2026): the DynamoDB PITR scenario scored Tools/Answer/Safety
100% (Output 0% — the small model emitted no valid JSON), and the multi-service encryption
scenario correctly found the deployed DynamoDB + SQS resources while reporting the undeployed
S3 fixtures as `_unresolved`.

This harness is for local verification only — it is not part of the scored benchmark.
