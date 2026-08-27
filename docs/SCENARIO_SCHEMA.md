# Scenario Schema — `benchmark/scenarios/CloudOps_Scenario_Master.csv`

`CloudOps_Scenario_Master.csv` (and the equivalent `CloudOps_Scenario_Pack.xlsx`,
the authoritative source) is the master registry of all 40 benchmark scenarios. One row per
scenario. Columns:

| Column | Meaning |
|--------|---------|
| `Category` | Top-level WAFR-aligned area, e.g. "Security, Risk & Compliance" |
| `Subcategory` | Narrower topic within the category, e.g. "IAM & Least Privilege" |
| `Scenario` | Human-readable scenario title |
| `Level` | Autonomy level `1` (L1 — assessment: identify non-compliant resources) or `2` (L2 — planning: produce a remediation roadmap). CCB defines five levels (L1–L5); only L1/L2 are implemented — see [AUTONOMY_LEVELS.md](AUTONOMY_LEVELS.md) |
| `Complexity` | Difficulty label, e.g. "Basic (Visibility & Discovery)" |
| `Expected Recommendation & Success Criteria` | Free-text description of what "success" looks like and what the agent should recommend |
| `Scenario ID (stable)` | Stable slug ID used to reference the scenario everywhere (`runner.run <id>`, result filenames). Matches the corresponding file in `benchmark/gold_labels/` |
| `Scenario Definition Version` | Semantic version of the scenario definition itself |
| `Benchmark Objective` | One-paragraph statement of intent, including the fixture/packet reference paths used by the internal MontyCloud environment |
| `WAFR Pillar Mapping` | Which AWS Well-Architected pillar(s) the scenario maps to (see `docs/reference/Framework_Sources.csv`) |
| `WAFR Phase Mapping` | Which WAFR review phase (e.g. "Prepare") |
| `Input Fixture Reference` | Pointers to the environment fixture / packet / CloudFormation template that provisions the resources under test |
| `Allowed Permissions` | What the agent is permitted to do while running the scenario (e.g. "AWS read-only; ticket create/update; no environment writes") |
| `Required Outputs` | Expected output file(s) and their shape, e.g. `report.json{Findings[],ImprovementPlan[],Tickets[]}` |
| `Verifier Strategy` | How the output is checked — currently always `structured-output` (validated by `runner/evaluator.py`) |
| `Hard-Fail Conditions` | Conditions that cause an automatic failure regardless of other scores (e.g. "any unapproved AWS write") |
| `Human Intervention Budget` | Max number of human-in-the-loop interactions allowed for the scenario |

## Relationship to `benchmark/gold_labels/*.py`

Each row here has a corresponding Python file in `benchmark/gold_labels/`, named
`{CATEGORY_PREFIX}_{truncated_title}_L{level}_{short_uuid}.py`. That file holds the **gold
labels** used for scoring: `correct_resources`, `should_not_flag`, `expected_tools`, and
`judge_criteria`. The CSV/xlsx describes *what the scenario is*; the Python file describes
*what a correct answer looks like*.
