#!/usr/bin/env python3
"""Add a manual news/injury flag for an upcoming match.

Example:
    python scripts/add_flag.py --match-date 2026-09-27 --division E3 \\
        --home "Salford City" --away "Grimsby Town" --market 1x2 --outcome H \\
        --adjustment -0.15 --reason "Key striker out injured"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from football_predictor.calibration import MARKETS
from football_predictor.flags import add_flag

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--match-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--division", required=True)
    parser.add_argument("--home", required=True, dest="home_team")
    parser.add_argument("--away", required=True, dest="away_team")
    parser.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    parser.add_argument("--outcome", required=True, help="e.g. H/D/A, Over/Under, Home/Away")
    parser.add_argument("--adjustment", required=True, type=float, help="e.g. -0.15")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--flags-path", type=Path, default=REPO_ROOT / "logs" / "flags.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outcome_names = MARKETS[args.market]["outcome_names"]
    if args.outcome not in outcome_names:
        print(f"--outcome must be one of {outcome_names} for market {args.market!r}")
        return 1

    row = add_flag(
        args.flags_path,
        args.match_date,
        args.division,
        args.home_team,
        args.away_team,
        args.market,
        args.outcome,
        args.adjustment,
        args.reason,
    )
    print(
        f"Logged flag #{row['flag_id']}: {row['home_team']} v {row['away_team']} "
        f"({row['market']}/{row['outcome']}) {row['adjustment']:+.2f} — {row['reason']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
