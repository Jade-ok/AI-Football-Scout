"""Pipeline for the AI Football Scout.

Connects the Stats Agent and the deterministic Judge:
ask -> verify -> retry on failure.
"""

from agents.stats_agent import ask_stats_agent
from judges.deterministic import verify_numbers
from judges.llm_judge import verify_reasoning 

def scout_pipeline(question):
    out = ask_stats_agent(question)

    # No tool used (e.g. "who is the best player") -> nothing to verify
    if not out["tool_results"]:
        return {"answer": out["answer"], "verdict": "not_applicable"}

    # Judge 1 (deterministic): every number must exist in the source data
    verdicts = [verify_numbers(out["answer"], src) for src in out["tool_results"]]
    numbers_ok = all(v["verdict"] == "pass" for v in verdicts)

    # Judge 2 (LLM): the reasoning must follow from the source data
    # (only the first tool result for now — multi-source handling is backlog)
    reasoning = verify_reasoning(out["answer"], out["tool_results"][0])
    reasoning_ok = reasoning["verdict"] == "pass"

    overall = "pass" if (numbers_ok and reasoning_ok) else "fail"

    return {"answer": out["answer"], "verdict": overall,
            "details": verdicts, "reasoning_check": reasoning}


def scout_with_retry(question, max_attempts=2):
    for attempt in range(max_attempts):
        result = scout_pipeline(question)

        if result["verdict"] in ("pass", "not_applicable"):
            result["attempts"] = attempt + 1
            return result

        # Failed: tell the agent what could not be verified and retry
        bad = [n for v in result["details"] for n in v["unverified"]]
        question = (f"{question}\n\nYour previous answer contained numbers "
                    f"that could not be verified against the database: {bad}. "
                    f"Answer again using ONLY numbers from the tool results.")

    result["attempts"] = max_attempts
    result["warning"] = "still failing after retries"
    return result