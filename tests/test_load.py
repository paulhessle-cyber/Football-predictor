from pathlib import Path

import pandas as pd
import pytest

from football_predictor.load import load_division


def _write_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def test_load_division_concatenates_seasons(tmp_path: Path):
    _write_csv(
        tmp_path / "E3_2324.csv",
        [{"Date": "12/08/2023", "FTR": "H", "AvgH": 2.0, "AvgD": 3.2, "AvgA": 3.8}],
    )
    _write_csv(
        tmp_path / "E3_2425.csv",
        [{"Date": "10/08/2024", "FTR": "A", "AvgH": 1.9, "AvgD": 3.4, "AvgA": 4.0}],
    )

    df = load_division(tmp_path, "E3")

    assert len(df) == 2
    assert list(df["SeasonCode"]) == ["2324", "2425"]
    assert df["Division"].unique().tolist() == ["E3"]
    assert df["Date"].is_monotonic_increasing


def test_load_division_handles_missing_columns_across_seasons(tmp_path: Path):
    # Older season has no Avg odds columns at all.
    _write_csv(tmp_path / "E2_1516.csv", [{"Date": "08/08/2015", "FTR": "D"}])
    _write_csv(
        tmp_path / "E2_2425.csv",
        [{"Date": "10/08/2024", "FTR": "H", "AvgH": 2.1, "AvgD": 3.3, "AvgA": 3.6}],
    )

    df = load_division(tmp_path, "E2")

    assert len(df) == 2
    assert pd.isna(df.loc[df["SeasonCode"] == "1516", "AvgH"]).all()


def test_load_division_raises_when_no_files(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_division(tmp_path, "EC")
