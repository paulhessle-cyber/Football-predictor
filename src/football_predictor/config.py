"""Shared constants: division codes and season-code generation.

football-data.co.uk seasons are coded as e.g. "2526" for 2025/26. Coverage
notes (from the project brief): League One and League Two go back to the
1990s; National League ("EC") coverage only starts 2005/06, and Avg/Max
consensus-odds columns are a more recent addition still, so defaults here
are deliberately conservative (last ~10 seasons) rather than the full
history.
"""

from __future__ import annotations

DIVISIONS: dict[str, str] = {
    "E0": "Premier League",
    "E1": "Championship",
    "E2": "League One",
    "E3": "League Two",
    "EC": "National League",
}

DEFAULT_DIVISIONS: tuple[str, ...] = ("E2", "E3", "EC")

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{division}.csv"


def season_code(start_year: int) -> str:
    """"2025" -> "2526" (the season starting in `start_year`)."""
    end_year = start_year + 1
    return f"{start_year % 100:02d}{end_year % 100:02d}"


def season_codes(start_year: int, end_year: int) -> list[str]:
    """Season codes for every season starting in [start_year, end_year]."""
    return [season_code(y) for y in range(start_year, end_year + 1)]
