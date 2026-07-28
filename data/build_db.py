"""Build data/stats.db from the FBref cache.

Two tables:
  outfield  — 574 field players. standard + shooting + misc + playing_time,
              joined on name+team so one player is one row with attacking,
              shooting, defensive and playing-time stats side by side.
  keepers   — 44 goalkeepers. keeper + playing_time.

Run occasionally (new season, new stat tables): python data/build_db.py
Everyday reads go through loader.py — this script only rebuilds the DB.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import soccerdata as sd

DB_PATH = Path(__file__).parent / "stats.db"

# Which columns to keep from each stat_type, and what to rename them to.
# (source_column, output_name). Context columns (name, team, ...) are
# handled separately because they are the join keys.
STANDARD_COLS = [
    ("pos", "position"), ("age", "age"), ("nation", "nation"),
    ("Playing Time_Starts", "starts"), ("Playing Time_Min", "minutes"),
    ("Playing Time_90s", "nineties"),
    ("Performance_Gls", "goals"), ("Performance_Ast", "assists"),
    ("Performance_G+A", "goals_assists"), ("Performance_G-PK", "npg"),
    ("Performance_PK", "pk"), ("Performance_PKatt", "pk_att"),
    ("Performance_CrdY", "yellow"), ("Performance_CrdR", "red"),
    ("Per 90 Minutes_Gls", "goals_per90"),
    ("Per 90 Minutes_Ast", "assists_per90"),
    ("Per 90 Minutes_G+A", "ga_per90"),
    ("Per 90 Minutes_G-PK", "npg_per90"),
    ("Per 90 Minutes_G+A-PK", "npga_per90"),
]
SHOOTING_COLS = [
    ("Standard_Sh", "shots"), ("Standard_SoT", "shots_on_target"),
    ("Standard_SoT%", "shots_on_target_pct"),
    ("Standard_Sh/90", "shots_per90"), ("Standard_SoT/90", "sot_per90"),
    ("Standard_G/Sh", "goals_per_shot"), ("Standard_G/SoT", "goals_per_sot"),
]
MISC_COLS = [
    ("Performance_2CrdY", "second_yellow"), ("Performance_Fls", "fouls"),
    ("Performance_Fld", "fouled"), ("Performance_Off", "offsides"),
    ("Performance_Crs", "crosses"), ("Performance_Int", "interceptions"),
    ("Performance_TklW", "tackles_won"), ("Performance_OG", "own_goals"),
]
PLAYTIME_COLS = [
    ("Playing Time_Mn/MP", "min_per_match"),
    ("Playing Time_Min%", "min_pct"),
    ("Starts_Mn/Start", "min_per_start"), ("Starts_Compl", "complete_matches"),
    ("Subs_Subs", "sub_appearances"),
    ("Team Success_PPM", "points_per_match"),
    ("Team Success_+/-", "plus_minus"),
    ("Team Success_+/-90", "plus_minus_per90"),
    ("Team Success_On-Off", "on_off"),
]
KEEPER_COLS = [
    ("pos", "position"), ("age", "age"), ("nation", "nation"),
    ("Playing Time_Starts", "starts"), ("Playing Time_Min", "minutes"),
    ("Playing Time_90s", "nineties"),
    ("Performance_GA", "goals_against"),
    ("Performance_GA90", "goals_against_per90"),
    ("Performance_SoTA", "shots_on_target_against"),
    ("Performance_Saves", "saves"), ("Performance_Save%", "save_pct"),
    ("Performance_W", "wins"), ("Performance_D", "draws"),
    ("Performance_L", "losses"),
    ("Performance_CS", "clean_sheets"), ("Performance_CS%", "clean_sheet_pct"),
    ("Penalty Kicks_PKatt", "pk_faced"), ("Penalty Kicks_PKA", "pk_allowed"),
    ("Penalty Kicks_PKsv", "pk_saved"), ("Penalty Kicks_PKm", "pk_missed"),
]


def flatten(df):
    """FBref returns two-level columns like ('Performance', 'Gls').
    Flatten them to 'Performance_Gls' so we can select by one string.
    Context columns like ('pos', '') become just 'pos'.
    """
    df = df.reset_index()
    df.columns = [a if b == "" else f"{a}_{b}" for a, b in df.columns]
    return df


def pick(df, cols):
    """Keep only wanted columns and rename them. Missing ones are skipped
    with a warning so a column rename upstream does not kill the whole build.
    """
    out = {}
    for src, dst in cols:
        if src in df.columns:
            out[dst] = df[src]
        else:
            print(f"  ! missing column {src!r} -> skipped")
    return pd.DataFrame(out)


def build():
    fbref = sd.FBref(leagues="ENG-Premier League", seasons="2425")
    conn = sqlite3.connect(DB_PATH)

    # Read and flatten every stat type once.
    standard = flatten(fbref.read_player_season_stats(stat_type="standard"))
    shooting = flatten(fbref.read_player_season_stats(stat_type="shooting"))
    misc = flatten(fbref.read_player_season_stats(stat_type="misc"))
    playtime = flatten(fbref.read_player_season_stats(stat_type="playing_time"))
    keeper = flatten(fbref.read_player_season_stats(stat_type="keeper"))

    # --- outfield table ---
    # Context + standard is the base. The join key is name+team, which keeps
    # transfers split (a moved player has two rows, one per club).
    base = standard[["league", "season", "player", "team"]].copy()
    base.columns = ["competition", "season", "name", "team"]
    base = pd.concat([base, pick(standard, STANDARD_COLS)], axis=1)

    for df, cols in [(shooting, SHOOTING_COLS), (misc, MISC_COLS),
                     (playtime, PLAYTIME_COLS)]:
        keyed = df[["player", "team"]].copy()
        keyed.columns = ["name", "team"]
        keyed = pd.concat([keyed, pick(df, cols)], axis=1)
        base = base.merge(keyed, on=["name", "team"], how="left")

    base.to_sql("outfield", conn, if_exists="replace", index=False)

    # --- keepers table ---
    kbase = keeper[["league", "season", "player", "team"]].copy()
    kbase.columns = ["competition", "season", "name", "team"]
    kbase = pd.concat([kbase, pick(keeper, KEEPER_COLS)], axis=1)

    ptk = playtime[["player", "team"]].copy()
    ptk.columns = ["name", "team"]
    ptk = pd.concat([ptk, pick(playtime, PLAYTIME_COLS)], axis=1)
    kbase = kbase.merge(ptk, on=["name", "team"], how="left")

    kbase.to_sql("keepers", conn, if_exists="replace", index=False)

    for t in ("outfield", "keepers"):
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        cols = len(conn.execute(f"SELECT * FROM {t} LIMIT 1").description)
        print(f"{t}: {n} rows, {cols} columns")
    conn.close()


if __name__ == "__main__":
    build()