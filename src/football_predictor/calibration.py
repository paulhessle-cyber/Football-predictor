"""Market-calibration check: does the market-implied probability match the
actual outcome frequency, and does the gap differ by league?

This is deliberately the *first* thing to run against real data (per the
project brief) — before any model code — to check whether the "lower
leagues are priced softer" premise actually holds, and if so, in which
league(s).

Method: take the market's average odds, strip the overround out to get a
"fair" implied probability per outcome, then bin all (predicted probability,
did-it-happen) pairs into equal-width buckets and compare the bucket's mean
predicted probability against the bucket's actual frequency. A well-priced
market has predicted ≈ actual in every bucket (small Expected Calibration
Error / ECE); a mispriced market shows a persistent gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

MarketColumns = tuple[str, ...]

MARKETS: dict[str, dict] = {
    "1x2": {
        "outcome_names": ("H", "D", "A"),
        "odds_candidates": [
            ("AvgCH", "AvgCD", "AvgCA"),
            ("AvgH", "AvgD", "AvgA"),
        ],
    },
    "ou25": {
        "outcome_names": ("Over", "Under"),
        "odds_candidates": [
            ("AvgC>2.5", "AvgC<2.5"),
            ("Avg>2.5", "Avg<2.5"),
        ],
    },
}


def pick_odds_columns(
    columns: pd.Index, candidates: list[MarketColumns]
) -> MarketColumns | None:
    """First fully-present column tuple from `candidates` (closing odds
    preferred, then opening) — or None if this DataFrame has neither."""
    for candidate in candidates:
        if all(col in columns for col in candidate):
            return candidate
    return None


def implied_probabilities(odds: pd.DataFrame) -> pd.DataFrame:
    """Overround-adjusted ("fair") implied probability per outcome column."""
    raw = 1.0 / odds
    overround = raw.sum(axis=1)
    return raw.div(overround, axis=0)


def _actual_outcomes_1x2(df: pd.DataFrame) -> pd.DataFrame:
    ftr = df["FTR"]
    return pd.DataFrame(
        {
            "H": (ftr == "H").astype(float),
            "D": (ftr == "D").astype(float),
            "A": (ftr == "A").astype(float),
        },
        index=df.index,
    )


def _actual_outcomes_ou25(df: pd.DataFrame) -> pd.DataFrame:
    total_goals = df["FTHG"] + df["FTAG"]
    return pd.DataFrame(
        {
            "Over": (total_goals > 2.5).astype(float),
            "Under": (total_goals < 2.5).astype(float),
        },
        index=df.index,
    )


_ACTUAL_OUTCOME_FUNCS = {
    "1x2": _actual_outcomes_1x2,
    "ou25": _actual_outcomes_ou25,
}


def build_long_frame(df: pd.DataFrame, market: str) -> tuple[pd.DataFrame, MarketColumns] | None:
    """Long-format (predicted_prob, actual) pairs, one row per outcome per
    match, for matches where the odds and result are both present.

    Returns None if this DataFrame has no usable odds columns for `market`.
    """
    spec = MARKETS[market]
    odds_cols = pick_odds_columns(df.columns, spec["odds_candidates"])
    if odds_cols is None:
        return None

    required = list(odds_cols) + (["FTR"] if market == "1x2" else ["FTHG", "FTAG"])
    usable = df.dropna(subset=required).copy()
    if usable.empty:
        return None

    odds = usable[list(odds_cols)].astype(float)
    fair = implied_probabilities(odds)
    fair.columns = spec["outcome_names"]

    actual = _ACTUAL_OUTCOME_FUNCS[market](usable)

    long_rows = []
    for outcome in spec["outcome_names"]:
        long_rows.append(
            pd.DataFrame(
                {
                    "predicted_prob": fair[outcome].to_numpy(),
                    "actual": actual[outcome].to_numpy(),
                }
            )
        )
    long_df = pd.concat(long_rows, ignore_index=True)
    return long_df, odds_cols


@dataclass
class CalibrationReport:
    market: str
    odds_columns_used: MarketColumns
    n_matches: int
    n_outcome_rows: int
    bins: pd.DataFrame
    ece: float
    brier_score: float
    log_loss: float
    notes: list[str] = field(default_factory=list)


def expected_calibration_error(long_df: pd.DataFrame, n_bins: int = 10) -> tuple[pd.DataFrame, float]:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_idx = np.clip(np.digitize(long_df["predicted_prob"], edges[1:-1]), 0, n_bins - 1)

    rows = []
    n_total = len(long_df)
    ece = 0.0
    for b in range(n_bins):
        mask = bin_idx == b
        n = int(mask.sum())
        if n == 0:
            rows.append(
                {
                    "bin_lo": edges[b],
                    "bin_hi": edges[b + 1],
                    "n": 0,
                    "mean_predicted": np.nan,
                    "actual_frequency": np.nan,
                    "gap": np.nan,
                }
            )
            continue
        mean_pred = long_df.loc[mask, "predicted_prob"].mean()
        actual_freq = long_df.loc[mask, "actual"].mean()
        gap = actual_freq - mean_pred
        ece += (n / n_total) * abs(gap)
        rows.append(
            {
                "bin_lo": edges[b],
                "bin_hi": edges[b + 1],
                "n": n,
                "mean_predicted": mean_pred,
                "actual_frequency": actual_freq,
                "gap": gap,
            }
        )
    return pd.DataFrame(rows), ece


def calibration_report(df: pd.DataFrame, market: str, n_bins: int = 10) -> CalibrationReport | None:
    built = build_long_frame(df, market)
    if built is None:
        return None
    long_df, odds_cols = built

    bins, ece = expected_calibration_error(long_df, n_bins=n_bins)

    p = long_df["predicted_prob"].clip(1e-6, 1 - 1e-6)
    y = long_df["actual"]
    brier = float(((p - y) ** 2).mean())
    log_loss = float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())

    n_outcomes = len(MARKETS[market]["outcome_names"])
    return CalibrationReport(
        market=market,
        odds_columns_used=odds_cols,
        n_matches=len(long_df) // n_outcomes,
        n_outcome_rows=len(long_df),
        bins=bins,
        ece=ece,
        brier_score=brier,
        log_loss=log_loss,
    )
