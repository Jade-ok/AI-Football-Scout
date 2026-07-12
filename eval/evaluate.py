"""Evaluation loop for the LLM Judge.

Runs every golden case through the judge and scores the results.
The golden dataset is the exam; this file is the grader.
"""

import json
import time
from pathlib import Path

from data.loader import get_player_stats
from judges.llm_judge import verify_reasoning

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"


def load_golden_cases():
    with open(GOLDEN_PATH) as f:
        return json.load(f)


def evaluate_judge(cases, verbose=True):
    """Run the LLM judge on every golden case and score it.

    Returns {"score": "n/total", "mismatches": [...], "errors": [...]}
    API errors on one case do not kill the run — they are recorded as data.
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

    return {"score": f"{len(cases) - len(mismatches) - len(errors)}"
                     f"/{len(cases)}",
            "mismatches": mismatches,
            "errors": errors}