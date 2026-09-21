import numpy as np
import pandas as pd
import pytest

from football_predictor.calibration import (
    _settle_handicap_line,
    _split_handicap_lines,
    build_long_frame,
    calibration_report,
    expected_calibration_error,
    implied_probabilities,
    odds_to_fair_probabilities,
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


def test_odds_to_fair_probabilities_matches_dataframe_version():
    single = odds_to_fair_probabilities(2.00, 3.50, 4.00)
    frame = implied_probabilities(pd.DataFrame({"H": [2.00], "D": [3.50], "A": [4.00]}))
    assert single == pytest.approx(tuple(frame.iloc[0]))
    assert sum(single) == pytest.approx(1.0)


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
    long_df, odds_cols, line_col = built
    assert odds_cols == ("AvgH", "AvgD", "AvgA")
    assert line_col is None
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


def test_split_handicap_lines_whole_and_half_are_unsplit():
    line = pd.Series([-0.5, -1.0, 0.0])
    lo, hi = _split_handicap_lines(line)
    assert list(lo) == [-0.5, -1.0, 0.0]
    assert list(hi) == [-0.5, -1.0, 0.0]


def test_split_handicap_lines_quarter_splits_into_neighbours():
    line = pd.Series([-0.25, 0.25, 0.75])
    lo, hi = _split_handicap_lines(line)
    assert list(lo) == pytest.approx([-0.5, 0.0, 0.5])
    assert list(hi) == pytest.approx([0.0, 0.5, 1.0])


def test_settle_handicap_line_win_loss_push():
    fthg = np.array([2, 0, 1])
    ftag = np.array([0, 2, 1])
    line = np.array([-1.0, -1.0, 0.0])
    # margins: 2-1-0=1 (win), 0-1-2=-3 (loss), 1+0-1=0 (push)
    result = _settle_handicap_line(fthg, ftag, line)
    assert list(result) == [1.0, 0.0, 0.5]


def test_build_long_frame_ah_quarter_line_half_win():
    # Home favourite at -0.75 wins by exactly 1 goal: splits into -0.5 (win)
    # and -1.0 (push) -> settles as a "half win" (0.75).
    df = pd.DataFrame(
        {
            "AvgAHH": [1.9],
            "AvgAHA": [1.95],
            "AHh": [-0.75],
            "FTHG": [2],
            "FTAG": [1],
        }
    )
    built = build_long_frame(df, "ah")
    assert built is not None
    long_df, odds_cols, line_col = built
    assert line_col == "AHh"
    home_row = long_df.iloc[0]
    away_row = long_df.iloc[1]
    assert home_row["actual"] == pytest.approx(0.75)
    assert away_row["actual"] == pytest.approx(0.25)


def test_build_long_frame_ah_none_without_line_column():
    df = pd.DataFrame(
        {"AvgAHH": [1.9], "AvgAHA": [1.95], "FTHG": [1], "FTAG": [0]}
    )
    assert build_long_frame(df, "ah") is None


def test_build_long_frame_drops_rows_with_non_numeric_odds():
    # Real football-data.co.uk exports occasionally have a stray non-numeric
    # character in an odds cell (observed in practice: a bare "`") — it
    # must be dropped as unusable, not crash the whole run.
    df = pd.DataFrame(
        {
            "AvgH": [2.0, "`", 1.8],
            "AvgD": [3.3, 3.4, 3.2],
            "AvgA": [3.6, 3.5, 4.0],
            "FTR": ["H", "A", "H"],
        }
    )
    built = build_long_frame(df, "1x2")
    assert built is not None
    long_df, odds_cols, line_col = built
    assert len(long_df) == 2 * 3  # only the 2 clean rows survive


def test_calibration_report_ah_uses_market_average_line():
    df = pd.DataFrame(
        {
            "AvgAHH": [1.9, 2.0, 1.85, 2.05],
            "AvgAHA": [1.95, 1.85, 2.0, 1.8],
            "AHh": [-0.5, -1.0, 0.0, 0.25],
            "FTHG": [2, 1, 0, 3],
            "FTAG": [0, 1, 0, 1],
        }
    )
    report = calibration_report(df, "ah", n_bins=5)
    assert report is not None
    assert report.line_column_used == "AHh"
    assert report.n_matches == 4
    assert report.n_outcome_rows == 8  # Home + Away per match
