"""Movers: what the 'What changed' section is built from.

`compute_delta` is only meaningful when today's set and the previous snapshot overlap. For
most of this repo's life they never did — see tests/test_track.py — so these tests exercise
the classification logic directly, and test_carryovers_make_movers_reachable pins the
end-to-end property that fix depends on.
"""
from __future__ import annotations
import json

import pytest

from distill import delta
from tests.conftest import make_item


@pytest.fixture
def state_path(tmp_path, monkeypatch):
    p = tmp_path / "state.json"
    monkeypatch.setattr(delta, "STATE_PATH", p)
    return p


def test_first_run_marks_everything_new(state_path):
    d = delta.compute_delta([make_item(id="a"), make_item(id="b")])
    assert d["first_run"] is True
    assert len(d["new"]) == 2
    assert d["climbing"] == [] and d["cooled"] == []


def test_an_unseen_item_is_new(state_path):
    delta.save_state([make_item(id="a", signals={"gh_stars": 10})])
    d = delta.compute_delta([make_item(id="a", signals={"gh_stars": 10}),
                             make_item(id="b", signals={"gh_stars": 10})])
    assert d["first_run"] is False
    assert [x["title"] for x in d["new"]] == ["acme/widget — a widget"]
    assert len(d["new"]) == 1


def test_growing_traction_registers_as_climbing(state_path):
    delta.save_state([make_item(id="a", score=3, signals={"gh_stars": 100})])
    d = delta.compute_delta([make_item(id="a", score=3, signals={"gh_stars": 5000})])
    assert len(d["climbing"]) == 1 and d["cooled"] == []
    assert d["climbing"][0]["mag_delta"] > 0


def test_a_score_drop_registers_as_cooled(state_path):
    delta.save_state([make_item(id="a", score=4, signals={"gh_stars": 100})])
    d = delta.compute_delta([make_item(id="a", score=2, signals={"gh_stars": 100})])
    assert len(d["cooled"]) == 1
    assert d["cooled"][0]["score_delta"] == -2


def test_noise_is_not_a_move(state_path):
    """A handful of extra stars on an already-popular repo is not news."""
    delta.save_state([make_item(id="a", score=3, signals={"gh_stars": 5000})])
    d = delta.compute_delta([make_item(id="a", score=3, signals={"gh_stars": 5010})])
    assert d["climbing"] == [] and d["cooled"] == []


def test_save_state_preserves_first_seen(state_path):
    delta.save_state([make_item(id="a", signals={"gh_stars": 1})])
    first = json.loads(state_path.read_text())["a"]["first_seen"]
    delta.save_state([make_item(id="a", signals={"gh_stars": 2})])
    assert json.loads(state_path.read_text())["a"]["first_seen"] == first


def test_carryovers_make_movers_reachable(state_path, monkeypatch):
    """The end-to-end property the carryover ledger exists to restore: an item that stays on
    the radar appears in two consecutive runs, so its traction change is detectable.

    Without carryovers, run two's scored set shares no ids with run one's snapshot and every
    bucket except 'new' is empty by construction."""
    from distill import track

    fetchers = {"github": lambda o, r: {"stars": 9000, "forks": 10}}

    day1 = [make_item(id="ghrepo:acme/widget", score=3, signals={"gh_stars": 100})]
    delta.save_state(day1)
    ledger = track.promote(day1)

    # Day two collects nothing new; the radar re-observes what it is tracking.
    real_today = track._today
    track._today = lambda: "2026-07-02"
    try:
        ledger, _ = track.refresh(ledger, fetchers=fetchers)
    finally:
        track._today = real_today
    day2 = track.carryover_items(ledger)

    assert day2, "a quiet day still has candidates"
    d = delta.compute_delta(day2)
    assert len(d["climbing"]) == 1, "traction growth on a tracked item is visible"
    assert d["new"] == []
