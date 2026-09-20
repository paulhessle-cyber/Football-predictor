"""Download football-data.co.uk season CSVs into a local directory.

Some (division, season) combinations don't exist — e.g. the National League
("EC") has no data before 2005/06 — so a missing file is logged and skipped
rather than treated as fatal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import BASE_URL

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


@dataclass
class FetchResult:
    division: str
    season: str
    path: Path | None
    status: str  # "downloaded", "cached", "not_found", "error"
    detail: str = ""


def raw_csv_path(data_dir: Path, division: str, season: str) -> Path:
    return Path(data_dir) / f"{division}_{season}.csv"


def fetch_one(
    division: str,
    season: str,
    data_dir: Path,
    force: bool = False,
    session: requests.Session | None = None,
) -> FetchResult:
    dest = raw_csv_path(data_dir, division, season)
    if dest.exists() and not force:
        return FetchResult(division, season, dest, "cached")

    url = BASE_URL.format(season=season, division=division)
    http = session or requests
    try:
        resp = http.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return FetchResult(division, season, None, "error", str(exc))

    if resp.status_code == 404:
        return FetchResult(division, season, None, "not_found", url)
    if not resp.ok:
        return FetchResult(
            division, season, None, "error", f"HTTP {resp.status_code} for {url}"
        )
    if not resp.content.strip():
        return FetchResult(division, season, None, "not_found", f"empty body from {url}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return FetchResult(division, season, dest, "downloaded")


def fetch_many(
    divisions: list[str],
    seasons: list[str],
    data_dir: Path,
    force: bool = False,
) -> list[FetchResult]:
    data_dir = Path(data_dir)
    results = []
    with requests.Session() as session:
        for division in divisions:
            for season in seasons:
                result = fetch_one(division, season, data_dir, force=force, session=session)
                results.append(result)
                logger.info("%s %s: %s", division, season, result.status)
    return results
