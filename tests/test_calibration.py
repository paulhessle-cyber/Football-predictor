import numpy as np
import pandas as pd
import pytest

from football_predictor.calibration import (
    build_long_frame,
    calibration_report,
    expected_calibration_error,
    implied_probabilities,
    pick_odds_columns,
)


def test_pick_odds_columns_prefers_closing():
    columns = pd.Index(["AvgH", "AvgD", "AvgA", "AvgCH", "AvgCD", "AvgCA"])
    candidates = [("AvgCH", "AvgCD", "AvgCA"), ("AvgH", "AvgD", "AvgA")]
    assert pick_odds_columns(columns, candidates) == ("AvgCH", "AvgCD", "AvgCA")


def test_pick_odds_columns_falls_back_to_opening():
    columns = pd.Index(["AvgH", "AvgD", "AvgA"])
    candidates = [("AvgCH", "AvgCD", "AvgCA"), ("AvgH", "AvgD", "AvgA")]
    assert pick_odds_columns(columns, candidates) == ("AvgH", "AvgD", "AvgA")


def test_pick_odds_columns_none_when_missing():
    columns = pd.Index(["FTR"])
    candidates = [("AvgCH", "AvgCD", "AvgCA"), ("AvgH", "AvgD", "AvgA")]
    assert pick_odds_columns(columns, candidates) is None


def test_implied_probabilities_strips_overround():
    # 2.00 / 3.50 / 4.00 -> raw implied = 0.5 + 0.2857 + 0.25 = 1.0357 (3.57% overround)
    odds = pd.DataFrame({"H": [2.00], "D": [3.50], "A": [4.00]})
    fair = implied_probabilities(odds)
    assert fair.sum(axis=1).iloc[0] == pytest.approx(1.0)
    assert fair["H"].iloc[0] == pytest.approx(0.5 / 1.035714, rel=1e-4)


def _perfectly_calibrated_1x2_frame(n_per_outcome: int = 100) -> pd.DataFrame:
    # Fair 2.00 odds on H, long-shot 10.00 on D, and matching actual results:
    # H wins exactly half the time, D wins exactly a tenth of the time.
    rows = []
    for i in range(n_per_outcome):
        rows.append({"AvgH": 2.0, "AvgD": 10.0, "AvgA": 2.5, "FTR": "H" if i % 2 == 0 else "A"})
    return pd.DataFrame(rows)


def test_build_long_frame_1x2_shape():
    df = _perfectly_calibrated_1x2_frame(10)
    built = build_long_frame(df, "1x2")
    assert built is not None
    long_df, odds_cols = built
    assert odds_cols == ("AvgH", "AvgD", "AvgA")
    # 3 outcomes per match
    assert len(long_df) == len(df) * 3


def test_build_long_frame_returns_none_without_odds_columns():
    df = pd.DataFrame({"FTR": ["H", "A", "D"]})
    assert build_long_frame(df, "1x2") is None


def test_expected_calibration_error_zero_when_perfect():
    # Predicted prob always exactly matches whether it happened.
    long_df = pd.DataFrame(
        {
            "predicted_prob": [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
            "actual": [1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        }
    )
    bins, ece = expected_calibration_error(long_df, n_bins=10)
    assert ece == pytest.approx(0.0, abs=1e-9)


def test_expected_calibration_error_detects_gap():
    # Market says 90% every time, but it only happens half the time.
    long_df = pd.DataFrame(
        {
            "predicted_prob": [0.9] * 10,
            "actual": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        }
    )
    bins, ece = expected_calibration_error(long_df, n_bins=10)
    assert ece == pytest.approx(0.4, abs=1e-9)


def test_calibration_report_ou25_uses_goal_totals():
    df = pd.DataFrame(
        {
            "Avg>2.5": [1.8] * 4,
            "Avg<2.5": [2.1] * 4,
            "FTHG": [2, 1, 0, 3],
            "FTAG": [1, 1, 0, 0],  # totals: 3 (over), 2 (under), 0 (under), 3 (over)
        }
    )
    report = calibration_report(df, "ou25", n_bins=5)
    assert report is not None
    assert report.n_matches == 4
    assert report.n_outcome_rows == 8  # 2 outcomes x 4 matches
    assert 0.0 <= report.brier_score <= 1.0


def test_calibration_report_none_without_usable_columns():
    df = pd.DataFrame({"FTHG": [1], "FTAG": [1]})
    assert calibration_report(df, "ou25") is None
