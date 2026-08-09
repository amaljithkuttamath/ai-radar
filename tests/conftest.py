"""Shared fixtures. Every test that touches persistent state redirects the module-level path
constants at a tmp_path first — the pipeline modules resolve their paths from the repo root at
import time, and a test that forgets to redirect would quietly rewrite the real ledger."""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_persistent_state(tmp_path, monkeypatch):
    """Redirect every persistent path at a tmp dir, for every test, without being asked.

    The docstring above has warned about this since the suite was written, and eleven tests
    still forgot — `test_track.py` and `test_delta.py` called `promote`/`_run` without
    taking `ledger_path`, so `track.LEDGER` stayed pointed at the committed
    `data/tracked.json`. They passed while that file was small and drifted into failure as
    daily runs grew it to 50 items: `assert stats["observed"] == 1` was reading 13 real
    carryovers alongside the one the test created. Nothing was wrong with the code under
    test, so the failures looked like flakes and the whole suite stayed red on every PR
    (`guard.yml` runs it), which trains you to ignore a red check.

    A convention that has to be remembered is not isolation. Autouse makes forgetting
    impossible: the opt-in fixtures below still work and simply override this with their
    own tmp path, and a test that wants the real files must now say so explicitly.
    """
    from distill import delta, track

    scored = tmp_path / "_auto_scored"
    scored.mkdir(exist_ok=True)
    monkeypatch.setattr(track, "LEDGER", tmp_path / "_auto_tracked.json")
    monkeypatch.setattr(track, "SCORED", scored)
    monkeypatch.setattr(delta, "STATE_PATH", tmp_path / "_auto_state.json")


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


@pytest.fixture
def ledger_path(tmp_path, monkeypatch):
    """Point the tracked-item ledger at a tmp file for the duration of a test."""
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
