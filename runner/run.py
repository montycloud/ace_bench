"""
Runner — sends a scenario to the agent under evaluation, scores the response, saves results.

Usage:
    python -m runner.run <csv_id>        # run a scenario
    python -m runner.run --list          # list all available scenarios
    python -m runner.run --list-gold     # list scenarios with gold labels
    python -m runner.run --reeval        # re-score all saved runs against current gold
    python -m runner.run --rejudge       # re-run LLM judge on all saved runs
"""

import json
import time
import asyncio
import argparse
from datetime import datetime, timezone
from pathlib import Path

from runner.loader import load_scenario, load_gold, load_scenarios
from runner.capture import capture, print_capture
from runner.evaluator import evaluate, print_evaluation
from runner.agents import get_adapter, list_agents
from runner.resolver import load_resolver

RESULTS_DIR = Path(__file__).parent / "result"
INDEX_FILE = (
    Path(__file__).parent.parent / "dashboard" / "public" / "data" / "index.json"
)

MODEL_LABELS = {
    "toolloop": "toolloop/agent-under-test",
    "s3soa": "bedrock/s3soa",
    "soa": "bedrock/soa",
    "eoa": "bedrock/eoa",
    "poa": "bedrock/poa",
}
MODEL_LABEL = "toolloop/agent-under-test"  # default for the agnostic path


def _save_result(
    eval_result: dict,
    captured: dict,
    scenario: dict,
    gold: dict,
    prompt_sent: str,
    *,
    judge_result: dict | None = None,
    duration_s: float | None = None,
    agent: str = "toolloop",
):
    agent_dir = RESULTS_DIR / agent
    agent_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_id = scenario["csv_id"].replace("/", "__").replace("-", "_")
    run_id = f"{safe_id}__{agent}__{ts}"

    category = scenario["category"].split(",")[0].strip().lower().replace(" ", "_")

    record = {
        "id": run_id,
        "scenario_id": scenario["csv_id"],
        "scenario_name": scenario["scenario"],
        "category": category,
        "agent": agent,
        "model": MODEL_LABELS.get(agent, agent),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_score": eval_result["total_score"],
        "scores": eval_result["scores"],
        "details": eval_result["details"],
        "judge": judge_result,
        "prompt": {
            "version": scenario["prompt_version"],
            "system_context": scenario["prompt"].split("\n\n")[0],
            "objective_raw": scenario["objective_raw"],
            "objective_clean": scenario["objective_clean"],
            "full_prompt": prompt_sent,
        },
        "scenario": {
            "csv_id": scenario["csv_id"],
            "description": gold.get("description", ""),
            "objective": scenario["objective_raw"],
            "success_criteria": scenario.get("success_criteria", ""),
            "hard_fail": scenario.get("hard_fail", ""),
            "wafr_pillar": scenario.get("wafr_pillar", ""),
            "wafr_phase": scenario.get("wafr_phase", ""),
            "correct_resources": gold.get("correct_resources", []),
            "should_not_flag": gold.get("should_not_flag", []),
            "judge_criteria": gold.get("judge_criteria", []),
        },
        "tool_calls": captured.get("tool_calls", []),
        "response": captured["response"],
        "token_usage": captured["token_usage"],
        "duration_s": duration_s,
        "cost": {
            "note": "cost tracking depends on the agent under test",
        },
    }

    (agent_dir / f"{run_id}.json").write_text(json.dumps(record, indent=2))

    index = json.loads(INDEX_FILE.read_text()) if INDEX_FILE.exists() else {"runs": []}
    index["runs"].append(
        {
            "id": run_id,
            "scenario_id": scenario["csv_id"],
            "scenario_name": scenario["scenario"],
            "category": category,
            "timestamp": record["timestamp"],
            "total_score": eval_result["total_score"],
            "scores": eval_result["scores"],
            "has_judge": judge_result is not None,
            "model": MODEL_LABEL,
            "agent": agent,
        }
    )
    INDEX_FILE.write_text(json.dumps(index, indent=2))
    print(f"\n  [saved] {run_id}.json")


def reeval():
    """Re-score all saved runs against current gold labels without re-running the agent."""
    result_files = sorted(RESULTS_DIR.glob("*/*.json"))
    print(
        f"\n  Re-evaluating {len(result_files)} saved runs against current gold labels...\n"
    )

    updated_index = {"runs": []}

    for path in result_files:
        record = json.loads(path.read_text())
        csv_id = record["scenario_id"]

        try:
            gold = load_gold(csv_id)
        except Exception:
            gold = {}

        if not gold:
            updated_index["runs"].append(
                {
                    "id": record["id"],
                    "scenario_id": record["scenario_id"],
                    "scenario_name": record.get("scenario_name", ""),
                    "category": record.get("category", ""),
                    "timestamp": record["timestamp"],
                    "total_score": record["total_score"],
                    "scores": record["scores"],
                    "has_judge": record.get("judge") is not None,
                    "model": record.get("model", MODEL_LABEL),
                }
            )
            continue

        from runner.capture import _parse_response_json

        tool_calls_saved = record.get("tool_calls", [])
        tools_used = list(
            dict.fromkeys(tc["tool"] for tc in tool_calls_saved if tc.get("tool"))
        )
        parsed_json = _parse_response_json(record["response"])

        correct_resources = gold.get("correct_resources", [])
        found_in_response = []
        if parsed_json:
            reported_ids = [
                f.get("resource_id", "")
                for f in parsed_json.get("findings", [])
                if f.get("resource_id")
            ]
            found_in_response = [r for r in correct_resources if r in reported_ids]

        tool_outputs_text = " ".join(
            str(tc.get("output", "")) for tc in tool_calls_saved
        )
        found_in_tools = [r for r in correct_resources if r in tool_outputs_text]
        found_anywhere = list(set(found_in_response + found_in_tools))
        missed = [r for r in correct_resources if r not in found_anywhere]

        captured = {
            "scenario_id": csv_id,
            "tools_used": tools_used,
            "tool_calls": tool_calls_saved,
            "response": record["response"],
            "parsed_json": parsed_json,
            "found_in_response": found_in_response,
            "found_in_tools": found_in_tools,
            "found_anywhere": found_anywhere,
            "missed": missed,
            "raw_tool_results": [tc.get("output", "") for tc in tool_calls_saved],
            "token_usage": record.get("token_usage", {}),
        }
        # Historical saved runs use the legacy day2 tool trace — keep legacy tool
        # scoring so a label that gains an `expected_tools` field does not retroactively break.
        eval_result = evaluate(captured, gold, native_tools=False)

        record["total_score"] = eval_result["total_score"]
        record["scores"] = eval_result["scores"]
        record["details"] = eval_result["details"]
        if "scenario" not in record:
            record["scenario"] = {}
        record["scenario"]["correct_resources"] = gold.get("correct_resources", [])
        record["scenario"]["should_not_flag"] = gold.get("should_not_flag", [])
        record["scenario"]["judge_criteria"] = gold.get("judge_criteria", [])

        path.write_text(json.dumps(record, indent=2))

        updated_index["runs"].append(
            {
                "id": record["id"],
                "scenario_id": record["scenario_id"],
                "scenario_name": record.get("scenario_name", ""),
                "category": record.get("category", ""),
                "timestamp": record["timestamp"],
                "total_score": eval_result["total_score"],
                "scores": eval_result["scores"],
                "has_judge": record.get("judge") is not None,
                "model": record.get("model", MODEL_LABEL),
            }
        )

        scores = eval_result["scores"]
        t = eval_result["total_score"]
        print(
            f"  {t:.2f}  T={scores.get('tools',0):.1f} A={scores.get('answer',0):.1f} "
            f"S={scores.get('safety',0):.1f} O={scores.get('output',0):.1f}  "
            f"{record['id'][-30:]}"
        )

    INDEX_FILE.write_text(json.dumps(updated_index, indent=2))
    print(f"\n  Done. index.json rebuilt with {len(updated_index['runs'])} entries.")


def _has_existing_result(csv_id: str, agent: str) -> bool:
    """Check whether a saved result already exists for this scenario/agent pair."""
    safe_id = csv_id.replace("/", "__").replace("-", "_")
    agent_dir = RESULTS_DIR / agent
    if not agent_dir.exists():
        return False
    return any(agent_dir.glob(f"{safe_id}__{agent}__*.json"))


def run(csv_id: str, agent: str = "toolloop", skip_existing: bool = False, region: str = "us-east-1"):
    if skip_existing and _has_existing_result(csv_id, agent):
        print(f"\n  [skip] {csv_id} ({agent}) — result already exists")
        return None

    print(f"\n{'='*60}")
    print(f"  Scenario : {csv_id}")
    print(f"  Agent    : {agent}")
    print(f"{'='*60}")

    # ── build the agent adapter (agnostic dispatch — no per-agent branching) ──
    adapter = get_adapter(agent, region=region)

    # ── resolve gold labels against the live environment manifest ──
    resolver = load_resolver()
    env = resolver.manifest
    raw_gold = load_gold(csv_id)
    gold = resolver.resolve_gold(raw_gold) if raw_gold else {}

    scenario = load_scenario(csv_id)

    print(f"\n  Name     : {scenario['scenario']}")
    print(f"  Category : {scenario['category']}")
    print(f"  Level    : L{scenario['level']}")
    print(f"\n  Objective:\n    {scenario['objective_clean']}")

    if not gold:
        print("\n  [WARNING] No gold labels found — evaluation will be partial")
    if gold.get("_unresolved"):
        print(f"  [note] unresolved resource handles (fixture not deployed?): {gold['_unresolved']}")
    if not env and adapter.observable_tools and agent == "toolloop":
        print("\n  [WARNING] No env manifest — run `python -m runner.provisioner --region <r>` first")

    print(f"\n[Running agent...]\n")

    t0 = time.time()
    agent_input = adapter.build_input(scenario, gold, env)
    result = adapter.run(agent_input).to_capture_dict()
    elapsed = result.get("elapsed") or round(time.time() - t0, 1)
    prompt = agent_input.as_prompt()

    captured = capture(result, csv_id, gold)
    eval_result = evaluate(
        captured,
        gold,
        observable_tools=adapter.observable_tools,
        native_tools=getattr(adapter, "native_tools", True),
    )

    print_capture(captured)
    print(f"  Duration      : {elapsed}s")
    print_evaluation(eval_result)
    _save_result(
        eval_result, captured, scenario, gold, prompt, duration_s=elapsed, agent=agent
    )

    return eval_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_id", nargs="?", help="Scenario CSV ID to run")
    parser.add_argument(
        "--agent",
        default="toolloop",
        help="Agent to use: toolloop, s3soa, soa, eoa, poa (default: toolloop)",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region the fixtures were deployed to (default: us-east-1)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all scenarios with gold labels"
    )
    parser.add_argument(
        "--level", type=int, choices=[1, 2], help="Filter --all to L1 or L2 only"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip scenarios that already have a saved result for the chosen agent",
    )
    parser.add_argument("--list", action="store_true", help="List all scenarios")
    parser.add_argument(
        "--list-gold", action="store_true", help="List scenarios with gold labels"
    )
    parser.add_argument(
        "--reeval",
        action="store_true",
        help="Re-score all saved runs against current gold labels",
    )
    args = parser.parse_args()

    if args.all:
        scenarios = load_scenarios(level=args.level or 1) + (
            load_scenarios(level=2) if not args.level else []
        )
        with_gold = [s for s in scenarios if s["gold_path"]]
        # The toolloop suite excludes scenarios needing real usage history (cost /
        # rightsizing / savings) that a fresh CFN deploy cannot reproduce.
        if args.agent == "toolloop":
            skipped = [s for s in with_gold if not s["toolloop_runnable"]]
            with_gold = [s for s in with_gold if s["toolloop_runnable"]]
            if skipped:
                print(f"\n  [excluded from toolloop v1 — need usage history: {len(skipped)}]")
                for s in skipped:
                    print(f"    - {s['csv_id']}")
        print(f"\n  Running {len(with_gold)} scenarios with --agent {args.agent}...\n")
        for s in with_gold:
            try:
                run(s["csv_id"], agent=args.agent, skip_existing=args.skip_existing, region=args.region)
            except Exception as e:
                print(f"\n  [error] {s['csv_id']}: {e}")
    elif args.reeval:
        reeval()
    elif args.list or args.list_gold:
        scenarios = load_scenarios(level=1)
        print(f"\n{'─'*70}")
        for s in scenarios:
            has_gold = "✓ gold" if s["gold_path"] else "  ----"
            if args.list_gold and not s["gold_path"]:
                continue
            print(f"  {has_gold}  {s['csv_id']}")
            print(f"           {s['scenario']}")
        print(f"\n  Total: {len(scenarios)} scenarios")
    elif args.csv_id:
        run(args.csv_id, agent=args.agent, skip_existing=args.skip_existing, region=args.region)
    else:
        parser.print_help()
