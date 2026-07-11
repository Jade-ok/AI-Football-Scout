"""Stats Agent for the AI Football Scout.

Takes a natural-language question, lets Gemini decide when to call
get_player_stats, executes the tool, and returns the answer together
with the tool results it was based on.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from data.loader import get_player_stats


load_dotenv(override=True)

client = genai.Client()

MODEL = "gemini-2.5-flash"

TEAM = "Tottenham" 

SYSTEM_PROMPT = f"""You are a scouting assistant for {TEAM}'s recruitment department.
You answer questions about player statistics.

## Tool use
1. Use the get_player_stats tool for any question about a player's stats.
2. Base every number on tool results, never on memory.

## Reporting rules
3. Write all statistics as digits (e.g. "6 goals"), never as words.
4. If a player played for multiple teams in one season, report each
   team's numbers separately. Never merge them into a single total.
5. Name the scope of every number (team, season, competition),
   e.g. "6 goals for Arsenal in the 2024-25 Premier League season".

## When data is missing
6. If the database has no data for something, say so plainly.
7. Never assert facts that are not in the tool results — no data for X
   does not mean X is false."""

get_player_stats_declaration = {
    "name": "get_player_stats",
    "description": "Get a football player's season statistics (goals, assists, "
                   "minutes, etc.) from the EPL database. Use this whenever the "
                   "user asks about a specific player's stats.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string",
                     "description": "Player name, full or partial (e.g. 'Saka')"},
            "season": {"type": "string",
                       "description": "Season code. The database contains ONLY "
                                      "'2425' (the 2024-25 season). If the user "
                                      "asks about any other season, do not guess "
                                      "— tell them only 2024-25 data is available."},
        },
        "required": ["name"],
    },
}

tools = types.Tool(function_declarations=[get_player_stats_declaration])
config = types.GenerateContentConfig(
    tools=[tools],
    system_instruction=SYSTEM_PROMPT,
)


def ask_stats_agent(question, max_rounds=5, verbose=True):
    """Ask the scout a question.

    Returns {"answer": str, "tool_results": list} — tool results are
    kept so a judge can verify the answer against its actual sources.
    """
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    tool_results = []  # every dict the tool returns is kept here for the judge

    for _ in range(max_rounds):
        resp = client.models.generate_content(
            model=MODEL, contents=contents, config=config)

        # Scan ALL parts for a function call (it is not always parts[0])
        parts = resp.candidates[0].content.parts
        fc = next((p.function_call for p in parts if p.function_call), None)

        if fc is None:
            # No tool request anywhere -> this is the final answer
            return {"answer": resp.text,
                    "tool_results": tool_results}

        if verbose:
            print(f"  [tool call] {fc.name}({dict(fc.args)})")
        result = get_player_stats(**fc.args)
        tool_results.append(result)  # keep a copy before handing it to the model
        contents.append(resp.candidates[0].content)
        contents.append(types.Content(role="tool", parts=[
            types.Part.from_function_response(
                name=fc.name, response={"result": result})]))

    return {"answer": "(stopped: too many tool calls)",  # safety valve
            "tool_results": tool_results}