# AI Football Scout

A multi-agent AI system for hallucination-free football player analysis, built with the Orchestrator-Worker pattern and a dual-Judge architecture.

## Why This Project

LLMs frequently make up numbers when asked about sports statistics. This project solves that problem mechanically: every number in a generated report is extracted and verified against the actual database by a **deterministic Judge** — not another LLM. If the numbers don't match, the Orchestrator sends the task back for rework. No unverified answer reaches the user.

## Architecture

- **Orchestrator**: decomposes user questions into sub-tasks and controls the feedback loop
- **Stats Agent** (Gemini Flash): retrieves player statistics via function calling
- **Deterministic Judge** (pure code): extracts numbers from answers with regex and verifies them against source data
- **Analysis Agent & LLM Judge** (Gemini Pro): planned extensions for scout reports and logic verification

## Data Sources

EPL player statistics from FBref (via `soccerdata`), xG data from Understat, and EA FC player ratings from Kaggle. The data layer is abstracted so that adding a new league (e.g., MLS) is a configuration-level change.

## Status

Week 1 in progress — building the local end-to-end pipeline. This README doubles as a design journal; key decisions are recorded below as the project evolves.