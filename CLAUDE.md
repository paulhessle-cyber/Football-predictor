# Football Predictor — Project Brief

## What this is

A football match predictor focused on English lower leagues: League One,
League Two, and the National League. The premise: these markets get a
fraction of the volume and sharp-money attention that the Premier League and
Championship do, so bookmaker prices can sit "wrong" for longer, especially
on markets like Asian handicaps rather than just match result. The trade-off
is worse data availability the further down you go (no xG, patchy corners/
cards data), so the edge has to come from diligence, not better data than
the market.

This is a new, standalone project — not part of the Racer/Formintel repo,
even though it reuses a lot of that project's patterns (see below).

## Prior art: Formintel

Formintel is a UK/Irish horse racing prediction suite (github.com/
paulhessle-cyber/Racer) built by the same person maintaining this project.
Worth mirroring its structure rather than reinventing:

- Composite scoring model blending historical form signals with market
  (odds) signals, rather than treating either as sufficient alone
- Model trained on a Windows PC from historical data, served via a
  Node.js backend on a DigitalOcean droplet
- Static frontend (GitHub Pages style), with **Safari iOS compatibility
  as a hard constraint** — this predictor will primarily be used from
  iPhone/iPad
- Confidence-banded predictions with a results log, feeding back into
  calibration once enough predictions have settled (Formintel uses Platt
  calibration once 30+ results are logged) — plan for the same feedback
  loop here rather than a static one-shot model
- UK conventions throughout (dates, terminology)

## Prediction targets

1. Match result (1X2)
2. Over/under goals (2.5 as the baseline line)
3. Asian handicap
4. Corners and cards — **phase 2**, see data gap below

## Data sources

### Historical training data: football-data.co.uk

Free CSVs, no API key needed. This plays the same role rpscrape plays for
Formintel's horse racing data.

- URL pattern: `https://www.football-data.co.uk/mmz4281/{season}/{div}.csv`
  - Season format: `2526` for 2025/26, `2425` for 2024/25, etc.
  - Division codes: `E2` = League One, `E3` = League Two, `EC` = National
    League (also `E0` = Premier League, `E1` = Championship, if ever useful
    for comparison)
- Coverage: League One and League Two go back to the 1990s; National
  League coverage only starts 2005/06
- 78 columns per match, including:
  - Result and half-time score (`FTHG`, `FTAG`, `FTR`, `HTHG`, `HTAG`, `HTR`)
  - Shots, shots on target, fouls, corners, cards (`HS`/`AS`, `HST`/`AST`,
    `HF`/`AF`, `HC`/`AC`, `HY`/`AY`, `HR`/`AR`)
  - Referee
  - Opening + closing odds from 9+ bookmakers (Bet365, Pinnacle, Betfair
    Exchange, William Hill, etc.) across three markets: match result,
    over/under 2.5 goals, and Asian handicap
  - `Max`/`Avg` market-consensus columns for each market (max/average
    price across all bookmakers) — useful as a single "market opinion"
    feature without picking one bookmaker
  - Closing-price columns are suffixed `C` (e.g. `B365CH` is Bet365's
    closing home price vs `B365H` opening)

**Data gap to plan around:** there is no corners/cards odds data in this
file at all — only match result, O/U 2.5, and Asian handicap markets are
covered. A corners/cards model needs a logged-results history built up
over time from this project's own predictions, the same way Formintel's
Placepot/Lucky 15 features needed real logged data before calibration was
possible. Don't try to backtest corners/cards against historical odds —
there's nothing to backtest against yet.

A 10-match raw + cleaned sample from League Two (`E3`, 2025/26 opening
weekend) was already pulled and inspected in a prior session, but not
saved into this repo — re-pull a full season as the first real step.

### Live data (fixtures, injuries, news) — not yet chosen

API-Football has a usable free tier (100 requests/day) with fixtures,
injuries, lineups, and even a predictions endpoint, if useful as a starting
point for later phases. Nothing has been committed to yet — decide once
the historical model is validated.

## Open decision: news/story impact

Wanted: daily news and stories (injuries, manager changes, etc.) should be
able to move a prediction. **Mechanism is deliberately undecided** — don't
build an automated scraping/NLP layer as a first step. Two realistic paths
discussed:

1. **Manual flags** — a few tags entered by hand daily (e.g. "key striker
   out: -0.15", "new manager bounce: +0.1"), model just needs a slot to
   apply the weight. Ships fast, produces real logged data to prove
   whether news actually moves ROI.
2. **Automated tagging** — pull team news/injury feeds, run each item
   through an LLM to get a structured impact tag, tune the weights against
   logged results (same pattern as Formintel's Platt calibration).

Plan: build the manual-flag stub first, prove it changes outcomes using the
results log, then justify automating.

## Validate the premise before building on top of it

Before investing in feature engineering or a full model, check whether the
"lower leagues are priced softer" premise actually holds in the data:
compute market-implied probability (from `Avg` odds columns) vs. actual
results per league (League One vs Two vs National League) and see where
the calibration gap is largest. Build the model on whichever league(s)
show it, rather than assuming all three qualify equally.

## Person/environment context

- Works primarily from iPhone/iPad Safari; Windows PC for data processing
  and model training — same split as Formintel
- Comfortable with Python, JavaScript, Linux/SSH, DigitalOcean deployment
- Also runs Formintel and a separate stack of trading/alerting bots — reuse
  patterns from those where sensible rather than reinventing (e.g. odds
  proxy design, systemd services on the droplet, results-log/checker UI
  pattern)

## Suggested first task

Scaffold a Python data pipeline that pulls football-data.co.uk CSVs for
League One, League Two, and National League into a local `data/` folder,
then run the market-calibration check above (implied probability vs.
actual result, per league) before writing any model code.

## Status

The data pipeline and calibration-check scaffold (`src/football_predictor/`,
`scripts/`) exist — see `README.md` for how to run them.

### First calibration run (2015/16–2025/26 seasons, ~3,600–3,750 matches/league)

| Division | League | Market | ECE | Brier | n |
|---|---|---|---|---|---|
| E2 | League One | 1x2 | **0.0204** | 0.2022 | 3712 |
| EC | National League | 1x2 | 0.0101 | 0.2024 | 3642 |
| E3 | League Two | ou25 | 0.0091 | 0.2440 | 3752 |
| E2 | League One | ou25 | 0.0088 | 0.2457 | 3712 |
| E3 | League Two | 1x2 | 0.0081 | 0.2105 | 3752 |
| EC | National League | ou25 | 0.0032 | 0.2449 | 3642 |

**Reading:** on match result (1X2) and over/under 2.5 goals — the two most
heavily-bet markets — the market is well-calibrated everywhere. Every ECE is
under 2.1 percentage points, and Brier scores are nearly identical across
all three leagues. This is *not* the pattern the premise predicted: League
One (arguably the "sharpest" of the three) shows the largest 1X2 gap, and
National League (expected to be the softest) has the *smallest* O/U 2.5 gap
of the three. On these two markets alone, "lower leagues are priced softer"
doesn't hold.

**This doesn't kill the premise, because it hasn't been tested on the
market the premise actually named:** the brief specifically flagged Asian
handicap as the market expected to be softer ("especially on markets like
Asian handicaps rather than just match result") — 1X2 and O/U 2.5 are the
most liquid, most scrutinized markets even several divisions down, so
efficient pricing there isn't surprising.

### Asian handicap calibration — implemented, not yet run

`calibration.py` now has an `ah` market: fair probability from
`AvgAHH`/`AvgAHA` (closing `AvgCAHH`/`AvgCAHA` preferred if present) against
the market-average line (`AHh`). Quarter-ball lines are split into their two
neighbouring half/whole lines and settled independently (half win = 0.75,
push = 0.5, etc — standard AH settlement fractions), so it's not just a
simplified binary win/loss check.

**Next step, before writing any model code:** run
`scripts/run_calibration.py` again (now includes `ah` by default) against
real data and record the result here. If AH also comes back well-calibrated
across all three leagues, the premise as stated doesn't hold and the
project needs a different edge hypothesis rather than pushing ahead on
League One 1X2 just because it had the largest number in the first run.
Also worth checking the per-bin CSVs/plots in `outputs/` for localized bias
(e.g. classic favourite–longshot bias) that a single pooled ECE number can
hide, before drawing conclusions from any of these tables.
