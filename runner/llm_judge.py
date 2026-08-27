"""
LLM-as-judge evaluator for agent trajectories.

Reads judge_criteria from the gold label and evaluates the full trajectory
(tool calls + outputs + response) against each criterion, returning structured
findings per criterion and an overall qualitative comment.

Usage:
    python -m runner.llm_judge <run_id>          # judge a specific saved run by ID
    python -m runner.llm_judge <path/to/run.json> # judge a specific file
    python -m runner.llm_judge --all              # judge every saved run that has gold labels
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv()

JUDGE_MODEL = os.getenv(
    "ASF_JUDGE_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
JUDGE_REGION = "us-east-1"


def _format_tool_calls(tool_calls: list[dict]) -> str:
    if not tool_calls:
        return "(no tool calls recorded)"

    parts = []
    for i, tc in enumerate(tool_calls, 1):
        tool = tc.get("tool", "(unknown)")
        inputs = tc.get("inputs", tc.get("input", {}))
        output = tc.get("output", "")

        output_str = str(output) if output else "(no output)"

        parts.append(
            f"### Tool Call {i}: {tool}\n"
            f"Inputs: {json.dumps(inputs, indent=2)}\n"
            f"Output:\n{output_str}"
        )

    return "\n\n".join(parts)


def _build_prompt(
    scenario: dict, gold: dict, tool_calls: list[dict], response: str
) -> str:
    criteria = gold.get("judge_criteria", [])
    correct_resources = gold.get("correct_resources", [])
    should_not_flag = gold.get("should_not_flag", [])
    known_platform_gaps = gold.get("known_platform_gaps", [])

    criteria_numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(criteria))

    resources_str = (
        "\n".join(f"- {r}" for r in correct_resources)
        if correct_resources
        else "(none — tools may not surface specific resource IDs for this scenario)"
    )

    should_not_str = (
        "\n".join(f"- {r}" for r in should_not_flag)
        if should_not_flag
        else "(none specified)"
    )

    gaps_str = (
        "\n".join(f"- {g}" for g in known_platform_gaps)
        if known_platform_gaps
        else "(none — all relevant data should be accessible through available tools)"
    )

    tool_calls_str = _format_tool_calls(tool_calls)

    return f"""You are evaluating a CloudOps AI agent on a compliance assessment scenario. Analyse the quality of the agent's investigation and response.

## Scenario
Name: {scenario.get("scenario", "")}
Category: {scenario.get("category", "")}
WAFR Pillar: {scenario.get("wafr_pillar", "")}

## What Success Looks Like
{scenario.get("success_criteria", "(not specified)")}

## Hard-Fail Conditions
{scenario.get("hard_fail", "(none specified)")}

## Known Correct Resources (ground truth confirmed in WAFR assessment)
{resources_str}

## Known Platform Gaps (things the agent structurally cannot access — do NOT penalise for these)
{gaps_str}

## Resources That Should NOT Be Flagged
{should_not_str}

---

## Agent's Tool Calls and Full Outputs
{tool_calls_str}

---

## Agent's Final Response
{response}

---

## Evaluation Instructions

For each criterion below, write a concise factual finding that describes exactly what the agent did or did not do — citing specific evidence from the tool calls or response above. Do not speculate.

Important:
- If tools structurally cannot surface specific resource IDs (returning type summaries or aggregate counts), credit the agent for explicitly acknowledging that rather than penalising it.
- If the agent invents resource names, check IDs, or configuration details not present in tool output, say so explicitly in the finding.

Criteria:
{criteria_numbered}

Return a single valid JSON object with no markdown fences:
{{
  "criteria_results": [
    {{
      "criterion": "(copy the criterion text exactly as written above)",
      "met": true,
      "finding": "one to two sentences of factual observation citing specific evidence from the tool output or the agent's response"
    }}
  ],
  "overall_comment": "two to three sentences: what the agent got right, what it missed, and the primary failure mode if any"
}}

"met" is true if the answer to the criterion question is yes based on the evidence, false otherwise."""


def judge(
    scenario: dict,
    gold: dict,
    tool_calls: list[dict],
    response: str,
    *,
    model: str = JUDGE_MODEL,
) -> dict:
    """
    Run LLM-as-judge on an agent trajectory.

    Args:
        scenario:   scenario dict from loader (must include success_criteria, hard_fail, wafr_pillar)
        gold:       gold label dict (must include judge_criteria, correct_resources, should_not_flag)
        tool_calls: list of tool call dicts with 'tool', 'inputs'/'input', 'output' keys
        response:   The agent's full final response text
        model:      Claude model ID to use for judging

    Returns:
        dict with keys: scenario_id, criteria_results (criterion + finding), overall_comment,
        known_correct_resources, should_not_flag, judge_model, timestamp
    """
    if not gold.get("judge_criteria"):
        return {
            "error": "No judge_criteria in gold label — cannot judge this scenario",
            "scenario_id": gold.get("csv_id", ""),
        }

    client = boto3.client("bedrock-runtime", region_name=JUDGE_REGION)
    prompt = _build_prompt(scenario, gold, tool_calls, response)

    response_body = client.converse(
        modelId=model,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 2048, "temperature": 0.1},
    )

    usage = response_body.get("usage", {})
    raw = response_body["output"]["message"]["content"][0]["text"].strip()
    json_text = re.sub(r"^```(?:json)?\s*", "", raw)
    json_text = re.sub(r"\s*```$", "", json_text.strip())
    parsed = json.loads(json_text)

    criteria = parsed.get("criteria_results", [])
    met = sum(1 for r in criteria if r.get("met"))
    input_tok = usage.get("inputTokens", 0)
    output_tok = usage.get("outputTokens", 0)

    return {
        "scenario_id": gold.get("csv_id", ""),
        "scenario_name": scenario.get("scenario", ""),
        "category": scenario.get("category", ""),
        "wafr_pillar": scenario.get("wafr_pillar", ""),
        "judge_model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "criteria_results": criteria,
        "met": met,
        "total": len(criteria),
        "overall_comment": parsed.get("overall_comment", ""),
        "known_correct_resources": gold.get("correct_resources", []),
        "should_not_flag": gold.get("should_not_flag", []),
        "known_platform_gaps": gold.get("known_platform_gaps", []),
        "prompt": prompt,
        "token_usage": {
            "input": input_tok,
            "output": output_tok,
            "total": input_tok + output_tok,
        },
    }


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

RESULTS_DIR = Path(__file__).parent / "result"
INDEX_FILE = (
    Path(__file__).parent.parent / "dashboard" / "public" / "data" / "index.json"
)


def _resolve_path(run_id_or_path: str) -> Path:
    """Accept a run ID (stem), a partial match, or a full file path."""
    p = Path(run_id_or_path)
    if p.exists():
        return p
    # try as stem anywhere under RESULTS_DIR (agent subfolders)
    exact = sorted(RESULTS_DIR.rglob(f"{run_id_or_path}.json"))
    if len(exact) == 1:
        return exact[0]
    # partial match — find files whose name contains the string
    matches = sorted(RESULTS_DIR.rglob(f"*{run_id_or_path}*.json"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = "\n  ".join(m.stem for m in matches)
        raise SystemExit(f"Ambiguous — {len(matches)} matches:\n  {names}")
    raise SystemExit(f"No saved run found matching: {run_id_or_path}")


def _print_result(result: dict):
    criteria = result.get("criteria_results", [])
    met = sum(1 for r in criteria if r.get("met"))
    total = len(criteria)

    print(f"\n  {'─' * 60}")
    print(
        f"  Judge: {result.get('judge_model', '')}  ·  {result.get('scenario_name', '')}"
    )
    print(f"  Score: {met}/{total} criteria met")
    print(f"  {'─' * 60}")
    for i, r in enumerate(criteria, 1):
        print(f"\n  {i}. {r['criterion']}")
        finding = r.get("finding", "")
        if finding:
            words, line = finding.split(), ""
            for word in words:
                if len(line) + len(word) + 1 > 72:
                    print(f"       {line}")
                    line = word
                else:
                    line = f"{line} {word}".lstrip()
            if line:
                print(f"       {line}")
    comment = result.get("overall_comment", "")
    if comment:
        print(f"\n  Overall: {comment}")
    tok = result.get("token_usage", {})
    if tok:
        print(
            f"\n  Tokens: {tok.get('input', 0):,} in  {tok.get('output', 0):,} out  ({tok.get('total', 0):,} total)"
        )


def _rebuild_index():
    updated = {"runs": []}
    for path in sorted(RESULTS_DIR.rglob("*.json")):
        rec = json.loads(path.read_text())
        j = rec.get("judge") or {}
        updated["runs"].append(
            {
                "id": rec["id"],
                "scenario_id": rec["scenario_id"],
                "scenario_name": rec.get("scenario_name", ""),
                "category": rec.get("category", ""),
                "timestamp": rec["timestamp"],
                "total_score": rec["total_score"],
                "scores": rec["scores"],
                "has_judge": bool(j),
                "judge_met": j.get("met"),
                "judge_total": j.get("total"),
                "model": rec.get("model", ""),
                "agent": rec.get("agent", ""),
            }
        )
    INDEX_FILE.write_text(json.dumps(updated, indent=2))


def _judge_file(path: Path):
    from runner.loader import load_gold, load_scenario

    record = json.loads(path.read_text())
    csv_id = record["scenario_id"]

    gold = load_gold(csv_id)
    scenario = load_scenario(csv_id)

    if not gold.get("judge_criteria"):
        raise SystemExit(f"No judge_criteria in gold label for {csv_id}")

    result = judge(scenario, gold, record.get("tool_calls", []), record["response"])
    _print_result(result)

    record["judge"] = result
    path.write_text(json.dumps(record, indent=2))
    _rebuild_index()
    print(f"\n  Saved → {path.name}")


if __name__ == "__main__":
    import argparse

    from runner.loader import load_gold, load_scenario

    parser = argparse.ArgumentParser(description="LLM-as-judge for saved agent runs")
    parser.add_argument(
        "run", nargs="?", help="Run ID, partial ID, or path to result JSON"
    )
    parser.add_argument(
        "--all", action="store_true", help="Judge every saved run that has gold labels"
    )
    parser.add_argument(
        "--unjudged",
        action="store_true",
        help="Judge only saved runs that have not been judged yet",
    )
    parser.add_argument(
        "--agent",
        help="Restrict --all/--unjudged to a single agent (toolloop, s3soa, soa, eoa, poa)",
    )
    parser.add_argument(
        "--save-prompts",
        action="store_true",
        help="Reconstruct and save judge prompts into existing run JSONs — no LLM calls",
    )
    args = parser.parse_args()

    if args.save_prompts:
        files = sorted(RESULTS_DIR.rglob("*.json"))
        judged = [f for f in files if json.loads(f.read_text()).get("judge")]
        print(f"\n  Saving prompts for {len(judged)} judged runs (no LLM calls)...\n")
        for path in judged:
            rec = json.loads(path.read_text())
            csv_id = rec["scenario_id"]
            try:
                gold = load_gold(csv_id)
                scenario = load_scenario(csv_id)
                prompt = _build_prompt(
                    scenario, gold, rec.get("tool_calls", []), rec["response"]
                )
                rec["judge"]["prompt"] = prompt
                path.write_text(json.dumps(rec, indent=2))
                print(f"  saved  {rec['id'][-55:]}")
            except Exception as e:
                print(f"  [error] {csv_id}: {e}")
        print("\n  Done.")

    elif args.all or args.unjudged:
        files = (
            sorted((RESULTS_DIR / args.agent).glob("*.json"))
            if args.agent
            else sorted(RESULTS_DIR.rglob("*.json"))
        )
        if args.unjudged:
            files = [f for f in files if not json.loads(f.read_text()).get("judge")]
        scope = f"{args.agent} " if args.agent else ""
        print(
            f"\n  Judging {len(files)} {scope}{'unjudged ' if args.unjudged else ''}saved runs...\n"
        )
        total_in = total_out = 0
        for path in files:
            rec = json.loads(path.read_text())
            csv_id = rec["scenario_id"]
            try:
                gold = load_gold(csv_id)
                if not gold.get("judge_criteria"):
                    print(f"  [skip] {csv_id} — no judge_criteria")
                    continue
                scenario = load_scenario(csv_id)
                result = judge(
                    scenario, gold, rec.get("tool_calls", []), rec["response"]
                )
                rec["judge"] = result
                path.write_text(json.dumps(rec, indent=2))
                tok = result.get("token_usage", {})
                total_in += tok.get("input", 0)
                total_out += tok.get("output", 0)
                print(
                    f"  done   {rec['id'][-50:]}  ({tok.get('input', 0):,}in {tok.get('output', 0):,}out)"
                )
            except Exception as e:
                print(f"  [error] {csv_id}: {e}")
        _rebuild_index()
        cost_in = total_in / 1_000_000 * 3.00
        cost_out = total_out / 1_000_000 * 15.00
        print(
            f"\n  Tokens : {total_in:,} in  {total_out:,} out  ({total_in + total_out:,} total)"
        )
        print(
            f"  Cost   : ${cost_in + cost_out:.4f}  (${cost_in:.4f} in + ${cost_out:.4f} out)"
        )
        print("  index.json rebuilt.")

    elif args.run:
        path = _resolve_path(args.run)
        _judge_file(path)

    else:
        parser.print_help()
        print(f"\nSaved runs in {RESULTS_DIR}:")
        for f in sorted(RESULTS_DIR.rglob("*.json")):
            rec = json.loads(f.read_text())
            has_j = "✓ judged" if rec.get("judge") else "  ------"
            print(f"  {has_j}  {f.stem}")
