#!/usr/bin/env python3
"""Log a prediction for an upcoming match: computes the market's fair
implied probability from the odds you give it, applies any matching manual
flags, and stores both — so flag impact can be evaluated later without
needing a full model.

Example (1X2, home win):
    python scripts/log_prediction.py --match-date 2026-09-27 --division E3 \\
        --home "Salford City" --away "Grimsby Town" --market 1x2 --outcome H \\
        --odds 2.10 3.30 3.60
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from football_predictor.calibration import MARKETS, odds_to_fair_probabilities
from football_predictor.results_log import log_prediction

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--match-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--division", required=True)
    parser.add_argument("--home", required=True, dest="home_team")
    parser.add_argument("--away", required=True, dest="away_team")
    parser.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    parser.add_argument("--outcome", required=True, help="Must be one of this market's outcome names")
    parser.add_argument(
        "--odds",
        required=True,
        nargs="+",
        type=float,
        help="Current odds for every outcome in this market's order, e.g. H D A for 1x2",
    )
    parser.add_argument("--results-path", type=Path, default=REPO_ROOT / "logs" / "results_log.csv")
    parser.add_argument("--flags-path", type=Path, default=REPO_ROOT / "logs" / "flags.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outcome_names = MARKETS[args.market]["outcome_names"]
    if args.outcome not in outcome_names:
        print(f"--outcome must be one of {outcome_names} for market {args.market!r}")
        return 1
    if len(args.odds) != len(outcome_names):
        print(f"--odds needs {len(outcome_names)} values (one per {outcome_names}), got {len(args.odds)}")
        return 1

    fair = odds_to_fair_probabilities(*args.odds)
    market_prob = fair[outcome_names.index(args.outcome)]

    row = log_prediction(
        args.results_path,
        args.flags_path,
        args.match_date,
        args.division,
        args.home_team,
        args.away_team,
        args.market,
        args.outcome,
        market_prob,
    )
    print(
        f"Logged prediction #{row['match_id']}: {row['home_team']} v {row['away_team']} "
        f"({row['market']}/{row['outcome']}) market={row['market_prob']:.3f} "
        f"flag={row['flag_adjustment']:+.3f} -> predicted={row['predicted_prob']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
