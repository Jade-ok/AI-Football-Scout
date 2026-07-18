"""Stats Agent for the AI Football Scout.

Takes a natural-language question, lets Gemini decide when to call
get_player_stats, executes the tool, and returns the answer together
with the tool results it was based on.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from data.loader import get_player_stats, find_players


load_dotenv(override=True)

client = genai.Client()

MODEL = "gemini-2.5-flash"

TEAM = "Tottenham" 

SYSTEM_PROMPT = f"""You are a scouting assistant for {TEAM}'s recruitment department.
You answer questions about player statistics.

## Tool use
1. Use get_player_stats when the user asks about a SPECIFIC named player.
2. Use find_players when the user asks to find or recommend players
   by criteria without naming one.
3. Base every number on tool results, never on memory.

## Reporting rules
4. Write all statistics as digits (e.g. "6 goals"), never as words.
5. If a player played for multiple teams in one season, report each
   team's numbers separately. Never merge them into a single total.
6. Name the scope of every number (team, season, competition),
   e.g. "6 goals for Arsenal in the 2024-25 Premier League season".

## When data is missing
7. If the database has no data for something, say so plainly.
8. Never assert facts that are not in the tool results — no data for X
   does not mean X is false.
9. If the user provides a common or incomplete name and you are unsure 
   which player they mean, do not guess. Ask the user to clarify the specific player or team."""


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


find_players_declaration = {
    "name": "find_players",
    "description": "Search for players matching scouting criteria and rank "
                   "them. Use this when the user asks to FIND, RECOMMEND, or "
                   "COMPARE players by conditions (position, age, performance) "
                   "WITHOUT naming a specific player. If the user names a "
                   "specific player, use get_player_stats instead.",
    "parameters": {
        "type": "object",
        "properties": {
            "position": {"type": "string",
                         "description": "Position filter: 'FW', 'MF', or 'DF'. "
                                        "'DF' ranks by defensive actions; "
                                        "others rank by attacking output."},
            "max_age": {"type": "integer",
                        "description": "Only players this age or younger."},
            "min_minutes": {"type": "integer",
                            "description": "Minimum minutes played. "
                                           "Default 900 (10 full games)."},
            "limit": {"type": "integer",
                      "description": "How many candidates to return. Default 10."},
        },
        "required": [],
    },
}

tools = types.Tool(function_declarations=[get_player_stats_declaration,
                                          find_players_declaration])
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
        # Run whichever tool the model asked for (fc.name tells us which)
        TOOL_FUNCTIONS = {"get_player_stats": get_player_stats,
                          "find_players": find_players}
        result = TOOL_FUNCTIONS[fc.name](**fc.args)
        tool_results.append(result)  # keep a copy before handing it to the model
        contents.append(resp.candidates[0].content)
        contents.append(types.Content(role="tool", parts=[
            types.Part.from_function_response(
                name=fc.name, response={"result": result})]))

    return {"answer": "(stopped: too many tool calls)",  # safety valve
            "tool_results": tool_results}