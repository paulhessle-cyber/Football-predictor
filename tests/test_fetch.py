from pathlib import Path

from football_predictor.fetch import fetch_one, raw_csv_path


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content
        self.ok = status_code < 400

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int):
        self.requested_urls.append(url)
        return self._response


def test_fetch_one_downloads_and_writes_file(tmp_path: Path):
    session = _FakeSession(_FakeResponse(200, b"Date,FTR\n12/08/2023,H\n"))

    result = fetch_one("E3", "2324", tmp_path, session=session)

    assert result.status == "downloaded"
    assert result.path == raw_csv_path(tmp_path, "E3", "2324")
    assert result.path.read_bytes() == b"Date,FTR\n12/08/2023,H\n"
    assert session.requested_urls == [
        "https://www.football-data.co.uk/mmz4281/2324/E3.csv"
    ]


def test_fetch_one_skips_existing_file_without_force(tmp_path: Path):
    dest = raw_csv_path(tmp_path, "E3", "2324")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"already here")
    session = _FakeSession(_FakeResponse(200, b"new content"))

    result = fetch_one("E3", "2324", tmp_path, session=session)

    assert result.status == "cached"
    assert dest.read_bytes() == b"already here"
    assert session.requested_urls == []


def test_fetch_one_force_redownloads(tmp_path: Path):
    dest = raw_csv_path(tmp_path, "E3", "2324")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"stale")
    session = _FakeSession(_FakeResponse(200, b"fresh"))

    result = fetch_one("E3", "2324", tmp_path, force=True, session=session)

    assert result.status == "downloaded"
    assert dest.read_bytes() == b"fresh"


def test_fetch_one_handles_404_as_not_found(tmp_path: Path):
    session = _FakeSession(_FakeResponse(404, b""))

    result = fetch_one("EC", "0304", tmp_path, session=session)

    assert result.status == "not_found"
    assert not raw_csv_path(tmp_path, "EC", "0304").exists()
