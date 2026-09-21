# Football Predictor

Match predictor for English lower leagues (League One, League Two, National
League), built on the premise that these markets are priced softer than the
Premier League/Championship. See [`CLAUDE.md`](./CLAUDE.md) for the full
project brief.

**Current stage: pivoted away from raw odds-mispricing.** The calibration
check below has been run against real data on all three markets (see
`CLAUDE.md` → Status): every league is well-priced on match result,
over/under 2.5 goals, *and* Asian handicap (ECE under 2.1pp everywhere).
"Lower leagues are priced softer" doesn't hold at this granularity, so
instead of building a model on that premise, the project is now building
the **manual news/injury-flag mechanism** the brief described as the
fallback — see step 3 below.

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

## 3. Manual news/injury flags

Per the brief: prove that hand-entered news tags (injuries, manager
changes, etc.) actually move outcomes *before* ever building automated
scraping/NLP tagging. This is the whole mechanism — a flag store, a
prediction log that applies matching flags on top of the market's baseline
probability, and an evaluator that compares Brier scores with vs without
the flag, the same way `calibration.py` evaluates market pricing.

```bash
# Tag something you've noticed about an upcoming match
python scripts/add_flag.py --match-date 2026-09-27 --division E3 \
    --home "Salford City" --away "Grimsby Town" --market 1x2 --outcome H \
    --adjustment -0.15 --reason "Key striker out injured"

# Log a prediction for that match (fetches fair prob from the odds you give
# it, then applies any flags matching this exact match/market/outcome)
python scripts/log_prediction.py --match-date 2026-09-27 --division E3 \
    --home "Salford City" --away "Grimsby Town" --market 1x2 --outcome H \
    --odds 2.10 3.30 3.60

# After the match is played, record what actually happened
# (1/0 for 1X2 and O/U; a fractional AH settlement — 0, 0.25, 0.5, 0.75, 1 — for ah)
python scripts/settle_result.py --match-id 1 --actual 0

# Once 30+ flagged results are settled, check whether the flags are helping
python scripts/evaluate_flags.py
```

State lives in `logs/flags.csv` and `logs/results_log.csv` — tracked in
git (unlike `data/`, this isn't regenerable from football-data.co.uk, it's
the project's own accumulating record) — so it's committed as you go,
same pattern as Formintel's results-log/checker workflow. `evaluate_flags.py`
refuses to give a verdict under 30 settled+flagged results (same threshold
Formintel uses before trusting its Platt calibration) — don't lower
`--min-n` to force an early answer, the point is not fooling yourself with
a handful of matches.

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
  flags.py        # manual news/injury-flag store
  results_log.py  # prediction/results log + flag-impact evaluation
scripts/
  fetch_data.py       # CLI for step 1
  run_calibration.py  # CLI for step 2
  add_flag.py          # CLI for step 3
  log_prediction.py    # CLI for step 3
  settle_result.py     # CLI for step 3
  evaluate_flags.py    # CLI for step 3
logs/             # flags.csv, results_log.csv -- tracked, accumulating state
tests/            # offline unit tests (no network required)
```

## Tests

```bash
pytest
```

All tests run against synthetic fixtures — no network access required.
