"""Tests for the carryover ledger — the radar's memory.

The headline test here is `test_streak_accumulates_across_runs`. Before distill/track.py
existed, an item was collected once, scored once, and never seen again, so `streak` was 1 on
every item in every committed snapshot and `story_arcs()` could not fire even in principle.
These tests pin the behaviour that fixes it.
"""
from __future__ import annotations
import json

import pytest

from distill import track
from tests.conftest import make_item


# A fetcher table that reports fixed numbers, so a test never depends on the network.
def fake_fetchers(*, stars=None, hf=None, paper=None):
    return {
        "github": (lambda o, r: None if stars is None else {"stars": stars, "forks": 1}),
        "hf_repo": (lambda kind, key: hf),
        "hf_paper": (lambda key: paper),
    }


# ---------------------------------------------------------------------------
# What can be re-observed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("iid,expected", [
    ("ghrepo:getzep/graphiti", ("github", "getzep/graphiti")),
    ("hfmodel:owensong/Inflect-Micro-v2", ("hf_model", "owensong/Inflect-Micro-v2")),
    ("hfdataset:acme/corpus", ("hf_dataset", "acme/corpus")),
    ("arxiv:2501.01234", ("arxiv", "2501.01234")),
    ("blog:deadbeef", None),
])
def test_signal_source_covers_every_id_scheme(iid, expected):
    assert track.signal_source({"id": iid}) == expected


def test_blog_item_with_a_linked_repo_is_trackable():
    """A vendor blog post has no counter of its own, but if the collector captured a repo
    link there is something to watch."""
    entry = {"id": "blog:abc", "links": {"github": "https://github.com/acme/widget"}}
    assert track.signal_source(entry) == ("github", "acme/widget")
    assert track.is_trackable(entry)
    assert not track.is_trackable({"id": "blog:abc", "links": {}})


def test_observe_reads_the_source_of_record():
    entry = {"id": "ghrepo:acme/widget"}
    assert track.observe(entry, fake_fetchers(stars=402)) == {"gh_stars": 402, "gh_forks": 1}

    paper = {"id": "arxiv:2501.01234", "links": {}}
    assert track.observe(paper, fake_fetchers(paper={"hf_upvotes": 62, "hf_comments": 4})) == \
        {"hf_upvotes": 62, "hf_comments": 4}


def test_observe_folds_a_papers_repo_stars_into_its_upvotes():
    """A paper's long-run traction lives in its repo as much as in HF upvotes; when the
    collector captured both, an observation carries both."""
    entry = {"id": "arxiv:2501.01234", "links": {"github": "https://github.com/acme/widget"}}
    got = track.observe(entry, fake_fetchers(stars=90, paper={"hf_upvotes": 62}))
    assert got == {"hf_upvotes": 62, "gh_stars": 90}


def test_observe_returns_none_when_the_source_is_gone():
    assert track.observe({"id": "ghrepo:acme/deleted"}, fake_fetchers(stars=None)) is None


# ---------------------------------------------------------------------------
# The regression: streaks and history must accumulate
# ---------------------------------------------------------------------------

_REAL_TODAY = track._today


def _run(ledger, day, **kw):
    """Simulate one daily run at a given date. `refresh` stamps `last_seen` from the clock,
    and the whole point of these tests is what happens across days."""
    track._today = lambda: day
    try:
        return track.refresh(ledger, **kw)
    finally:
        track._today = _REAL_TODAY


def test_streak_accumulates_across_runs():
    """Three consecutive runs on a growing repo => streak 4, four magnitude observations.

    This is the assertion the old design could never satisfy: `data/seen.json` dedups an item
    forever, so it appeared in exactly one run's scored set and its streak was pinned at 1.
    """
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4,
                                      signals={"gh_stars": 100})])
    assert ledger["ghrepo:acme/widget"]["streak"] == 1

    for day, stars in [("2026-07-02", 150), ("2026-07-03", 260), ("2026-07-04", 420)]:
        ledger, stats = _run(ledger, day, fetchers=fake_fetchers(stars=stars))
        assert stats["observed"] == 1

    entry = ledger["ghrepo:acme/widget"]
    assert entry["streak"] == 4
    assert len(entry["mag_history"]) == 4
    assert entry["mag_history"] == sorted(entry["mag_history"]), "traction only grew"
    assert entry["signals"]["gh_stars"] == 420, "signals are the latest observation"
    assert entry["last_seen"] == "2026-07-04"
    assert entry["first_seen"] != "2026-07-04", "first_seen is preserved, not overwritten"


def test_story_arcs_fire_once_streaks_are_real():
    """The feature that had never once produced output in production."""
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4,
                                      signals={"gh_stars": 40})])
    assert track.story_arcs(ledger) == [], "one run is not an arc"

    for day, stars in [("2026-07-02", 120), ("2026-07-03", 380)]:
        ledger, _ = _run(ledger, day, fetchers=fake_fetchers(stars=stars))

    arcs = track.story_arcs(ledger)
    assert len(arcs) == 1
    arc = arcs[0]
    assert arc["streak"] == 3
    assert arc["mag_pct_change"] > 0
    assert arc["url"] == "https://github.com/acme/widget"


def test_a_falling_item_is_not_an_arc():
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4,
                                      signals={"gh_stars": 500})])
    for day, stars in [("2026-07-02", 480), ("2026-07-03", 470)]:
        ledger, _ = _run(ledger, day, fetchers=fake_fetchers(stars=stars))
    assert track.story_arcs(ledger) == []


def test_same_day_rerun_does_not_inflate_the_streak():
    """distill can be dispatched manually after a scheduled run. That must not look like an
    extra day of traction."""
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4,
                                      signals={"gh_stars": 100})])
    day = ledger["ghrepo:acme/widget"]["last_seen"]
    ledger, stats = _run(ledger, day, fetchers=fake_fetchers(stars=999))
    assert stats["skipped"] == 1 and stats["observed"] == 0
    assert ledger["ghrepo:acme/widget"]["streak"] == 1


# ---------------------------------------------------------------------------
# Pruning
# ---------------------------------------------------------------------------

def test_a_missed_observation_is_not_evidence_of_cooling():
    """A network blip must cost a data point, never a fabricated decline."""
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4,
                                      signals={"gh_stars": 100})])
    before = list(ledger["ghrepo:acme/widget"]["mag_history"])
    ledger, stats = _run(ledger, "2026-07-02", fetchers=fake_fetchers(stars=None))
    entry = ledger["ghrepo:acme/widget"]
    assert stats["missed"] == 1
    assert entry["mag_history"] == before, "history untouched"
    assert entry["streak"] == 1, "an unobserved run does not extend a streak"
    assert entry["misses"] == 1


def test_an_unreachable_item_is_dropped_after_max_misses():
    ledger = track.promote([make_item(id="ghrepo:acme/gone", score=4,
                                      signals={"gh_stars": 100})])
    for day in ["2026-07-02", "2026-07-03", "2026-07-04"]:
        ledger, _ = _run(ledger, day, fetchers=fake_fetchers(stars=None))
    assert ledger == {}, "a repo that 404s three runs running leaves the radar"


def test_flat_traction_ages_an_item_out():
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4,
                                      signals={"gh_stars": 100})])
    for day in ["2026-07-0%d" % d for d in range(2, 9)]:
        ledger, _ = _run(ledger, day, fetchers=fake_fetchers(stars=100))
    assert ledger == {}, "an item that stopped moving stops being a radar target"


def test_ttl_expires_an_item_however_well_it_is_doing():
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4,
                                      signals={"gh_stars": 100})])
    ledger["ghrepo:acme/widget"]["first_seen"] = "2026-01-01"
    ledger, _ = _run(ledger, "2026-07-02", fetchers=fake_fetchers(stars=100000))
    assert ledger == {}


def test_size_cap_keeps_the_biggest_peaks(monkeypatch):
    monkeypatch.setattr(track, "MAX_TRACKED", 2)
    items = [make_item(id=f"ghrepo:acme/w{n}", score=4, signals={"gh_stars": n * 100})
             for n in (1, 2, 3, 4)]
    ledger = track.promote(items)
    ledger, _ = _run(ledger, "2026-07-02", fetchers=fake_fetchers(stars=None))
    assert len(ledger) == 2
    assert set(ledger) == {"ghrepo:acme/w3", "ghrepo:acme/w4"}


def test_refresh_budget_leaves_low_peaks_unobserved_rather_than_missed():
    """Running out of budget means we didn't look — not that the item was unreachable."""
    items = [make_item(id=f"ghrepo:acme/w{n}", score=4, signals={"gh_stars": n * 100})
             for n in (1, 2, 3)]
    ledger = track.promote(items)
    ledger, stats = _run(ledger, "2026-07-02", fetchers=fake_fetchers(stars=500), budget=1)
    assert stats["observed"] == 1 and stats["skipped"] == 2
    assert all(e["misses"] == 0 for e in ledger.values())
    assert ledger["ghrepo:acme/w3"]["streak"] == 2, "highest peak is refreshed first"


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------

def test_promote_is_selective():
    items = [
        make_item(id="ghrepo:acme/big", score=4),          # tracked
        make_item(id="ghrepo:acme/small", score=1),        # below MIN_SCORE
        make_item(id="blog:xyz", score=5, links={}),       # nothing to re-observe
    ]
    ledger = track.promote(items)
    assert set(ledger) == {"ghrepo:acme/big"}


def test_promote_never_resets_an_items_history():
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4,
                                      signals={"gh_stars": 100})])
    ledger, _ = _run(ledger, "2026-07-02", fetchers=fake_fetchers(stars=300))
    assert ledger["ghrepo:acme/widget"]["streak"] == 2

    # The item is collected again (a second topic feed surfaces it) and re-promoted.
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4)], ledger)
    assert ledger["ghrepo:acme/widget"]["streak"] == 2, "history survives re-promotion"


# ---------------------------------------------------------------------------
# Carryover candidates
# ---------------------------------------------------------------------------

def test_carryover_items_rescore_from_current_signals():
    """An item promoted while small can outrank its original self once it has grown."""
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=3,
                                      signals={"gh_stars": 10})])
    ledger, _ = _run(ledger, "2026-07-02", fetchers=fake_fetchers(stars=9000))

    items = track.carryover_items(ledger)
    assert len(items) == 1
    it = items[0]
    assert it["carryover"] is True
    assert it["streak"] == 2
    assert it["traction_delta"] > 0
    assert it["signals"]["gh_stars"] == 9000
    assert "trending (Tier-2 signal)" in it["score_reasons"]
    assert it["score"] >= 2


def test_carryover_items_drop_below_the_routing_floor():
    ledger = {"ghrepo:acme/quiet": {
        "id": "ghrepo:acme/quiet", "title": "acme/quiet", "url": "https://github.com/acme/quiet",
        "source": "GitHub Trending", "category": "releases", "links": {}, "summary": "",
        "keywords": [], "first_seen": "2026-07-01", "last_seen": "2026-07-02", "streak": 2,
        "misses": 0, "flat_runs": 0, "signals": {"gh_stars": 3}, "mag_history": [1.0, 1.1],
        "peak_mag": 1.1,
    }}
    assert track.carryover_items(ledger) == []


def test_write_carryovers_never_clobbers_a_fresh_observation(scored_dir):
    """If today's collection produced the item too, the freshly collected copy wins."""
    (scored_dir / "ghrepo_acme_widget.json").write_text(json.dumps({"fresh": True}))
    n = track.write_carryovers([make_item(id="ghrepo:acme/widget", carryover=True)])
    assert n == 0
    assert json.loads((scored_dir / "ghrepo_acme_widget.json").read_text()) == {"fresh": True}


def test_write_carryovers_writes_new_ones(scored_dir):
    n = track.write_carryovers([make_item(id="ghrepo:acme/other", carryover=True)])
    assert n == 1
    written = json.loads((scored_dir / "ghrepo_acme_other.json").read_text())
    assert written["carryover"] is True


# ---------------------------------------------------------------------------
# Ledger IO
# ---------------------------------------------------------------------------

def test_the_suite_never_reads_the_committed_ledger():
    """Guard for conftest's autouse isolation.

    `promote()` with no ledger argument falls back to `load_ledger()`, and `LEDGER` points at
    `data/tracked.json` — the file the daily run commits. If that default ever reaches the
    tests again, every assertion about ledger contents starts depending on what the radar was
    tracking that morning."""
    from collectors.common import ROOT
    assert track.LEDGER != ROOT / "data" / "tracked.json"
    assert track.promote([]) == {}


def test_a_corrupt_ledger_costs_memory_not_the_digest(ledger_path):
    ledger_path.write_text("{ this is not json")
    assert track.load_ledger() == {}


def test_ledger_roundtrips(ledger_path):
    ledger = track.promote([make_item(id="ghrepo:acme/widget", score=4)])
    track.save_ledger(ledger)
    assert track.load_ledger() == ledger
