"""Prediction/results log.

Records the market's baseline probability, any manual-flag adjustment
applied on top of it, and (once the match is played) the actual outcome —
so flag impact can be *evaluated*, using the same Brier-score methodology
calibration.py uses for market pricing, instead of just asserted.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .flags import flags_for_match, load_flags

RESULTS_COLUMNS = [
    "match_id",
    "match_date",
    "division",
    "home_team",
    "away_team",
    "market",
    "outcome",
    "market_prob",
    "flag_adjustment",
    "predicted_prob",
    "actual",
    "logged_at",
    "settled_at",
]

# Matches the "30+ results" threshold Formintel uses before trusting its
# Platt calibration — same idea: don't draw a conclusion from a handful of
# matches.
MIN_RESULTS_FOR_VERDICT = 30


def load_results_log(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=RESULTS_COLUMNS)
    df = pd.read_csv(path)
    # An all-empty datetime column (e.g. no results settled yet) can get
    # inferred at second resolution by read_csv's date parsing, which then
    # rejects assigning a microsecond-precision timestamp later. Coerce
    # explicitly instead of relying on parse_dates' inference.
    for col in ("match_date", "logged_at", "settled_at"):
        df[col] = pd.to_datetime(df[col], errors="coerce").astype("datetime64[ns]")
    return df


def log_prediction(
    results_path: Path,
    flags_path: Path,
    match_date: str,
    division: str,
    home_team: str,
    away_team: str,
    market: str,
    outcome: str,
    market_prob: float,
) -> pd.Series:
    """Log a prediction for an upcoming match: the market's baseline
    probability plus whatever hand-entered flags apply to this exact
    (match, market, outcome). `actual` is left blank until settle_result()
    is called after the match is played.
    """
    results_path = Path(results_path)
    existing = load_results_log(results_path)

    flags_df = load_flags(flags_path)
    matching = flags_for_match(
        flags_df, match_date, division, home_team, away_team, market, outcome
    )
    flag_adjustment = float(matching["adjustment"].sum()) if not matching.empty else 0.0
    predicted_prob = float(np.clip(market_prob + flag_adjustment, 0.0, 1.0))

    match_id = int(existing["match_id"].max()) + 1 if not existing.empty else 1
    row = {
        "match_id": match_id,
        "match_date": pd.Timestamp(match_date),
        "division": division,
        "home_team": home_team,
        "away_team": away_team,
        "market": market,
        "outcome": outcome,
        "market_prob": float(market_prob),
        "flag_adjustment": flag_adjustment,
        "predicted_prob": predicted_prob,
        "actual": np.nan,
        "logged_at": pd.Timestamp(datetime.now()),
        "settled_at": pd.NaT,
    }
    updated = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(results_path, index=False)
    return pd.Series(row)


def settle_result(results_path: Path, match_id: int, actual: float) -> pd.Series:
    """Fill in what actually happened for a previously logged prediction.
    `actual` is 1.0/0.0 for 1X2 and O/U outcomes, or a fractional Asian
    handicap settlement value (0, 0.25, 0.5, 0.75, 1) for push/half-win
    lines — see calibration.py's `_settle_handicap_line`.
    """
    results_path = Path(results_path)
    df = load_results_log(results_path)
    mask = df["match_id"] == match_id
    if not mask.any():
        raise KeyError(f"No logged prediction with match_id={match_id}")
    df.loc[mask, "actual"] = float(actual)
    df.loc[mask, "settled_at"] = pd.Timestamp(datetime.now())
    df.to_csv(results_path, index=False)
    return df.loc[mask].iloc[0]


def evaluate_flag_impact(results_path: Path, min_n: int = MIN_RESULTS_FOR_VERDICT) -> dict:
    """Does applying the manual flag adjustment move predictions closer to
    what actually happened, or further away?

    Compares the Brier score of the flag-adjusted prediction against the
    market's unadjusted baseline, on settled matches where a flag was
    actually applied. Requires at least `min_n` such matches before
    returning a verdict rather than noise.
    """
    df = load_results_log(results_path)
    settled = df.dropna(subset=["actual"])
    flagged = settled[settled["flag_adjustment"] != 0]

    n = len(flagged)
    if n < min_n:
        return {
            "status": "insufficient_data",
            "n_flagged_settled": n,
            "min_required": min_n,
            "message": (
                f"{n}/{min_n} flagged results settled so far — "
                "not enough to draw a conclusion yet."
            ),
        }

    baseline_brier = float(((flagged["market_prob"] - flagged["actual"]) ** 2).mean())
    flagged_brier = float(((flagged["predicted_prob"] - flagged["actual"]) ** 2).mean())

    return {
        "status": "ok",
        "n_flagged_settled": n,
        "n_unflagged_settled": int((settled["flag_adjustment"] == 0).sum()),
        "baseline_brier": baseline_brier,  # market odds alone, ignoring the flag
        "flagged_brier": flagged_brier,  # market odds + flag adjustment
        "improvement": baseline_brier - flagged_brier,  # positive = flags are helping
    }


__all__ = [
    "MIN_RESULTS_FOR_VERDICT",
    "RESULTS_COLUMNS",
    "evaluate_flag_impact",
    "load_results_log",
    "log_prediction",
    "settle_result",
]
