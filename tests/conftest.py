"""Shared fixtures. Every test that touches persistent state redirects the module-level path
constants at a tmp_path first — the pipeline modules resolve their paths from the repo root at
import time, and a test that forgets to redirect would quietly rewrite the real ledger."""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def make_item(**over) -> dict:
    """A scored-item dict with sane defaults. Pass overrides for the field under test."""
    item = {
        "id": "ghrepo:acme/widget",
        "category": "releases",
        "title": "acme/widget — a widget",
        "url": "https://github.com/acme/widget",
        "source": "GitHub Trending",
        "authors": [],
        "published": "2026-07-01T00:00:00+00:00",
        "fetched": "2026-07-27T00:00:00+00:00",
        "raw_summary": "A widget.",
        "links": {},
        "keywords": [],
        "signals": {},
        "score": 3,
        "score_reasons": [],
        "focus_match": False,
    }
    item.update(over)
    return item


@pytest.fixture(autouse=True)
def _empty_ledger(tmp_path, monkeypatch):
    """Every test starts from an empty tracked-item ledger.

    `track.promote()` and `track.story_arcs()` read `load_ledger()` when the caller doesn't
    hand them one, which resolves to the repo's committed `data/tracked.json` — a file the
    daily radar run rewrites. Without this the suite's result depends on what the radar
    happened to be watching that morning: a single tracked item leaks into every ledger a
    test builds, and eight assertions about ledger contents fail on any day but an empty one.
    Autouse because the leak is in the module default, so opting in per test is exactly the
    thing that gets forgotten.
    """
    from distill import track
    monkeypatch.setattr(track, "LEDGER", tmp_path / "tracked-isolated.json")


@pytest.fixture
def ledger_path(tmp_path, monkeypatch):
    """Point the tracked-item ledger at a tmp file the test can read back."""
    from distill import track
    p = tmp_path / "tracked.json"
    monkeypatch.setattr(track, "LEDGER", p)
    return p


@pytest.fixture
def scored_dir(tmp_path, monkeypatch):
    """Point data/scored/ at a tmp dir."""
    from distill import track
    d = tmp_path / "scored"
    d.mkdir()
    monkeypatch.setattr(track, "SCORED", d)
    return d


@pytest.fixture
def no_profile(monkeypatch):
    """Neutralize config/profile.yaml + the FOCUS env var so focus_match is deterministic."""
    from distill import focus
    focus._profile_terms.cache_clear()
    monkeypatch.setenv("FOCUS", "")
    monkeypatch.setattr(focus, "PROFILE", Path("/nonexistent/profile.yaml"))
    yield
    focus._profile_terms.cache_clear()
