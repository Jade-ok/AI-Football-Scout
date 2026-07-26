"""Evaluation harness for the LLM Judge.

Runs every case in the golden dataset through the judge and compares
the verdict it returns against the expected verdict. A single API
failure is recorded rather than raised, so one bad call cannot destroy
the results already collected.

Run as a script to get a pass rate and a threshold gate. The process
exits with a non-zero status when the pass rate falls below THRESHOLD,
which makes this file usable as a regression test.
"""

import json
import sys
import time
from pathlib import Path

from data.loader import get_player_stats
from judges.llm_judge import verify_reasoning

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"
THRESHOLD = 0.88


def load_golden_cases():
    with open(GOLDEN_PATH) as f:
        return json.load(f)


def evaluate_judge(cases, verbose=True):
    """Run the LLM judge on every golden case and score it.

    Returns a dict with "score", "passed", "total", "mismatches", "errors".
    Both the display string and the raw counts are included, so callers can
    print the result or compute a rate without parsing anything.

    An API error on one case is recorded rather than raised. One bad call
    cannot destroy the results already collected.
    """
    mismatches = []
    errors = []
    for case in cases:
        source = get_player_stats(case["player"])

        try:
            got = verify_reasoning(case["answer"], source)["verdict"]
        except Exception as e:
            # One failed case must not destroy the other results
            errors.append({"id": case["id"], "error": str(e)[:100]})
            if verbose:
                print(f"⚠️ {case['id']}: API error, skipped")
            time.sleep(15)
            continue

        ok = got == case["expected"]
        if verbose:
            print(f"{'✅' if ok else '❌'} {case['id']}: expected "
                  f"{case['expected']}, got {got}")
        if not ok:
            mismatches.append({"id": case["id"],
                               "expected": case["expected"], "got": got})

        time.sleep(15)   # free tier: 5 requests/min -> stay under the limit

    passed = len(cases) - len(mismatches) - len(errors)

    return {"score": f"{passed}/{len(cases)}",
            "passed": passed,
            "total": len(cases),
            "mismatches": mismatches,
            "errors": errors}


# Only runs when this file is executed directly, not when it is imported.
# Importing evaluate_judge from a notebook must not fire off a full run.
if __name__ == "__main__":
    cases = load_golden_cases()
    result = evaluate_judge(cases)

    pass_rate = result["passed"] / result["total"]
    print(f"\nPass rate: {pass_rate:.2f} ({result['score']})")

    # Errors already lower the pass rate, so the score alone cannot tell
    # a weak judge apart from a bad network. Flag the difference.
    if result["errors"]:
        print(f"WARNING: {len(result['errors'])} case(s) hit API errors")

    # A non-zero exit status is what automation reads, not the printed text.
    if pass_rate < THRESHOLD:
        print(f"FAILED: below threshold {THRESHOLD}")
        sys.exit(1)

    print("PASSED")