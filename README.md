# Football Predictor

Match predictor for English lower leagues (League One, League Two, National
League), built on the premise that these markets are priced softer than the
Premier League/Championship. See [`CLAUDE.md`](./CLAUDE.md) for the full
project brief.

**Current stage: the premise doesn't hold as stated — deciding what's next.**
The calibration check below has now been run against real data on all three
markets (see `CLAUDE.md` → Status): every league is well-priced on match
result, over/under 2.5 goals, *and* Asian handicap (ECE under 2.1pp
everywhere; National League is in fact the best-calibrated league on two of
the three markets, the opposite of what the premise predicted). Don't build
a model on raw odds-mispricing in any single league based on this data —
see `CLAUDE.md` for the two honest ways to proceed from here.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 1. Fetch historical data

Pulls free CSVs from football-data.co.uk for League One (`E2`), League Two
(`E3`) and National League (`EC`) into `data/raw/`.

```bash
python scripts/fetch_data.py --start-year 2015 --end-year 2025
```

- `--divisions E2 E3 EC` to change which leagues (default: all three)
- `--force` to re-download files that already exist
- National League ("EC") has no data before 2005/06 — earlier seasons are
  skipped automatically, not treated as an error

## 2. Check market calibration

Computes the market's overround-adjusted implied probability from the `Avg`
odds columns (closing odds preferred, falls back to opening) and compares it
against what actually happened, per league.

```bash
python scripts/run_calibration.py --divisions E2 E3 EC --plot
```

Outputs (in `outputs/`):
- `calibration_summary.csv` — one row per league/market, sorted by
  **ECE** (Expected Calibration Error) descending
- `{division}_{market}_calibration.csv` — the underlying probability-bucket
  breakdown
- `plots/{division}_{market}.png` — reliability diagram, if `--plot` is passed

**ECE** is the size of the gap between the market's implied probability and
the actual outcome frequency, pooled across probability buckets. A
well-priced market has ECE close to 0; a bigger ECE means the market's odds
tracked reality less well — i.e. more potential edge. Compare the ECE across
League One / Two / National League to see where (if anywhere) the "lower
leagues are priced softer" premise actually holds, per the brief. Build the
model on whichever league(s) show it.

Markets covered: match result (`1x2`), over/under 2.5 goals (`ou25`), and
Asian handicap (`ah`) — using the market-average line (`AHh`) and
`AvgAHH`/`AvgAHA` (or closing `AvgCAHH`/`AvgCAHA` if present). Quarter-ball
lines (e.g. -0.25) are split into their two neighbouring half/whole lines
and settled independently, so a "half win" settles as 0.75 and a push as
0.5, matching standard Asian handicap settlement conventions — see
`_settle_handicap_line` / `_split_handicap_lines` in `calibration.py`.

## A note on this environment

This scaffold was built and unit-tested in a sandbox whose network policy
blocks football-data.co.uk. All real data pulls and calibration runs
happened on an unrestricted machine — see `CLAUDE.md` → Status for the
results.

## Project layout

```
src/football_predictor/
  config.py       # division codes, season-code generation
  fetch.py        # download CSVs from football-data.co.uk
  load.py         # concatenate a division's CSVs into one DataFrame
  calibration.py  # implied-probability + Expected Calibration Error
scripts/
  fetch_data.py       # CLI for step 1
  run_calibration.py  # CLI for step 2
tests/            # offline unit tests (no network required)
```

## Tests

```bash
pytest
```

All tests run against synthetic fixtures — no network access required.
