"""Load raw football-data.co.uk CSVs into a single tidy DataFrame per division.

Column sets vary season to season (older seasons lack Max/Avg odds columns
entirely, or cover fewer bookmakers) — concatenation fills the gaps with NaN
rather than erroring, so calibration code must check for column presence
before using a given odds market.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .fetch import raw_csv_path

FILENAME_RE = re.compile(r"^(?P<division>[A-Z0-9]+)_(?P<season>\d{4})\.csv$")


def _read_one(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="latin1")
    match = FILENAME_RE.match(path.name)
    if match:
        df["Division"] = match.group("division")
        df["SeasonCode"] = match.group("season")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    return df


def load_division(data_dir: Path, division: str) -> pd.DataFrame:
    """Concatenate every downloaded season file for one division."""
    data_dir = Path(data_dir)
    paths = sorted(data_dir.glob(f"{division}_*.csv"))
    if not paths:
        raise FileNotFoundError(
            f"No CSVs for division {division!r} in {data_dir} — run fetch first."
        )
    frames = [_read_one(p) for p in paths]
    combined = pd.concat(frames, ignore_index=True, sort=False)
    if "Date" in combined.columns:
        combined = combined.sort_values("Date").reset_index(drop=True)
    return combined


def load_divisions(data_dir: Path, divisions: list[str]) -> dict[str, pd.DataFrame]:
    return {division: load_division(data_dir, division) for division in divisions}


__all__ = ["load_division", "load_divisions", "raw_csv_path"]
