from pathlib import Path

from football_predictor.flags import add_flag, flags_for_match, load_flags


def test_load_flags_returns_empty_frame_when_file_missing(tmp_path: Path):
    df = load_flags(tmp_path / "flags.csv")
    assert df.empty
    assert list(df.columns) == [
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


def test_add_flag_creates_file_and_returns_row(tmp_path: Path):
    path = tmp_path / "flags.csv"
    row = add_flag(
        path,
        match_date="2026-09-27",
        division="E3",
        home_team="Salford City",
        away_team="Grimsby Town",
        market="1x2",
        outcome="H",
        adjustment=-0.15,
        reason="Key striker out injured",
    )
    assert row["flag_id"] == 1
    assert path.exists()

    df = load_flags(path)
    assert len(df) == 1
    assert df.iloc[0]["adjustment"] == -0.15


def test_add_flag_increments_flag_id(tmp_path: Path):
    path = tmp_path / "flags.csv"
    add_flag(path, "2026-09-27", "E3", "A", "B", "1x2", "H", -0.1, "first")
    row2 = add_flag(path, "2026-09-28", "E3", "C", "D", "1x2", "A", 0.1, "second")
    assert row2["flag_id"] == 2


def test_flags_for_match_filters_to_exact_match_and_outcome(tmp_path: Path):
    path = tmp_path / "flags.csv"
    add_flag(path, "2026-09-27", "E3", "Salford City", "Grimsby Town", "1x2", "H", -0.15, "striker out")
    add_flag(path, "2026-09-27", "E3", "Salford City", "Grimsby Town", "1x2", "A", 0.05, "new manager bounce")
    add_flag(path, "2026-09-27", "E2", "Salford City", "Grimsby Town", "1x2", "H", -0.2, "different division")

    flags_df = load_flags(path)
    matching = flags_for_match(flags_df, "2026-09-27", "E3", "Salford City", "Grimsby Town", "1x2", "H")

    assert len(matching) == 1
    assert matching.iloc[0]["reason"] == "striker out"


def test_flags_for_match_empty_when_none_match(tmp_path: Path):
    path = tmp_path / "flags.csv"
    add_flag(path, "2026-09-27", "E3", "Salford City", "Grimsby Town", "1x2", "H", -0.15, "striker out")
    flags_df = load_flags(path)
    matching = flags_for_match(flags_df, "2026-10-04", "E3", "Salford City", "Grimsby Town", "1x2", "H")
    assert matching.empty
