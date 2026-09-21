"""Manual news/injury-flag store.

Per the project brief: a few hand-entered tags per match (e.g. "key striker
out: -0.15") that nudge a market-implied probability, rather than an
automated scraping/NLP layer. This is deliberately the whole mechanism for
now — the brief's plan is to prove flags move outcomes via the results log
(see results_log.py) before ever justifying automating tagging.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

FLAG_COLUMNS = [
    "flag_id",
    "date_added",
    "match_date",
    "division",
    "home_team",
    "away_team",
    "market",
    "outcome",
    "adjustment",
    "reason",
]


def load_flags(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=FLAG_COLUMNS)
    df = pd.read_csv(path)
    for col in ("date_added", "match_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce").astype("datetime64[ns]")
    return df


def add_flag(
    path: Path,
    match_date: str,
    division: str,
    home_team: str,
    away_team: str,
    market: str,
    outcome: str,
    adjustment: float,
    reason: str,
) -> pd.Series:
    """Append one hand-entered flag and return it as a row."""
    path = Path(path)
    existing = load_flags(path)
    flag_id = int(existing["flag_id"].max()) + 1 if not existing.empty else 1
    row = {
        "flag_id": flag_id,
        "date_added": pd.Timestamp(date.today()),
        "match_date": pd.Timestamp(match_date),
        "division": division,
        "home_team": home_team,
        "away_team": away_team,
        "market": market,
        "outcome": outcome,
        "adjustment": float(adjustment),
        "reason": reason,
    }
    updated = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(path, index=False)
    return pd.Series(row)


def flags_for_match(
    flags_df: pd.DataFrame,
    match_date: str,
    division: str,
    home_team: str,
    away_team: str,
    market: str,
    outcome: str,
) -> pd.DataFrame:
    """Every flag matching this exact (match, market, outcome). A flag that
    should affect more than one market/outcome is entered once per — kept
    deliberately simple rather than modelling cross-market spillover."""
    if flags_df.empty:
        return flags_df
    target_date = pd.Timestamp(match_date)
    mask = (
        (flags_df["match_date"] == target_date)
        & (flags_df["division"] == division)
        & (flags_df["home_team"] == home_team)
        & (flags_df["away_team"] == away_team)
        & (flags_df["market"] == market)
        & (flags_df["outcome"] == outcome)
    )
    return flags_df.loc[mask]


__all__ = ["FLAG_COLUMNS", "add_flag", "flags_for_match", "load_flags"]
