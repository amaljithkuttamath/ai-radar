"""Shared fixtures. Every test that touches persistent state redirects the module-level path
constants at a tmp_path first — the pipeline modules resolve their paths from the repo root at
import time, and a test that forgets to redirect would quietly rewrite the real ledger."""

from __future__ import annotations
import sys
import socket
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_persistent_state(tmp_path, monkeypatch):
    # Settings deliberately exports resolved values for legacy stage modules.
    # Restore the environment after every test so those values cannot leak.
    monkeypatch.setattr(os, "environ", os.environ.copy())
    from collectors import common
    from distill import delta, score, synthesize, reindex
    from radar import pipeline

    for module in (common, delta, score, synthesize, reindex, pipeline):
        monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(common, "RAW", tmp_path / "data/raw")
    monkeypatch.setattr(common, "SEEN_PATH", tmp_path / "data/seen.json")
    monkeypatch.setattr(delta, "STATE_PATH", tmp_path / "data/state.json")
    monkeypatch.setattr(score, "SCORED", tmp_path / "data/scored")
    monkeypatch.setattr(synthesize, "SCORED", tmp_path / "data/scored")
    monkeypatch.setattr(synthesize, "ENRICHED", tmp_path / "data/enriched")
    monkeypatch.setattr(reindex, "REPORTS", tmp_path / "reports")

    from distill import track
    import llm

    monkeypatch.setattr(track, "LEDGER", tmp_path / "data/tracked.json")
    monkeypatch.setattr(track, "SCORED", tmp_path / "data/scored")
    llm._AUTO_CACHE.clear()
    monkeypatch.setattr(llm, "auto_model", lambda *a, **kw: "")

    connect = socket.create_connection

    def offline(address, *args, **kwargs):
        if address[0] in {"127.0.0.1", "::1", "localhost"}:
            return connect(address, *args, **kwargs)
        raise AssertionError("Tests must replace network access at the transport boundary")

    monkeypatch.setattr(socket, "create_connection", offline)


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
