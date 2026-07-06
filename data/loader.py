"""Data layer for the AI Football Scout.

Loads EPL player season stats from FBref (via soccerdata)
and exposes them through get_player_stats().
"""

import soccerdata as sd


def load_data(season="2024-2025"):
    # Data source is hidden behind this function,
    # so we can swap FBref for another source (e.g. FPL API) later.
    fbref = sd.FBref(leagues="ENG-Premier League", seasons=season)
    return fbref.read_player_season_stats(stat_type="standard")


# Load once when this module is imported.
# Every call to get_player_stats() reuses this same DataFrame.
df = load_data()


def get_player_stats(name, season="2425", competition="ENG-Premier League"):
    # 1. Filter by season first
    try:
        rows = df.xs(season, level="season")
    except KeyError:
        return {"error": f"No data for season {season}"}

    # 2. Search by name - strict match first, then fall back to looser matches
    all_players = rows.index.get_level_values("player").unique()

    # Step 1: whole-word match (treat hyphens as spaces)
    matches = [p for p in all_players
               if name.lower() in p.lower().replace("-", " ").split()]

    # Step 2: if nothing found, try substring match
    if not matches:
        matches = [p for p in all_players if name.lower() in p.lower()]

    # Step 3: if still nothing, compare with hyphens/spaces removed
    # (e.g. "heungmin" matches "sonheungmin")
    if not matches:
        squash = lambda s: s.lower().replace("-", "").replace(" ", "")
        matches = [p for p in all_players if squash(name) in squash(p)]

    # Final safety net — return an error dict instead of crashing
    if not matches:
        return {"error": f"Player '{name}' not found"}
    if len(matches) > 1:
        return {"error": "Multiple players matched — please be more specific",
                "candidates": matches}

    # 3. Return one record per team - do NOT merge rows
    # (a mid-season transfer means two rows; keep them separate
    #  so the Judge can verify numbers against the original data)
    player_name = matches[0]
    player_rows = rows.xs(player_name, level="player")
    records = []
    for idx, row in player_rows.iterrows():
        team = idx[-1] if isinstance(idx, tuple) else idx  # if tuple, take the last part (team)
        stats = {f"{c[0]}_{c[1]}" if c[1] else c[0]: v for c, v in row.items()}
        records.append({"team": team, "stats": stats})

    return {
        "player": player_name,
        "season": season,
        "competition": competition,
        "records": records,  # length 1 for one team, 2+ if transferred mid-season
    }