"""
Local end-to-end test of the ACE Bench ToolLoop pipeline — no AWS, no deploy.

Wires together, in one process:
  - a mock AWS session (local_test/mock_aws.py) + matching manifest
  - the agent bridge (local_test/agent_bridge.py) proxying to a local Ollama model
  - the REAL ToolLoopAdapter, capture, resolver, and evaluator

so you can confirm the whole flow works before deploying fixtures or migrating labels.

Usage:
    # Ollama must be reachable (host install, or `docker compose up -d` in this dir)
    python -m local_test.run_local
    python -m local_test.run_local COPS-kms-keys-with-rotation-disable-L1-f8c2675f
"""

import os
import sys
import time
import threading

from local_test.agent_bridge import make_server
from local_test.mock_aws import MockSession, MOCK_MANIFEST

from runner.loader import load_scenario, load_gold
from runner.resolver import ManifestResolver
from runner.agents.toolloop import ToolLoopAdapter
from runner.capture import capture, print_capture
from runner.evaluator import evaluate, print_evaluation

DEFAULT_SCENARIO = "COPS-kms-keys-with-rotation-disable-L1-f8c2675f"
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8099"))


def main():
    csv_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SCENARIO

    # 1. start the agent bridge in a background thread
    server = make_server(port=BRIDGE_PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.3)
    endpoint = f"http://127.0.0.1:{BRIDGE_PORT}"
    print(f"\n  bridge     : {endpoint}  (→ Ollama {os.getenv('OLLAMA_MODEL','huihui_ai/llama3.2-abliterate:3b')})")

    # 2. resolve the gold label against the MOCK manifest
    resolver = ManifestResolver(MOCK_MANIFEST)
    env = MOCK_MANIFEST
    gold = resolver.resolve_gold(load_gold(csv_id))
    scenario = load_scenario(csv_id)
    print(f"  scenario   : {csv_id}")
    print(f"  correct    : {gold.get('correct_resources')}")
    print(f"  expect tools: {[t['tool'] for t in gold.get('expected_tools', [])]}")

    # 3. build the REAL ToolLoop adapter with the injected MOCK AWS session
    adapter = ToolLoopAdapter(region="us-east-1", endpoint=endpoint, session=MockSession())

    # 4. run the scenario end to end
    print("\n  [running agent through the tool loop...]\n")
    agent_input = adapter.build_input(scenario, gold, env)
    result = adapter.run(agent_input).to_capture_dict()

    print(f"  tool calls made: {[tc['tool'] for tc in result['tool_calls']]}")
    captured = capture(result, csv_id, gold)
    eval_result = evaluate(captured, gold, observable_tools=True, native_tools=True)

    print_capture(captured)
    print_evaluation(eval_result)

    server.shutdown()
    print("\n  local end-to-end run complete.")
    return eval_result


if __name__ == "__main__":
    main()
