#!/usr/bin/env python3
"""Market-calibration check: does market-implied probability track actual
results, and where is the gap largest?

Run this against real data *before* writing any model code (per the project
brief) — it decides which league(s) the "lower leagues are priced softer"
premise actually holds for.

Example:
    python scripts/run_calibration.py
    python scripts/run_calibration.py --divisions E2 E3 EC --markets 1x2 ou25
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from football_predictor.calibration import MARKETS, calibration_report
from football_predictor.config import DEFAULT_DIVISIONS, DIVISIONS
from football_predictor.load import load_division

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--divisions", nargs="+", default=list(DEFAULT_DIVISIONS))
    parser.add_argument("--markets", nargs="+", default=list(MARKETS.keys()))
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "outputs")
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument(
        "--plot", action="store_true", help="Also save a reliability-diagram PNG per league/market"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for division in args.divisions:
        try:
            df = load_division(args.data_dir, division)
        except FileNotFoundError as exc:
            print(f"[skip] {division}: {exc}")
            continue

        for market in args.markets:
            report = calibration_report(df, market, n_bins=args.bins)
            if report is None:
                print(f"[skip] {division}/{market}: no usable odds columns in this data")
                continue

            bins_path = args.output_dir / f"{division}_{market}_calibration.csv"
            report.bins.to_csv(bins_path, index=False)

            summary_rows.append(
                {
                    "division": division,
                    "league": DIVISIONS.get(division, division),
                    "market": market,
                    "odds_columns": "/".join(report.odds_columns_used),
                    "n_matches": report.n_matches,
                    "ece": report.ece,
                    "brier_score": report.brier_score,
                    "log_loss": report.log_loss,
                }
            )

            if args.plot:
                _save_plot(report, division, market, args.output_dir)

    if not summary_rows:
        print("\nNo calibration reports produced — run scripts/fetch_data.py first.")
        return 1

    import pandas as pd

    summary = pd.DataFrame(summary_rows).sort_values("ece", ascending=False)
    summary_path = args.output_dir / "calibration_summary.csv"
    summary.to_csv(summary_path, index=False)

    print("\nMarket calibration summary (largest gap first):\n")
    print(summary.to_string(index=False))
    print(f"\nSaved: {summary_path}")
    print(
        "\nECE (Expected Calibration Error) is the size of the gap between what the "
        "market's odds implied and what actually happened, pooled across probability "
        "buckets — higher means the market's prices tracked reality less closely."
    )
    return 0


def _save_plot(report, division: str, market: str, output_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bins = report.bins.dropna(subset=["mean_predicted", "actual_frequency"])
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="perfectly calibrated")
    ax.scatter(bins["mean_predicted"], bins["actual_frequency"], s=bins["n"] / bins["n"].max() * 200 + 20)
    ax.set_xlabel("Market-implied probability")
    ax.set_ylabel("Actual frequency")
    ax.set_title(f"{DIVISIONS.get(division, division)} — {market} (ECE={report.ece:.3f})")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(plots_dir / f"{division}_{market}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
