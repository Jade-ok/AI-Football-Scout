# AI Football Scout

A multi-agent LLM system that answers football player questions and verifies every answer against the source data before returning it. Built with an Orchestrator-Worker pattern and a dual-Judge verification architecture.

## Why This Project

LLMs frequently make up numbers when asked about sports statistics. This project addresses that mechanically. No answer reaches the user until it has been checked against the database it came from.

Two judges cover two different failure modes. The **Deterministic Judge** catches wrong numbers. The **LLM Judge** catches answers where the numbers are right but the reasoning behind them is fabricated. If either judge fails an answer, the Orchestrator sends the task back for rework.

## Architecture

**Implemented**

- **Orchestrator** (`orchestrator/`): routes user questions to the Stats Agent and runs the verify-and-retry loop. `ask_stats_agent` returns both the answer and the raw tool results, so judges always see the answer and its source data.
- **Stats Agent** (`agents/stats_agent.py`, Gemini 2.5 Flash): answers player-stat queries via multi-round function calling. System-prompt "producer constraints" (for example, never merge stats across clubs) prevent a class of hallucinations upstream instead of relying only on downstream verification.
- **Deterministic Judge** (`judges/deterministic.py`): extracts numbers from answers and verifies them against source data with `math.isclose`. Pure code, zero LLM cost.
- **LLM Judge** (`judges/llm_judge.py`, Gemini structured output): returns a JSON verdict on whether the answer's claims are supported by the retrieved data.

**Planned**

- **Analysis Agent**: narrative scout reports on top of verified stats.

## Data

EPL player statistics from FBref (via `soccerdata`), stored in a local SQLite database (`data/stats.db`) built by `data/build_db.py`.

Design principles baked into the data layer:

- **Transfer-split**: joins match on both player name and team, so a mid-season transfer never merges stats from two clubs into one row.
- **Minimum minutes threshold** (`min_minutes=900`): filters out small-sample noise in per-90 metrics.
- **Parameterized queries** throughout, so user-facing questions can never inject SQL.
- **Source abstraction**: query logic sits behind a loader module rather than being tied to FBref directly, which is what a second league (MLS) will plug into.

## Evaluation

`eval/` holds a golden dataset of cases with pass/fail ground truth, and a runner (`eval/evaluate.py`) that scores the pipeline against it.

Each case runs inside its own try/except, and a fixed delay between cases keeps requests under the API rate limit. Without that, one rate-limit error partway through the run discards the results of every case that already passed. The safeguard exists because exactly that happened.

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

- Vancouver Whitecaps / MLS data expansion
- Additional data sources (xG, player ratings) once the core pipeline is validated
- Model upgrades (Flash to Pro) only where evaluation results justify the cost
- Cloud deployment after local completion

## Status

The core pipeline runs end-to-end on a local machine. A question goes to the Stats Agent, both judges verify the answer, and a failed answer is sent back for a retry. The evaluation suite runs the golden dataset against this pipeline automatically.

Next up is the Analysis Agent.

This README doubles as a design journal. Key decisions are recorded here as the project evolves.
