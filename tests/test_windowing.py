"""Window filtering: which stored items count as "recent", and what a malformed one costs.

Every stage that reads a directory of JSON items filters it by the `fetched` stamp. The
files are written by the pipeline itself, so the happy path is boring — but they are also
plain JSON on disk that a partial write, a hand edit, or an older schema can leave in a
shape `datetime.fromisoformat` refuses. One such file used to abort the entire stage.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone

import pytest

from collectors import common
from collectors.common import parse_ts
from distill import synthesize
from tests.conftest import make_item


NOW = datetime.now(timezone.utc)


@pytest.mark.parametrize("value,expected_utc", [
    ("2026-07-27T10:00:00+00:00", True),
    ("2026-07-27T10:00:00Z", True),          # trailing Z, which fromisoformat rejects <3.11
    ("2026-07-27T10:00:00", True),           # naive -> assumed UTC, never left comparable-unsafe
])
def test_parse_ts_returns_an_aware_datetime(value, expected_utc):
    dt = parse_ts(value)
    assert dt is not None and dt.tzinfo is not None
    assert (dt.utcoffset() == timedelta(0)) is expected_utc


@pytest.mark.parametrize("value", [None, "", "not a date", 1753600000, {"t": 1}, []])
def test_parse_ts_refuses_junk_without_raising(value):
    """`fromisoformat(None)` raises TypeError, which `except ValueError` does not catch."""
    assert parse_ts(value) is None


def _write(dirpath, item):
    dirpath.mkdir(parents=True, exist_ok=True)
    name = str(item.get("id") or "x").replace(":", "_").replace("/", "_")
    (dirpath / f"{name}.json").write_text(json.dumps(item))


def test_iter_raw_skips_a_bad_stamp_instead_of_dying(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "RAW", tmp_path / "raw")
    good = make_item(id="ghrepo:acme/good", fetched=NOW.isoformat())
    naive = make_item(id="ghrepo:acme/naive", fetched=NOW.replace(tzinfo=None).isoformat())
    for it in (good, naive,
               make_item(id="ghrepo:acme/null", fetched=None),
               make_item(id="ghrepo:acme/junk", fetched="yesterday-ish")):
        _write(tmp_path / "raw" / "releases", it)

    got = {it["id"] for it in common.iter_raw("48h")}
    assert got == {"ghrepo:acme/good", "ghrepo:acme/naive"}, \
        "a null or unparseable stamp costs that item, not the run"


def test_load_scored_skips_a_bad_stamp_instead_of_dying(tmp_path, monkeypatch):
    monkeypatch.setattr(synthesize, "SCORED", tmp_path / "scored")
    for it in (make_item(id="ghrepo:acme/good", fetched=NOW.isoformat()),
               make_item(id="ghrepo:acme/null", fetched=None),
               make_item(id="ghrepo:acme/stale",
                         fetched=(NOW - timedelta(days=30)).isoformat())):
        _write(tmp_path / "scored", it)

    assert [it["id"] for it in synthesize.load_scored()] == ["ghrepo:acme/good"]
