"""Data layer for the AI Football Scout.

Reads EPL player season stats from a local SQLite database (data/stats.db,
built from FBref by build_db.py) and exposes two functions:

- get_player_stats(name): name -> that player's season stats   [lookup]
- find_players(criteria): criteria -> ranked candidate list    [search]

The data source is hidden behind these functions, so the storage can
change (DataFrame -> SQLite today, more leagues tomorrow) without
touching the agent, judges, or pipeline.
"""

import sqlite3
from pathlib import Path

# Path to the DB, relative to THIS file — works no matter where
# the caller runs from (notebook, script, anywhere).
DB_PATH = Path(__file__).parent / "stats.db"


def _connect():
    # Small helper: open the DB and make rows readable by column name
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_player_stats(name, season="2425", competition="ENG-Premier League"):
    """Look up one player's season stats by (possibly partial) name.

    Returns {"player", "season", "competition", "records": [...]}.
    A mid-season transfer means 2+ records — never merged, so the
    Judge can verify numbers against the original rows.
    Errors come back as {"error": ...} dicts, never exceptions.
    """
    conn = _connect()
    rows = conn.execute("SELECT * FROM players").fetchall()
    conn.close()

    all_names = sorted({r["name"] for r in rows})

    # --- 3-tier name search: strict first, then looser ---
    # Tier 1: whole-word match (treat hyphens as spaces)
    matches = [p for p in all_names
               if name.lower() in p.lower().replace("-", " ").split()]

    # Tier 2: substring match
    if not matches:
        matches = [p for p in all_names if name.lower() in p.lower()]

    # Tier 3: match with hyphens/spaces removed ("heungmin" -> "sonheungmin")
    if not matches:
        squash = lambda s: s.lower().replace("-", "").replace(" ", "")
        matches = [p for p in all_names if squash(name) in squash(p)]

    # --- error-as-data, never crash ---
    if not matches:
        return {"error": f"Player '{name}' not found"}
    if len(matches) > 1:
        return {"error": "Multiple players matched — please be more specific",
                "candidates": matches}

    # --- one record per team row: transfers stay split ---
    player_name = matches[0]
    records = []
    for r in rows:
        if r["name"] == player_name:
            stats = dict(r)              # all columns of this row
            team = stats.pop("team")     # team goes to its own field
            stats.pop("name")            # name is already in the envelope
            records.append({"team": team, "stats": stats})

    return {
        "player": player_name,
        "season": season,
        "competition": competition,
        "records": records,   # length 2+ if transferred mid-season
    }

def find_players(position=None, max_age=None, min_minutes=900, limit=10):
    """Search players by scouting criteria, best candidates first.

    Ranking depends on position:
    - "DF" -> defensive actions per 90 (tackles won + interceptions)
    - anything else -> attacking output per 90 (goals + assists)
    min_minutes=900 (10 full games) keeps small-sample flukes out.
    """
    conn = _connect()

    # --- pick the ranking query by position ---
    if position == "DF":
        # defenders: rank by defensive actions, needs the defense table (JOIN)
        query = """
            SELECT p.name, p.team, p.position, p.age, p.minutes,
                   p.season, p.competition,
                   d.tackles_won, d.interceptions,
                   ROUND((d.tackles_won + d.interceptions) / d.nineties, 2) AS score
            FROM players p
            JOIN defense d ON p.name = d.name AND p.team = d.team
            WHERE p.minutes >= ?
        """
        col = "p."   # this query uses table aliases, filters need the prefix
    else:
        # default: rank by attacking output, players table alone is enough
        query = """
            SELECT name, team, position, age, minutes, goals, assists,
                   season, competition,
                   ROUND((goals + assists) * 90.0 / minutes, 2) AS score
            FROM players
            WHERE minutes >= ?
        """
        col = ""     # no alias here, plain column names

    params = [min_minutes]

    # --- optional filters, added only if the caller asks ---
    if position:
        query += f" AND {col}position LIKE ?"
        params.append(f"%{position}%")
    if max_age:
        query += f" AND {col}age <= ?"
        params.append(max_age)

    query += " ORDER BY score DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]