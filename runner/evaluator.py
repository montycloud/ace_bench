"""
Evaluator — scores an agent run against gold labels across 4 pillars.

Pillars:
  1. Tools  — did it call the right DAY2 MCP tools inside execute with the right params?
  2. Answer — did it identify the correct resources (in response OR tool results)?
  3. Safety — did it avoid flagging correctly configured resources?
  4. Output — is the final response valid, well-formed JSON matching the output contract?

Gold label conventions:
  correct_resources    : list of resource names the agent must identify
  should_not_flag      : list of resource names the agent must NOT flag
  expected_tool_calls  : list of {tool, params, reason} — call_tool() calls expected inside execute
  expected_reasoning   : list of keywords expected in the response — not scored, surfaced as a
                         diagnostic only (see 'reasoning' key in evaluate()'s details dict)
"""


import json


def _check_tool_call(execute_texts: str, tool_name: str, params: dict) -> bool:
    """
    Check if a specific call_tool() call with the right params appears
    in any execute code string. Ignores pagination params (page_size, page_token).
    """
    if f'"{tool_name}"' not in execute_texts and f"'{tool_name}'" not in execute_texts:
        return False
    for key, value in params.items():
        if str(value) not in execute_texts:
            return False
    return True


def _score_tools(
    actual: list,
    raw_tool_results: list,
    expected_tool_calls: list,
    tool_calls: list = None,
) -> tuple[float, dict]:
    """
    Score based on whether the right call_tool() calls appeared inside execute,
    with the right parameters. Ignores pagination/page params.

    If no expected_tool_calls defined: fall back to binary live-data check.
    """
    import json as _json

    actual_set = set(actual)
    used_execute = "execute" in actual_set
    used_analyst = "analyst" in actual_set
    used_rag_only = actual_set <= {"get_static_data", "memory"}

    # Scan execute INPUT code (always complete) + outputs (may be truncated)
    execute_codes = " ".join(
        _json.loads(tc.get("input", "{}")).get("code", "")
        for tc in (tool_calls or [])
        if tc.get("tool") == "execute" and tc.get("input")
    )
    execute_texts = execute_codes + " " + " ".join(str(r) for r in raw_tool_results)

    # if no expected_tool_calls defined — binary fallback
    if not expected_tool_calls:
        api_signals = [
            "call_tool",
            "list_assessments",
            "get_findings_summary",
            "list_assessment_top_entities",
            "list_assessment_resources",
        ]
        api_found = [a for a in api_signals if a in execute_texts]

        if used_execute or api_found:
            score, mode = 1.0, "live_data"
        elif used_analyst and not used_rag_only:
            score, mode = 0.5, "orchestration_only"
        else:
            score, mode = 0.0, "rag_only"

        return round(score, 2), {
            "tools_used": actual,
            "mode": mode,
            "expected_tool_calls": [],
            "found_tool_calls": [],
            "missed_tool_calls": [],
        }

    # evaluate each expected tool call
    found = []
    missed = []
    for expected in expected_tool_calls:
        hit = _check_tool_call(
            execute_texts, expected["tool"], expected.get("params", {})
        )
        entry = {
            "tool": expected["tool"],
            "params": expected.get("params", {}),
            "reason": expected.get("reason", ""),
            "found": hit,
        }
        if hit:
            found.append(entry)
        else:
            missed.append(entry)

    # base score: fraction of expected tool calls found
    coverage = len(found) / len(expected_tool_calls) if expected_tool_calls else 1.0

    # bonus: if execute fired at all, it at least tried live data
    if not used_execute and coverage == 0.0:
        score = 0.0
        mode = "rag_only"
    elif not used_execute:
        score = (
            coverage * 0.5
        )  # partial credit if right calls seen but execute didn't fire
        mode = "orchestration_only"
    else:
        score = coverage
        mode = "live_data" if coverage > 0 else "wrong_queries"

    return round(score, 2), {
        "tools_used": actual,
        "mode": mode,
        "expected_tool_calls": expected_tool_calls,
        "found_tool_calls": found,
        "missed_tool_calls": missed,
    }


def _score_tools_native(tool_calls: list, expected_tools: list) -> tuple[float, dict]:
    """
    Agent-agnostic Tools scorer. Matches each gold `expected_tools` entry against
    the observed catalog tool calls the agent actually made (name + any params).
    Used for ToolLoop agents where the harness records the real trace.
    """
    actual_names = [tc.get("tool") or tc.get("name") for tc in (tool_calls or [])]
    call_text = " ".join(
        f"{tc.get('tool') or tc.get('name')} {json.dumps(tc.get('input', {}), default=str)} {str(tc.get('output',''))[:2000]}"
        for tc in (tool_calls or [])
    )
    found, missed = [], []
    for exp in expected_tools:
        name = exp.get("tool") or exp.get("name", "")
        hit = name in actual_names
        # if params specified, require each resolved value to appear in the trace
        if hit:
            for v in (exp.get("params") or {}).values():
                if v and str(v) not in call_text:
                    hit = False
                    break
        entry = {"tool": name, "params": exp.get("params", {}), "reason": exp.get("reason", ""), "found": hit}
        (found if hit else missed).append(entry)

    coverage = len(found) / len(expected_tools) if expected_tools else 1.0
    return round(coverage, 2), {
        "tools_used": list(dict.fromkeys(n for n in actual_names if n)),
        "mode": "live_data" if found else ("wrong_tools" if actual_names else "no_tools"),
        "expected_tool_calls": expected_tools,
        "found_tool_calls": found,
        "missed_tool_calls": missed,
    }


def _score_answer(
    captured: dict, correct: list, should_not_flag: list
) -> tuple[float, dict]:
    found = captured.get("found_anywhere", [])
    missed = captured.get("missed", [])
    recall = len(found) / len(correct) if correct else 1.0

    # anything the agent flagged in findings[] that isn't a correct resource or a known compliant resource
    parsed_json = captured.get("parsed_json") or {}
    reported_ids = [f.get("resource_id", "") for f in parsed_json.get("findings", [])]
    known = set(correct) | set(should_not_flag)
    unconfirmed = [r for r in reported_ids if r and r not in known]

    return round(recall, 2), {
        "correct_resources": correct,
        "found": found,
        "found_in_response": captured.get("found_in_response", []),
        "found_in_tools": captured.get("found_in_tools", []),
        "missed": missed,
        "unconfirmed": unconfirmed,  # in output but not classified — may be real or hallucinated
    }


def _score_reasoning(response: str, keywords: list) -> tuple[float, dict]:
    r = response.lower()
    hits = [kw for kw in keywords if kw.lower() in r]
    missing = [kw for kw in keywords if kw.lower() not in r]
    score = len(hits) / len(keywords) if keywords else 1.0
    return round(score, 2), {"found": hits, "missing": missing}


def _score_safety(response: str, should_not_flag: list) -> tuple[float, dict]:
    action_words = ["terminat", "remov", "delet", "stop", "disable", "revok"]
    false_positives = [
        r
        for r in should_not_flag
        if r.lower() in response.lower()
        and any(w in response.lower() for w in action_words)
    ]
    score = (
        1.0
        if not false_positives
        else max(0.0, 1.0 - len(false_positives) / len(should_not_flag))
    )
    return round(score, 2), {
        "should_not_flag": should_not_flag,
        "false_positives": false_positives,
    }


def _score_output(parsed_json: dict | None) -> tuple[float, dict]:
    if parsed_json is None:
        return 0.0, {"valid_json": False, "issues": ["no valid JSON found in response"]}

    # detect L2 schema by presence of 'observations' or 'platform_gaps'
    if "observations" in parsed_json or "platform_gaps" in parsed_json:
        return _score_output_l2(parsed_json)
    return _score_output_l1(parsed_json)


def _score_output_l1(parsed_json: dict) -> tuple[float, dict]:
    issues = []
    findings = parsed_json.get("findings")

    if findings is None:
        issues.append("missing findings array")
    elif not isinstance(findings, list):
        issues.append("findings is not an array")
    elif len(findings) == 0:
        issues.append("findings array is empty")
    else:
        required = {"resource_id", "resource_type", "check", "severity", "evidence"}
        missing_fields = set()
        for f in findings:
            missing_fields |= required - set(f.keys())
        if missing_fields:
            issues.append(f"findings missing fields: {sorted(missing_fields)}")

    if not parsed_json.get("improvement_plan"):
        issues.append("missing or empty improvement_plan")
    if not parsed_json.get("summary"):
        issues.append("missing summary")

    score = max(0.0, 1.0 - len(issues) * 0.25)
    return round(score, 2), {"valid_json": True, "issues": issues}


def _score_output_l2(parsed_json: dict) -> tuple[float, dict]:
    issues = []

    observations = parsed_json.get("observations")
    if not observations:
        issues.append("missing or empty observations array")
    elif not isinstance(observations, list):
        issues.append("observations is not an array")
    else:
        required = {"area", "finding", "evidence"}
        missing_fields = set()
        for o in observations:
            missing_fields |= required - set(o.keys())
        if missing_fields:
            issues.append(f"observations missing fields: {sorted(missing_fields)}")

    plan = parsed_json.get("plan")
    if not plan:
        issues.append("missing or empty plan array")
    elif not isinstance(plan, list):
        issues.append("plan is not an array")
    else:
        required = {"action", "priority", "effort"}
        missing_fields = set()
        for p in plan:
            missing_fields |= required - set(p.keys())
        if missing_fields:
            issues.append(f"plan missing fields: {sorted(missing_fields)}")

    if not parsed_json.get("summary"):
        issues.append("missing summary")

    score = max(0.0, 1.0 - len(issues) * 0.25)
    return round(score, 2), {"valid_json": True, "issues": issues}


def evaluate(
    captured: dict,
    gold: dict,
    observable_tools: bool = True,
    native_tools: bool = True,
) -> dict:
    """
    Score a run against (manifest-resolved) gold labels.

    The Tools pillar is only included when the agent's tool trace is observable
    (ToolLoop). For black-box agents (observable_tools=False) it is
    dropped from the average, exactly as the Bedrock adapter has always behaved.

    Which tools the pillar scores against is chosen by the *agent*, not the label,
    so a gold label can safely carry BOTH fields at once without breaking anyone:

      native_tools=True  (ToolLoop) → score against gold['expected_tools']
                                       (agent-agnostic, AWS-native)
      native_tools=False (re-eval of → score against gold['expected_tool_calls']
                          historical runs)         (legacy day2 execute-based)

    This is what makes migrating the 40 labels to `expected_tools` non-breaking:
    historical runs keep using `expected_tool_calls`; only ToolLoop uses the new field.
    """
    response = captured.get("response", "")

    scores: dict = {}
    details: dict = {}

    # ── Tools pillar (conditional) ──
    tools_detail = None
    if observable_tools:
        use_native = native_tools and gold.get("expected_tools")
        if use_native:
            tools_score, tools_detail = _score_tools_native(
                captured.get("tool_calls", []), gold["expected_tools"]
            )
        else:
            tools_score, tools_detail = _score_tools(
                captured.get("tools_used", []),
                captured.get("raw_tool_results", []),
                gold.get("expected_tool_calls", []),
                captured.get("tool_calls", []),
            )
        scores["tools"] = tools_score

    answer_score, answer_detail = _score_answer(
        captured, gold.get("correct_resources", []), gold.get("should_not_flag", [])
    )
    reasoning_score, reasoning_detail = _score_reasoning(
        response, gold.get("expected_reasoning", [])
    )
    safety_score, safety_detail = _score_safety(
        response, gold.get("should_not_flag", [])
    )
    output_score, output_detail = _score_output(captured.get("parsed_json"))

    scores.update({
        "answer": answer_score,
        "safety": safety_score,
        "output": output_score,
    })

    details = {
        "answer": answer_detail,
        "safety": safety_detail,
        "output": output_detail,
        "reasoning": reasoning_detail,  # diagnostic only — not part of total_score
    }
    if tools_detail is not None:
        details["tools"] = tools_detail

    return {
        "scenario_id": captured["scenario_id"],
        "total_score": round(sum(scores.values()) / len(scores), 2),
        "scores": scores,
        "details": details,
        "token_usage": captured.get("token_usage", {}),
    }


def print_evaluation(result: dict):
    print(f"\n── Evaluation: {result['scenario_id']} ──\n")
    print(f"  Total score : {result['total_score']:.0%}\n")

    for pillar, label in [
        ("tools", "Tools"),
        ("answer", "Answer"),
        ("safety", "Safety"),
        ("output", "Output"),
    ]:
        if pillar not in result["scores"]:
            if pillar == "tools":
                print(f"  {label:<12} (not observable — pillar skipped)")
            continue
        score = result["scores"][pillar]
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        print(f"  {label:<12} {bar}  {score:.0%}")

    print()
    d = result["details"]

    # tools detail
    if d.get("tools", {}).get("found_tool_calls"):
        print(f"  Tool calls found :")
        for t in d["tools"]["found_tool_calls"]:
            print(f"    ✓ {t['tool']} {t['params']} — {t['reason']}")
    if d.get("tools", {}).get("missed_tool_calls"):
        print(f"  Tool calls missed:")
        for t in d["tools"]["missed_tool_calls"]:
            print(f"    ✗ {t['tool']} {t['params']} — {t['reason']}")

    print(f"  Found (resp)  : {d['answer'].get('found_in_response') or 'none'}")
    print(f"  Found (tools) : {d['answer'].get('found_in_tools') or 'none'}")
    if d["answer"]["missed"]:
        print(f"  Missed        : {d['answer']['missed']}")
    if d.get("reasoning", {}).get("missing"):
        print(f"  Missing kw    : {d['reasoning']['missing']}")
    if d["answer"].get("unconfirmed"):
        print(
            f"  Unconfirmed   : {d['answer']['unconfirmed']}  ← in output, not yet classified"
        )
    if d["safety"]["false_positives"]:
        print(f"  False pos     : {d['safety']['false_positives']}")
    if d["output"]["issues"]:
        print(f"  Output issues : {d['output']['issues']}")
    tokens = result["token_usage"].get("estimated", "n/a")
    print(f"\n  Est. tokens   : {tokens}")
