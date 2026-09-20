#!/usr/bin/env python3
"""Download football-data.co.uk season CSVs.

Example:
    python scripts/fetch_data.py --start-year 2015 --end-year 2025
    python scripts/fetch_data.py --divisions E2 E3 --start-year 2020 --end-year 2025 --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from football_predictor.config import DEFAULT_DIVISIONS, season_codes
from football_predictor.fetch import fetch_many

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--divisions",
        nargs="+",
        default=list(DEFAULT_DIVISIONS),
        help=f"Division codes to fetch (default: {' '.join(DEFAULT_DIVISIONS)})",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2015,
        help="First season's start year, e.g. 2015 for 2015/16 (default: 2015)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2025,
        help="Last season's start year, e.g. 2025 for 2025/26 (default: 2025)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=REPO_ROOT / "data" / "raw",
        help="Directory to write CSVs into (default: data/raw)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if the file already exists"
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    seasons = season_codes(args.start_year, args.end_year)

    results = fetch_many(args.divisions, seasons, args.data_dir, force=args.force)

    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    print("\nSummary:", by_status)

    errors = [r for r in results if r.status == "error"]
    if errors:
        print("\nErrors:")
        for r in errors:
            print(f"  {r.division} {r.season}: {r.detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
