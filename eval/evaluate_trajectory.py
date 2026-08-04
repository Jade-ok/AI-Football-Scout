"""Trajectory evaluation for the Stats Agent.

Asks the agent every question in the trajectory dataset and checks
which tools it actually called against the expected tools. The final
answer is not judged here. A right answer produced by the wrong tool
is a failure that answer-level evaluation cannot see.

Comparison is by tool set. Order and repeat calls are ignored, because
the question here is tool selection, not call efficiency.
"""

import json
import sys
import time
import os

EVAL_DELAY = float(os.environ.get("EVAL_DELAY", 15))
from pathlib import Path

from agents.stats_agent import ask_stats_agent

DATASET_PATH = Path(__file__).parent / "trajectory_dataset.json"
THRESHOLD = 1.0


def load_cases():
    with open(DATASET_PATH) as f:
        return json.load(f)


def evaluate_trajectory(cases, verbose=True):
    """Ask the agent every question and score its tool selection.

    Returns a dict with "passed", "total", "mismatches", "errors".
    An API error on one case is recorded rather than raised.
    """
    mismatches = []
    errors = []
    for case in cases:
        try:
            out = ask_stats_agent(case["question"], verbose=False)
        except Exception as e:
            errors.append({"id": case["id"], "error": str(e)[:100]})
            if verbose:
                print(f"⚠️ {case['id']}: API error, skipped")
            continue

        called = {t["tool"] for t in out["tool_results"]}
        expected = set(case["expected_tools"])

        ok = called == expected
        if verbose:
            print(f"{'✅' if ok else '❌'} {case['id']}: expected "
                  f"{sorted(expected)}, called {sorted(called)}")
        if not ok:
            mismatches.append({"id": case["id"],
                               "expected": sorted(expected),
                               "called": sorted(called)})
        time.sleep(EVAL_DELAY)   # respect the free-tier rate limit, like the judge eval

    passed = len(cases) - len(mismatches) - len(errors)

    return {"passed": passed,
            "total": len(cases),
            "mismatches": mismatches,
            "errors": errors}


# Only runs when executed directly, not when imported.
if __name__ == "__main__":
    cases = load_cases()
    result = evaluate_trajectory(cases)

    pass_rate = result["passed"] / result["total"]
    print(f"\nPass rate: {pass_rate:.2f} ({result['passed']}/{result['total']})")

    if result["errors"]:
        print(f"WARNING: {len(result['errors'])} case(s) hit API errors")

    if pass_rate < THRESHOLD:
        print(f"FAILED: below threshold {THRESHOLD}")
        sys.exit(1)

    print("PASSED")