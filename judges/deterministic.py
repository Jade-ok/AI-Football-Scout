"""Deterministic Judge for the AI Football Scout.

Extracts every number from an agent's answer and verifies each one
against the source data. Pure code, no LLM — same input, same verdict.
"""

import math
import re


def extract_numbers(text):
    """Pull every number out of a text answer."""
    # Season notations like 24/25 or 2024-25 are not stat claims — drop them first
    text = re.sub(r"\b\d{2,4}[/-]\d{2,4}\b", " ", text)
    raw = re.findall(r"\d[\d,]*\.?\d*", text)
    return [float(n.replace(",", "")) for n in raw]


def verify_numbers(answer_text, source_record):
    """Check every number in the answer against the source data.

    source_record: the dict returned by get_player_stats
    Returns a verdict dict — never raises.

    Known limits (by design, v1):
    - Derived values (e.g. "6 in total" from 4+2) are flagged as unverified.
    - Non-numeric claims (interpretations) are invisible to this judge;
      those belong to the LLM Judge.
    """
    claimed = extract_numbers(answer_text)

    truth = []
    for rec in source_record.get("records", []):
        for v in rec["stats"].values():
            if isinstance(v, (int, float)):
                truth.append(float(v))

    unverified = [n for n in claimed
                  if not any(math.isclose(n, t, rel_tol=0.01) for t in truth)]

    return {
        "verdict": "pass" if not unverified else "fail",
        "claimed": claimed,
        "unverified": unverified,
    }