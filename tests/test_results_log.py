from pathlib import Path

import pandas as pd
import pytest

from football_predictor.flags import add_flag
from football_predictor.results_log import (
    evaluate_flag_impact,
    load_results_log,
    log_prediction,
    settle_result,
)


def test_log_prediction_with_no_matching_flags(tmp_path: Path):
    results_path = tmp_path / "results_log.csv"
    flags_path = tmp_path / "flags.csv"

    row = log_prediction(
        results_path,
        flags_path,
        match_date="2026-09-27",
        division="E3",
        home_team="Salford City",
        away_team="Grimsby Town",
        market="1x2",
        outcome="H",
        market_prob=0.45,
    )

    assert row["flag_adjustment"] == 0.0
    assert row["predicted_prob"] == pytest.approx(0.45)
    assert row["match_id"] == 1


def test_log_prediction_applies_matching_flag_adjustment(tmp_path: Path):
    results_path = tmp_path / "results_log.csv"
    flags_path = tmp_path / "flags.csv"
    add_flag(
        flags_path, "2026-09-27", "E3", "Salford City", "Grimsby Town", "1x2", "H", -0.15, "striker out"
    )

    row = log_prediction(
        results_path,
        flags_path,
        "2026-09-27",
        "E3",
        "Salford City",
        "Grimsby Town",
        "1x2",
        "H",
        market_prob=0.45,
    )

    assert row["flag_adjustment"] == pytest.approx(-0.15)
    assert row["predicted_prob"] == pytest.approx(0.30)


def test_log_prediction_sums_multiple_matching_flags(tmp_path: Path):
    results_path = tmp_path / "results_log.csv"
    flags_path = tmp_path / "flags.csv"
    add_flag(flags_path, "2026-09-27", "E3", "Salford City", "Grimsby Town", "1x2", "H", -0.15, "striker out")
    add_flag(flags_path, "2026-09-27", "E3", "Salford City", "Grimsby Town", "1x2", "H", 0.05, "home fortress")

    row = log_prediction(
        results_path, flags_path, "2026-09-27", "E3", "Salford City", "Grimsby Town", "1x2", "H", 0.45
    )

    assert row["flag_adjustment"] == pytest.approx(-0.10)
    assert row["predicted_prob"] == pytest.approx(0.35)


def test_log_prediction_clips_predicted_prob_to_valid_range(tmp_path: Path):
    results_path = tmp_path / "results_log.csv"
    flags_path = tmp_path / "flags.csv"
    add_flag(flags_path, "2026-09-27", "E3", "A", "B", "1x2", "H", 0.9, "huge boost")

    row = log_prediction(results_path, flags_path, "2026-09-27", "E3", "A", "B", "1x2", "H", 0.5)

    assert row["predicted_prob"] == 1.0


def test_settle_result_fills_actual_and_settled_at(tmp_path: Path):
    results_path = tmp_path / "results_log.csv"
    flags_path = tmp_path / "flags.csv"
    log_prediction(results_path, flags_path, "2026-09-27", "E3", "A", "B", "1x2", "H", 0.45)

    row = settle_result(results_path, match_id=1, actual=1.0)

    assert row["actual"] == 1.0
    assert pd.notna(row["settled_at"])

    df = load_results_log(results_path)
    assert df.iloc[0]["actual"] == 1.0


def test_settle_result_raises_for_unknown_match_id(tmp_path: Path):
    results_path = tmp_path / "results_log.csv"
    with pytest.raises(KeyError):
        settle_result(results_path, match_id=99, actual=1.0)


def test_evaluate_flag_impact_insufficient_data(tmp_path: Path):
    results_path = tmp_path / "results_log.csv"
    flags_path = tmp_path / "flags.csv"
    add_flag(flags_path, "2026-09-27", "E3", "A", "B", "1x2", "H", -0.15, "striker out")
    log_prediction(results_path, flags_path, "2026-09-27", "E3", "A", "B", "1x2", "H", 0.45)
    settle_result(results_path, match_id=1, actual=0.0)

    result = evaluate_flag_impact(results_path, min_n=30)

    assert result["status"] == "insufficient_data"
    assert result["n_flagged_settled"] == 1


def test_evaluate_flag_impact_reports_brier_improvement(tmp_path: Path):
    results_path = tmp_path / "results_log.csv"
    flags_path = tmp_path / "flags.csv"

    # Two flagged matches: market said 0.5, flag correctly pulled it down to
    # 0.2, and the outcome didn't happen (actual=0) -- flag should look better.
    add_flag(flags_path, "2026-09-27", "E3", "A", "B", "1x2", "H", -0.3, "striker out")
    add_flag(flags_path, "2026-09-28", "E3", "C", "D", "1x2", "H", -0.3, "striker out")
    log_prediction(results_path, flags_path, "2026-09-27", "E3", "A", "B", "1x2", "H", 0.5)
    log_prediction(results_path, flags_path, "2026-09-28", "E3", "C", "D", "1x2", "H", 0.5)
    settle_result(results_path, match_id=1, actual=0.0)
    settle_result(results_path, match_id=2, actual=0.0)

    result = evaluate_flag_impact(results_path, min_n=2)

    assert result["status"] == "ok"
    assert result["n_flagged_settled"] == 2
    assert result["baseline_brier"] == pytest.approx(0.25)  # (0.5-0)^2
    assert result["flagged_brier"] == pytest.approx(0.04)  # (0.2-0)^2
    assert result["improvement"] > 0
