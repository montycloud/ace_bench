"""
Scenario-level aggregate report across all judged runs.

Usage:
    python -m runner.report <scenario_id>          # generate or update
    python -m runner.report <scenario_id> --force  # regenerate from scratch
    python -m runner.report --list                 # list scenarios with judged runs
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv()

JUDGE_MODEL = os.getenv(
    "ASF_JUDGE_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
JUDGE_REGION = "us-east-1"

RESULTS_DIR = Path(__file__).parent / "result"
REPORTS_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "data" / "reports"


def _safe_id(scenario_id: str) -> str:
    return scenario_id.replace("-", "_")


def _load_judged_runs(scenario_id: str) -> list[dict]:
    runs = []
    for path in sorted(RESULTS_DIR.rglob(f"{_safe_id(scenario_id)}__*.json")):
        rec = json.loads(path.read_text())
        if rec.get("judge") and not rec["judge"].get("error"):
            runs.append(rec)
    return sorted(runs, key=lambda r: r["timestamp"])


def _format_runs(runs: list[dict]) -> str:
    parts = []
    for run in runs:
        j = run["judge"]
        lines = [
            f"### Run: {run['id']}",
            f"Timestamp: {run['timestamp']}",
            f"Met: {j.get('met', '?')}/{j.get('total', '?')} criteria",
            "",
        ]
        for r in j.get("criteria_results", []):
            lines.append(f"[{'MET' if r.get('met') else 'NOT MET'}] {r['criterion']}")
            lines.append(f"  {r.get('finding', '')}")
        lines.append(f"\nOverall: {j.get('overall_comment', '')}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def _schema() -> str:
    return """{
  "summary": "one paragraph executive summary of the agent's overall performance across all runs",
  "criterion_breakdown": [
    {
      "criterion": "(exact criterion text)",
      "met_count": 3,
      "not_met_count": 1,
      "analysis": "2-3 sentences: pattern across runs, which specific run IDs failed and why, any inconsistency",
      "notable_run_ids": ["run_id_1"]
    }
  ],
  "recurring_failures": "What consistently goes wrong — specific criteria and run IDs",
  "trends": "Whether performance is improving, regressing, or stuck — reference run sequence and timestamps",
  "recommendations": "Concrete changes that would fix the recurring issues — specific to the agent's tool use, prompt handling, or output behaviour",
  "what_changed": null
}"""


def _generate_prompt(scenario: dict, gold: dict, runs: list[dict]) -> str:
    criteria_str = "\n".join(
        f"{i + 1}. {c}" for i, c in enumerate(gold.get("judge_criteria", []))
    )
    return f"""You are analysing multiple evaluation runs of a CloudOps AI agent on a specific scenario. Produce a comprehensive scenario-level report.

## Scenario
Name: {scenario.get("scenario", "")}
Category: {scenario.get("category", "")}
WAFR Pillar: {scenario.get("wafr_pillar", "")}

## Success Criteria
{scenario.get("success_criteria", "(not specified)")}

## Hard-Fail Conditions
{scenario.get("hard_fail", "(none specified)")}

## Evaluation Criteria
{criteria_str}

## All Judged Runs ({len(runs)} runs)

{_format_runs(runs)}

---

Be specific — reference run IDs when calling out notable instances. Identify patterns, not just individual failures.

Return a single valid JSON object with no markdown fences:
{_schema()}"""


def _update_prompt(
    scenario: dict, gold: dict, new_runs: list[dict], existing: dict
) -> str:
    criteria_str = "\n".join(
        f"{i + 1}. {c}" for i, c in enumerate(gold.get("judge_criteria", []))
    )
    return f"""You are updating an existing scenario-level report for a CloudOps AI agent with new evaluation runs.

## Scenario
Name: {scenario.get("scenario", "")}
Category: {scenario.get("category", "")}
WAFR Pillar: {scenario.get("wafr_pillar", "")}

## Success Criteria
{scenario.get("success_criteria", "(not specified)")}

## Hard-Fail Conditions
{scenario.get("hard_fail", "(none specified)")}

## Evaluation Criteria
{criteria_str}

## Existing Report (covers previous runs)
{json.dumps(existing, indent=2)}

## New Runs ({len(new_runs)} new)

{_format_runs(new_runs)}

---

Rewrite the full report incorporating all runs. Then fill in "what_changed" with an explicit description of what the new runs revealed — improvements, regressions, new failure modes, or confirmation of existing patterns. Reference specific run IDs.

Return a single valid JSON object with no markdown fences:
{_schema().replace('"what_changed": null', '"what_changed": "explicit description of what shifted in the new runs"')}"""


def generate(scenario_id: str, *, force: bool = False) -> dict:
    from runner.loader import load_gold, load_scenario

    scenario = load_scenario(scenario_id)
    gold = load_gold(scenario_id)

    if not gold.get("judge_criteria"):
        raise ValueError(f"No judge_criteria for {scenario_id}")

    runs = _load_judged_runs(scenario_id)
    if not runs:
        raise ValueError(
            f"No judged runs found for {scenario_id} — run llm_judge first"
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{_safe_id(scenario_id)}.json"

    existing = None
    if report_path.exists() and not force:
        existing = json.loads(report_path.read_text())

    if existing:
        included = set(existing.get("run_ids_included", []))
        new_runs = [r for r in runs if r["id"] not in included]
        if not new_runs:
            print("  No new runs since last report. Use --force to regenerate.")
            return existing
        prompt = _update_prompt(scenario, gold, new_runs, existing)
        prompt_type = "update"
        print(
            f"  Updating with {len(new_runs)} new run(s) (total judged: {len(runs)})..."
        )
    else:
        prompt = _generate_prompt(scenario, gold, runs)
        prompt_type = "generate"
        print(f"  Generating from {len(runs)} judged run(s)...")

    client = boto3.client("bedrock-runtime", region_name=JUDGE_REGION)
    response = client.converse(
        modelId=JUDGE_MODEL,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.1},
    )

    raw = response["output"]["message"]["content"][0]["text"].strip()
    json_text = re.sub(r"^```(?:json)?\s*", "", raw)
    json_text = re.sub(r"\s*```$", "", json_text.strip())
    parsed = json.loads(json_text)

    now = datetime.now(timezone.utc).isoformat()
    report = {
        "scenario_id": scenario_id,
        "scenario_name": scenario.get("scenario", ""),
        "category": scenario.get("category", ""),
        "wafr_pillar": scenario.get("wafr_pillar", ""),
        "generated_at": existing.get("generated_at", now) if existing else now,
        "updated_at": now,
        "run_ids_included": [r["id"] for r in runs],
        "total_runs": len(runs),
        "judge_model": JUDGE_MODEL,
        "prompt_type": prompt_type,
        "prompt": prompt,
        **parsed,
    }

    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Saved → {report_path.name}")
    return report


def _print_report(report: dict):
    print(f"\n{'=' * 62}")
    print(f"  {report.get('scenario_name', '')}")
    print(
        f"  {report.get('total_runs', 0)} judged runs  ·  updated {report.get('updated_at', '')[:10]}"
    )
    print(f"{'=' * 62}")

    print(f"\n  Summary\n  {'─' * 58}")
    print(f"  {report.get('summary', '')}\n")

    print(f"  Criterion Breakdown\n  {'─' * 58}")
    for cb in report.get("criterion_breakdown", []):
        met = cb.get("met_count", 0)
        total = met + cb.get("not_met_count", 0)
        print(f"\n  [{met}/{total}] {cb['criterion']}")
        print(f"  {cb.get('analysis', '')}")
        if cb.get("notable_run_ids"):
            print(f"  Notable runs: {', '.join(cb['notable_run_ids'])}")

    for section, label in [
        ("recurring_failures", "Recurring Failures"),
        ("trends", "Trends"),
        ("recommendations", "Recommendations"),
        ("what_changed", "What Changed"),
    ]:
        if report.get(section):
            print(f"\n  {label}\n  {'─' * 58}")
            print(f"  {report[section]}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scenario-level aggregate report")
    parser.add_argument("scenario_id", nargs="?", help="Scenario CSV ID")
    parser.add_argument("--force", action="store_true", help="Regenerate from scratch")
    parser.add_argument(
        "--list", action="store_true", help="List scenarios with judged runs"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate/update reports for all scenarios with judged runs",
    )
    parser.add_argument(
        "--save-prompts",
        action="store_true",
        help="Reconstruct and save prompts into existing reports — no LLM calls",
    )
    args = parser.parse_args()

    if args.save_prompts:
        from runner.loader import load_gold, load_scenario

        reports = sorted(REPORTS_DIR.glob("*.json"))
        print(f"\n  Saving prompts for {len(reports)} reports (no LLM calls)...\n")
        for path in reports:
            rep = json.loads(path.read_text())
            sid = rep["scenario_id"]
            try:
                scenario = load_scenario(sid)
                gold = load_gold(sid)
                runs = _load_judged_runs(sid)
                existing = rep if rep.get("prompt_type") == "update" else None
                if existing:
                    included = set(rep.get("run_ids_included", []))
                    new_runs = [r for r in runs if r["id"] not in included]
                    prompt = _update_prompt(scenario, gold, new_runs or runs, rep)
                else:
                    prompt = _generate_prompt(scenario, gold, runs)
                rep["prompt"] = prompt
                path.write_text(json.dumps(rep, indent=2))
                print(f"  saved  {path.stem[-55:]}")
            except Exception as e:
                print(f"  [error] {sid}: {e}")
        print("\n  Done.")

    elif args.all:
        by_scenario = defaultdict(int)
        for path in RESULTS_DIR.rglob("*.json"):
            rec = json.loads(path.read_text())
            if rec.get("judge") and not rec["judge"].get("error"):
                by_scenario[rec["scenario_id"]] += 1
        print(f"\n  Generating reports for {len(by_scenario)} scenarios...\n")
        for sid in sorted(by_scenario):
            print(f"  ── {sid}")
            try:
                report = generate(sid, force=args.force)
            except Exception as e:
                print(f"  [error] {e}")

    elif args.list:
        by_scenario = defaultdict(int)
        for path in RESULTS_DIR.rglob("*.json"):
            rec = json.loads(path.read_text())
            if rec.get("judge") and not rec["judge"].get("error"):
                by_scenario[rec["scenario_id"]] += 1
        print("\n  Scenarios with judged runs:\n")
        for sid, count in sorted(by_scenario.items()):
            rp = REPORTS_DIR / f"{_safe_id(sid)}.json"
            tag = "✓ report" if rp.exists() else "  ------"
            print(f"  {tag}  {count:2d} runs  {sid}")

    elif args.scenario_id:
        report = generate(args.scenario_id, force=args.force)
        _print_report(report)

    else:
        parser.print_help()
