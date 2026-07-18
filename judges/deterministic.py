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


def verify_numbers(answer_text, source_record, question=None):
    """Check every number in the answer against the source data.

    source_record comes in two shapes:
    - dict from get_player_stats: {"records": [{"stats": {...}}, ...]}
    - list from find_players:     [{...}, {...}, ...]
    question: the user's original question. Numbers echoed from it
    (e.g. "under 25") are not stat claims and are exempt from checking.
    Returns a verdict dict — never raises.

    Known limits (by design, v1):
    - Derived values (e.g. "6 in total" from 4+2) are flagged as unverified.
    - Non-numeric claims (interpretations) are invisible to this judge;
      those belong to the LLM Judge.
    """
    claimed = extract_numbers(answer_text)

    # Numbers the user themselves said (e.g. "under 25") are not
    # stat claims — echoing the question must not fail the answer.
    question_numbers = extract_numbers(question) if question else []
    claimed = [n for n in claimed if n not in question_numbers]

    # --- collect every number from the source, whatever its shape ---
    # The judge does not care which tool produced the data —
    # it only needs the numbers inside, so handle both shapes.
    truth = []

    if isinstance(source_record, dict):
        # envelope shape: open "records", read each team's stats
        for rec in source_record.get("records", []):
            for v in rec["stats"].values():
                if isinstance(v, (int, float)):
                    truth.append(float(v))
    elif isinstance(source_record, list):
        # plain list shape: each row is one player, read its values directly
        for row in source_record:
            for v in row.values():
                if isinstance(v, (int, float)):
                    truth.append(float(v))

    unverified = [n for n in claimed
                  if not any(math.isclose(n, t, rel_tol=0.01) for t in truth)]

    return {
        "verdict": "pass" if not unverified else "fail",
        "claimed": claimed,
        "unverified": unverified,
    }