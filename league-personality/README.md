# League Personality

Do the top five European soccer leagues actually play differently? This
repository holds the data, the collection scripts and the analysis workbook
behind a research project for MERO 5013 (Research Design and Methodology,
Oklahoma State University, Fall 2026) that tests the league stereotypes
(English = physical, Spanish = technical, German = pressing) with match data.

## Headline result

One-way ANOVA on PPDA (passes allowed per defensive action) across the five
leagues, 2023/24 season, 1,752 matches stacked to 3,504 team-level rows:

- F = 9.08, p < 0.001, eta squared = 1.04% (trimmed, PPDA <= 40)
- The leagues do differ, but league membership explains only about 1% of
  pressing variation: a tendency, not a rule.
- The folklore flips: La Liga presses the most, the Bundesliga the least.

## Repository layout

```
data/        collected CSVs (Understat and FBref, 2023/24, top five leagues)
scripts/     Python scripts that collect and analyse the data
analysis/    LibreOffice workbooks and charts
```

Key files:

- `data/understat_team_matches.csv` - one row per match with home/away PPDA;
  the input to the ANOVA
- `data/understat_player_season.csv` - player goals, xG, minutes; the input to
  the finishing-outlier analysis
- `scripts/collect_league_data_v3.py` - pulls everything from Understat and
  FBref via the open-source `soccerdata` package
- `scripts/analyze_outliers_v1.py` - z-score outlier analysis of finishing
  (goals minus xG per 90)
- `analysis/finishing_outliers_workbook.xlsx` - the outlier homework workbook

## How to reproduce

1. Install Python 3.9+ and the dependencies:

   ```
   pip install soccerdata pandas matplotlib
   ```

2. Re-collect the data (or use the CSVs in `data/` as-is):

   ```
   python scripts/collect_league_data_v3.py
   ```

3. Rerun the outlier analysis:

   ```
   python scripts/analyze_outliers_v1.py
   ```

4. The ANOVA was built by hand in LibreOffice Calc (no black-box dialog):
   league means, sums of squares, the F ratio via `F.DIST.RT`, and an SST
   check (SSB + SSW = SST). The workbook is included in `analysis/`.

## Data sources

- [Understat](https://understat.com) - shots, goals, xG, PPDA
- [FBref](https://fbref.com) (StatsBomb/Opta data) - team and player match stats

Both are public sites; the `soccerdata` package standardises access to them.
Collected November 2026 for the 2023/24 season.

## Author

Mohammad Fahim Shahriar - MERO 5013, Oklahoma State University
