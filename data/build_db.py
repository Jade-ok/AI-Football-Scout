"""Build data/stats.db from the FBref cache.

Run occasionally (new season, new stat tables): python data/build_db.py
Everyday reads go through loader.py — this script only rebuilds the DB.
"""

import sqlite3
from pathlib import Path

import soccerdata as sd

DB_PATH = Path(__file__).parent / "stats.db"


def build():
    fbref = sd.FBref(leagues="ENG-Premier League", seasons="2425")
    conn = sqlite3.connect(DB_PATH)

    # --- players table (standard stats) ---
    df = fbref.read_player_season_stats(stat_type="standard").reset_index()
    players = df[[("player", ""), ("team", ""), ("pos", ""), ("age", ""),
                  ("Playing Time", "Min"), ("Performance", "Gls"),
                  ("Performance", "Ast"), ("Per 90 Minutes", "G+A"),
                  ("Performance", "PK")]].copy()
    players.columns = ["name", "team", "position", "age", "minutes",
                       "goals", "assists", "ga_per90", "pk"]
    players.to_sql("players", conn, if_exists="replace", index=False)

    # --- defense table (from misc stats) ---
    df_misc = fbref.read_player_season_stats(stat_type="misc").reset_index()
    defense = df_misc[[("player", ""), ("team", ""), ("90s", ""),
                       ("Performance", "TklW"), ("Performance", "Int"),
                       ("Performance", "Fls"), ("Performance", "CrdY")]].copy()
    defense.columns = ["name", "team", "nineties",
                       "tackles_won", "interceptions", "fouls", "yellow_cards"]
    defense.to_sql("defense", conn, if_exists="replace", index=False)

    for t in ("players", "defense"):
        print(t, conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone())
    conn.close()


if __name__ == "__main__":
    build()