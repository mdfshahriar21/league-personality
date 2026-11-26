"""
analyze_outliers_v1.py
======================
VERSION HISTORY
  v1  THIS VERSION - first outlier analysis, on the finishing layer.
      Question: which players scored far more or far fewer goals than
      the quality of their chances (xG) predicts?

METHOD, one step at a time:
  1. Filter: keep players with >= 450 minutes and > 10 shots.
     WHY: a rate computed from a 20-minute cameo is arithmetic on
     noise. (Brandon Aguilera "30 fouls per 90" from 5 total minutes
     was the lesson from the misc table; same trap here.)
  2. Compute the gap: (goals - xG) per 90 minutes.
     WHY per 90: raw gaps just measure playing time.
     WHY the gap: xG is the model's estimate of what the shots were
     worth, so the gap is the part of scoring the model does NOT
     explain. That residual is where outliers live.
  3. Standardize: z = (gap - mean) / std, so the chart axis is in
     "how unusual is this player" units instead of raw goals.
  4. Flag and plot: |z| > 2 = unusual, |z| > 3 = extreme.
     Histogram with the outlier zones shaded, named players labeled.

INPUT:  understat_player_season.csv  (from collect_league_data_v3.py)
OUTPUT: outliers_z_scores.csv   - every player with their z-score
        outliers_histogram.png  - the labeled chart

HOW TO RUN:
  1. Put this script next to your data folder (data/2324/...) or edit
     INPUT_CSV below.
  2. python analyze_outliers_v1.py
"""

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
INPUT_CSV = pathlib.Path("data") / "2324" / "understat_player_season.csv"
OUT_DIR = pathlib.Path("output")
OUT_DIR.mkdir(exist_ok=True)

MIN_MINUTES = 450
MIN_SHOTS = 10

# ----------------------------------------------------------------------
# 1. LOAD + FILTER
# ----------------------------------------------------------------------
u = pd.read_csv(INPUT_CSV)
n_raw = len(u)
u = u[(u["minutes"] >= MIN_MINUTES) & (u["shots"] > MIN_SHOTS)].copy()
print(f"players: {n_raw} raw -> {len(u)} after the {MIN_MINUTES}-minute / "
      f"{MIN_SHOTS}-shot filter")

# ----------------------------------------------------------------------
# 2. THE GAP (goals - xG) PER 90
# ----------------------------------------------------------------------
u["gap_p90"] = (u["goals"] - u["xg"]) / u["minutes"] * 90

# Why standardize? The raw gap is in goals per 90, which mixes two
# questions: "did he overperform?" and "by how much relative to everyone
# else?". Dividing by the standard deviation answers the second one, so
# +2 means "two typical-player-widths above average", not "2 goals".
mu, sd = u["gap_p90"].mean(), u["gap_p90"].std()
u["z"] = (u["gap_p90"] - mu) / sd
print(f"mean gap = {mu:+.4f} goals/90 (the average player breaks even)")
print(f"std dev  = {sd:.4f} goals/90")
print(f"xG explains {100 * np.corrcoef(u['xg'], u['goals'])[0,1]**2:.0f}% "
      "of goal variance; outliers are the rest")

# ----------------------------------------------------------------------
# 3. FLAG + REPORT
# ----------------------------------------------------------------------
outliers = u[u["z"].abs() > 2].sort_values("z")
high = outliers[outliers["z"] > 2]
low = outliers[outliers["z"] < -2]
print(f"\noutliers beyond 2 SD: {len(high)} high (overfinishers), "
      f"{len(low)} low (underfinishers)")

cols = ["league", "player", "team", "minutes", "goals", "xg", "gap_p90", "z"]
print("\n-- most extreme underfinishers --")
print(low.head(8)[cols].round(2).to_string(index=False))
print("\n-- most extreme overfinishers --")
print(high.tail(8)[cols].round(2).to_string(index=False))

u.sort_values("z").to_csv(OUT_DIR / "outliers_z_scores.csv", index=False)

# ----------------------------------------------------------------------
# 4. THE CHART
# ----------------------------------------------------------------------
z = u["z"].values
fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=200)
bins = np.arange(np.floor(z.min()) - 0.5, np.ceil(z.max()) + 0.5, 0.25)
ax.hist(z, bins=bins, color="#5b8db8", edgecolor="white", linewidth=0.6)

# shaded outlier zones and the 2/3 SD fences
ax.axvspan(2, z.max() + 1, color="#f2c14e", alpha=0.25)
ax.axvspan(z.min() - 1, -2, color="#c0504d", alpha=0.18)
for x in [-3, -2, 2, 3]:
    ax.axvline(x, color="#555555", linewidth=1, linestyle="--", alpha=0.8)
ymax = ax.get_ylim()[1]
ax.text(2.08, ymax * 0.97, "+2 SD", color="#555555", fontsize=9, va="top")
ax.text(-2.08, ymax * 0.97, "-2 SD", color="#555555", fontsize=9,
        va="top", ha="right")

# label the eight named players (edit this dict to label others)
NAMED = {
    "Robin Hack": "+3.8 SD\n10 G from 4.6 xG",
    "Benjamin Sesko": "+3.4 SD\n14 G from 8.6 xG",
    "Michael Olise": "+3.2 SD\n10 G from 5.7 xG",
    "Alexander Sørloth": "+2.9 SD\n23 G from 15.4 xG",
    "Kaio Jorge": "-5.0 SD\n3 G from 7.7 xG",
    "Antonio Puertas": "-4.9 SD\n0 G from 4.0 xG",
    "Eric Maxim Choupo-Moting": "-4.5 SD\n2 G from 5.6 xG",
    "Kike García": "-4.4 SD\n3 G from 10.4 xG",
}
placed = {}
for name, label in sorted(NAMED.items(), key=lambda kv: -u.loc[u["player"] == kv[0], "z"].iloc[0]):
    x = u.loc[u["player"] == name, "z"].iloc[0]
    level = 0.42 + 0.16 * sum(1 for p in placed if abs(p - x) < 1.2)
    placed[x] = level
    ax.plot([x, x], [level * ymax * 0.62, level * ymax * 0.98],
            color="#333333", linewidth=0.8)
    ax.plot(x, level * ymax * 0.62, marker="o", markersize=4, color="#333333")
    ax.text(x, level * ymax, label, ha="center", va="bottom", fontsize=8,
            color="#222222")

ax.set_title("Finishing outliers: goals minus xG per 90, in standard deviations\n"
             f"Top-5 European leagues, 2023/24, players with {MIN_MINUTES}+ minutes "
             f"and {MIN_SHOTS}+ shots (n={len(u):,})", fontsize=13)
ax.set_xlabel("Standard deviations from the mean finishing performance (z-score)")
ax.set_ylabel("Number of players")
ax.set_xlim(z.min() - 1.7, z.max() + 1.7)
ax.spines[["top", "right"]].set_visible(False)
fig.text(0.99, 0.005, f"Source: {INPUT_CSV}, collected via soccerdata",
         ha="right", fontsize=8, color="#666666")

plt.tight_layout()
plt.savefig(OUT_DIR / "outliers_histogram.png", bbox_inches="tight")
print(f"\nsaved {OUT_DIR/'outliers_z_scores.csv'} and {OUT_DIR/'outliers_histogram.png'}")
