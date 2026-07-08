"""Stats Agent for the AI Football Scout.

Takes a natural-language question, lets Gemini decide when to call
get_player_stats, executes the tool, and returns a text answer.
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
Answer questions about player statistics using the get_player_stats tool.
Always base numbers on tool results, never on memory.
When a player played for multiple teams in one season, report each team's
numbers separately and clearly.
If the database has no data for something, say so plainly.
Never assert facts that are not in the tool results."""

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
    """Ask the scout a question. Returns the final text answer."""
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]

    for _ in range(max_rounds):
        resp = client.models.generate_content(
            model=MODEL, contents=contents, config=config)

        # Scan ALL parts for a function call (it is not always parts[0])
        parts = resp.candidates[0].content.parts
        fc = next((p.function_call for p in parts if p.function_call), None)

        if fc is None:
            return resp.text  # no tool request anywhere -> final answer

        if verbose:  # --- Difference #3: print is now switchable
            print(f"  [tool call] {fc.name}({dict(fc.args)})")
        result = get_player_stats(**fc.args)
        contents.append(resp.candidates[0].content)
        contents.append(types.Content(role="tool", parts=[
            types.Part.from_function_response(
                name=fc.name, response={"result": result})]))

    return "(stopped: too many tool calls)"  # safety valve