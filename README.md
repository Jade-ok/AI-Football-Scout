# AI Football Scout

A multi-agent LLM system for hallucination-free football player analysis, built with an Orchestrator-Worker pattern and a dual-Judge verification architecture.

## Why This Project

LLMs frequently make up numbers when asked about sports statistics. This project solves that problem mechanically. Every answer is verified against the actual database before it reaches the user, and two complementary judges cover two different failure modes. A **deterministic Judge** catches wrong numbers, and an **LLM Judge** catches answers where the numbers are right but the reasoning behind them is fabricated. If verification fails, the Orchestrator sends the task back for rework.

## Architecture

**Implemented**

- **Orchestrator** (`orchestrator/`): routes user questions to the Stats Agent and runs the verify-and-retry loop. `ask_stats_agent` returns both the answer and the raw tool results, so judges always see the answer and its source data.
- **Stats Agent** (`agents/stats_agent.py`, Gemini 2.5 Flash): answers player-stat queries via multi-round function calling. System-prompt "producer constraints" (for example, never merge stats across clubs) prevent a class of hallucinations upstream instead of relying only on downstream verification.
- **Deterministic Judge** (`judges/deterministic.py`): extracts numbers from answers and verifies them against source data with `math.isclose`. Pure code, zero LLM cost.
- **LLM Judge** (`judges/llm_judge.py`, Gemini structured output): returns a JSON verdict on whether the answer's claims are actually supported by the retrieved data.

**Planned**

- **Analysis Agent**: narrative scout reports on top of verified stats.

## Data

EPL player statistics from FBref (via `soccerdata`), stored in a local SQLite database (`data/stats.db`) built by `data/build_db.py`.

Design principles baked into the data layer:

- **Transfer-split**: joins match on both player name and team, so a mid-season transfer never merges stats from two clubs into one row.
- **Minimum minutes threshold** (`min_minutes=900`): filters out small-sample noise in per-90 metrics.
- **Parameterized queries** throughout, so user-facing questions can never inject SQL.
- The data layer is abstracted so adding a new league (for example, MLS) is a configuration-level change.

## Evaluation

eval/ contains a golden dataset of cases with pass/fail ground truth and an automated runner (eval/evaluate.py). Each case runs inside its own try/except, with a fixed delay between cases to stay under the API rate limit, so a single API error cannot wipe the results of completed cases. That safeguard exists because a 429 error once did exactly that.


## Project Structure

```
agents/        Stats Agent (Gemini function calling)
data/          build_db.py, SQLite store, name-search loader
judges/        deterministic.py, llm_judge.py
orchestrator/  routing and the verify-and-retry loop
eval/          golden dataset and evaluation runner
notebooks/     prototyping (verified code graduates to modules)
```

## Roadmap

- Analysis Agent for narrative scout reports
- Vancouver Whitecaps / MLS data expansion
- Additional data sources (xG, player ratings) once the core pipeline is validated
- Model upgrades (Flash to Pro) only where evaluation results justify the cost
- Cloud deployment after local completion

## Status

Core pipeline complete end-to-end locally: agent, dual-judge verification, and retry, with an automated evaluation harness. This README doubles as a design journal; key decisions are recorded as the project evolves.
