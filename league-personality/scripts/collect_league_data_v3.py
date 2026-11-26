"""
collect_league_data_v3.py
=========================
VERSION HISTORY
  v1  First version. Used old FBref stat_type names (passing, passing_types,
      defensive_actions, possession) that no longer exist in soccerdata
      2026.x -> 4 of 5 team tables failed.
  v2  Fixed stat_type names to the current five: standard, keeper,
      shooting, playing_time, misc. Ran successfully; produced 7 CSVs,
      all team-level season aggregates plus schedules.
  v3  THIS VERSION - "everything the sources offer":
      * FBref PLAYER season stats (5 stat types)  -> 5 new CSVs
      * FBref team match-level stats (keeper, shooting, misc) -> 3 new CSVs
      * FBref opponent versions of the 5 team season tables -> 5 new CSVs
        (what teams ALLOWED: fouls drawn against you, cards conceded, etc.)
      * Understat team match stats, player season stats            -> 2 new CSVs
      * Per-match data (FBref lineups/events/player-match-stats,
        Understat shot events / player match stats) is available in the
        same package but is scraped GAME BY GAME, so it is behind a
        switch: N_MATCH_DETAIL. Default 0 (skip). Set to e.g. 10 to
        test the machinery on 10 games; scraping all 1756 games would
        take hours and risks a Cloudflare ban.

WHAT EACH NEW FILE GIVES YOU (the two-row-header CSVs need
header=[0,1] when you read them - see the notes at the bottom):

  fbref_player_standard.csv    every player's MP, Gls, Ast, per-90 rates
  fbref_player_shooting.csv    Sh, SoT, G/Sh per player
  fbref_player_misc.csv        per-player Fls, Fld, Int, TklW, Crs
  fbref_player_playing_time.csv
  fbref_player_keeper.csv      per-player keeper stats
  fbref_team_match_shooting.csv   shots per MATCH per team
  fbref_team_match_misc.csv       cards/fouls per MATCH per team
  fbref_team_match_keeper.csv     keeper numbers per MATCH
  fbref_standard_vs.csv      opponent-adjusted season tables (what a
  fbref_misc_vs.csv          team's opponents did against them)
  ..._vs.csv
  understat_team_matches.csv   team xG/goals per match, wide format
  understat_player_season.csv  player G, xG, A, xA, Sh, KP per season

HOW TO RUN:
  1. pip install soccerdata   (already done on your machine)
  2. python collect_league_data_v3.py
  3. CSVs land in ./data/<SEASON>/

Runtime: the season-level pulls are a few minutes (soccerdata caches,
so re-runs are fast). The per-match section, if enabled, costs roughly
20-40 seconds per match on top of that.
"""

import pathlib

import soccerdata as sd

# ----------------------------------------------------------------------
# 1. CONFIG
# ----------------------------------------------------------------------
SEASON = "2324"  # 2023/24. Other options: "2122", "2223", "2425"

LEAGUES = [
    "ENG-Premier League",
    "ESP-La Liga",
    "GER-Bundesliga",
    "ITA-Serie A",
    "FRA-Ligue 1",
]

# The five valid stat types in soccerdata 2026.x (v2 lesson learned).
STAT_TYPES = ["standard", "shooting", "misc", "playing_time", "keeper"]

# Per-match detail: 0 = skip (default), 10 = scrape the first 10 games.
# Each match costs ~20-40s and one page load per table.
N_MATCH_DETAIL = 0

OUT_DIR = pathlib.Path("data") / SEASON
OUT_DIR.mkdir(parents=True, exist_ok=True)


def save(df, name):
    """Save a DataFrame as CSV and print one summary line."""
    path = OUT_DIR / f"{name}.csv"
    df.to_csv(path)
    print(f"  saved {path}  ({len(df)} rows, {len(df.columns)} columns)")


def guarded(label, fn):
    """Run one pull; a failure prints and moves on instead of killing
    the run. (v1 lesson: one bad table should not lose the rest.)"""
    try:
        df = fn()
        save(df, label)
        return df
    except Exception as err:
        print(f"  ! {label} failed: {err}")
        return None


# ----------------------------------------------------------------------
# 2. FBref -- everything
# ----------------------------------------------------------------------
def collect_fbref():
    print("\n=== FBref ===")
    fbref = sd.FBref(leagues=LEAGUES, seasons=[SEASON])

    # 2a. Schedule: every game of the season.
    schedule = guarded("fbref_schedule", fbref.read_schedule)

    # 2b. Team SEASON aggregates, as in v2.
    for table in STAT_TYPES:
        guarded(f"fbref_{table}", lambda t=table: fbref.read_team_season_stats(stat_type=t))

    # 2c. NEW: opponent versions of the same tables. This is what teams
    #     ALLOWED - e.g. fouls committed by opponents, shots faced.
    for table in STAT_TYPES:
        guarded(
            f"fbref_{table}_vs",
            lambda t=table: fbref.read_team_season_stats(stat_type=t, opponent_stats=True),
        )

    # 2d. NEW: team MATCH-level stats (one row per team per game).
    for table in ["keeper", "shooting", "misc"]:
        guarded(f"fbref_team_match_{table}", lambda t=table: fbref.read_team_match_stats(stat_type=t))

    # 2e. NEW: PLAYER season stats, same five tables, one row per player.
    for table in STAT_TYPES:
        guarded(f"fbref_player_{table}", lambda t=table: fbref.read_player_season_stats(stat_type=t))

    # 2f. Per-match detail (off by default - see N_MATCH_DETAIL).
    if N_MATCH_DETAIL > 0 and schedule is not None:
        ids = schedule.index.get_level_values("game").unique()[:N_MATCH_DETAIL]
        print(f"  -- per-match detail for {len(ids)} game(s): {list(ids)}")
        for table in ["summary", "keepers"]:
            guarded(
                f"fbref_player_match_{table}",
                lambda t=table: fbref.read_player_match_stats(stat_type=t, match_id=list(ids)),
            )
        guarded("fbref_lineups", lambda: fbref.read_lineup(match_id=list(ids)))
        guarded("fbref_events", lambda: fbref.read_events(match_id=list(ids)))


# ----------------------------------------------------------------------
# 3. Understat -- everything
# ----------------------------------------------------------------------
def collect_understat():
    print("\n=== Understat ===")
    understat = sd.Understat(leagues=LEAGUES, seasons=[SEASON])

    # 3a. Schedule with match xG (the file you already have).
    schedule = guarded("understat_matches", understat.read_schedule)

    # 3b. NEW: team-level xG per match, wide format.
    guarded("understat_team_matches", understat.read_team_match_stats)

    # 3c. NEW: player season stats (G, xG, A, xA, Sh, KP...).
    guarded("understat_player_season", understat.read_player_season_stats)

    # 3d. Per-match detail (off by default).
    if N_MATCH_DETAIL > 0 and schedule is not None:
        ids = schedule["game_id"].unique()[:N_MATCH_DETAIL]
        print(f"  -- per-match detail for {len(ids)} game(s): {list(ids)}")
        guarded(
            "understat_shot_events",
            lambda: understat.read_shot_events(match_id=[int(i) for i in ids]),
        )
        guarded(
            "understat_player_matches",
            lambda: understat.read_player_match_stats(match_id=[int(i) for i in ids]),
        )


# ----------------------------------------------------------------------
# 4. RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    collect_fbref()
    collect_understat()
    print(f"\nDone. Files are in {OUT_DIR.resolve()}/")

# ----------------------------------------------------------------------
# NOTES ON READING THE OUTPUT
# ----------------------------------------------------------------------
# Every fbref_*.csv has a TWO-ROW header. To open one properly:
#
#   import pandas as pd
#   df = pd.read_csv("fbref_misc.csv", header=[0,1], index_col=[0,1,2])
#
# header=[0,1] tells pandas the first two rows are both header (FBref
# prints "Misc" on row 1 and "Fls", "Fld", "Int"... on row 2). Without
# it you get columns named "Unnamed: 1" and the data looks broken.
# index_col=[0,1,2] keeps league / season / team (or player) as the
# row labels.
#
# understat_*.csv files are flat single-row headers - no special
# handling needed.
