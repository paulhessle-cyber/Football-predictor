#!/usr/bin/env python3
"""Fill in what actually happened for a previously logged prediction.

Example:
    python scripts/settle_result.py --match-id 3 --actual 1
    python scripts/settle_result.py --match-id 4 --actual 0.75   # AH half-win
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from football_predictor.results_log import settle_result

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--match-id", required=True, type=int)
    parser.add_argument("--actual", required=True, type=float, help="1/0, or a fractional AH settlement")
    parser.add_argument("--results-path", type=Path, default=REPO_ROOT / "logs" / "results_log.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        row = settle_result(args.results_path, args.match_id, args.actual)
    except KeyError as exc:
        print(exc)
        return 1
    print(f"Settled #{row['match_id']}: {row['home_team']} v {row['away_team']} — actual={row['actual']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
