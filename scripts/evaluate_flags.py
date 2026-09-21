#!/usr/bin/env python3
"""Does the manual news/injury-flag adjustment actually help, or hurt?

Compares Brier score of flag-adjusted predictions against the market's
unadjusted baseline, on settled matches where a flag was applied. Needs at
least 30 settled+flagged results before it'll give a verdict (same
threshold Formintel uses for Platt calibration) — this is the check the
project brief asks for before ever justifying automating news tagging.

Example:
    python scripts/evaluate_flags.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from football_predictor.results_log import evaluate_flag_impact

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results-path", type=Path, default=REPO_ROOT / "logs" / "results_log.csv")
    parser.add_argument("--min-n", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = evaluate_flag_impact(args.results_path, min_n=args.min_n)

    if result["status"] == "insufficient_data":
        print(result["message"])
        return 0

    print(f"Flagged settled results: {result['n_flagged_settled']}")
    print(f"Unflagged settled results: {result['n_unflagged_settled']}")
    print(f"Baseline Brier (market odds alone): {result['baseline_brier']:.4f}")
    print(f"Flagged Brier (market odds + flag): {result['flagged_brier']:.4f}")
    if result["improvement"] > 0:
        verdict = "flags are helping"
    elif result["improvement"] < 0:
        verdict = "flags are hurting"
    else:
        verdict = "no difference"
    print(f"Improvement: {result['improvement']:+.4f} ({verdict})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
