"""End-to-end: three simulated daily runs through score -> track -> synthesize.

This is the test that pins the behaviour the repo shipped without for its whole life. It
reproduces the exact CI conditions that broke the radar:

  * `data/raw/` is gitignored and rebuilt from scratch every run;
  * `data/seen.json` dedups an item forever, so a second run collects nothing it saw before.

Under those conditions the old pipeline produced a disjoint scored set every day — hence
streaks stuck at 1, no movers, no story arcs, and an empty digest whenever the day was quiet.
Here, day two and day three collect *nothing at all*, which is the worst case, and the digest
still has candidates, movers, and eventually an arc.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

import pytest

from collectors import common
from distill import score as score_mod, synthesize, delta, track
from collectors.common import make_item as raw_item


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Redirect every persistent path the pipeline touches into tmp_path."""
    raw = tmp_path / "raw"
    scored = tmp_path / "scored"
    raw.mkdir()
    scored.mkdir()
    monkeypatch.setattr(common, "RAW", raw)
    monkeypatch.setattr(common, "SEEN_PATH", tmp_path / "seen.json")
    monkeypatch.setattr(score_mod, "SCORED", scored)
    monkeypatch.setattr(track, "SCORED", scored)
    monkeypatch.setattr(track, "LEDGER", tmp_path / "tracked.json")
    monkeypatch.setattr(synthesize, "SCORED", scored)
    monkeypatch.setattr(synthesize, "ENRICHED", tmp_path / "enriched")
    monkeypatch.setattr(synthesize, "cluster_items", lambda items: [])
    monkeypatch.setattr(delta, "STATE_PATH", tmp_path / "state.json")
    return tmp_path


def _collect_day_one(raw_dir):
    """One trackable repo and one HF-featured paper — a modest but normal day."""
    now = datetime.now(timezone.utc).isoformat()
    items = [
        raw_item(id="ghrepo:getzep/graphiti", category="releases",
                 title="getzep/graphiti — real-time knowledge graphs for agents",
                 url="https://github.com/getzep/graphiti", source="GitHub Trending",
                 raw_summary="Temporal knowledge graphs for agent memory.",
                 signals={"gh_stars": 900}),
        raw_item(id="arxiv:2501.01234", category="research",
                 title="Sparse autoencoders for circuit discovery",
                 url="https://arxiv.org/abs/2501.01234", source="HF Daily Papers",
                 raw_summary="We train SAEs to recover interpretable circuits.",
                 links={"github": "https://github.com/acme/sae-circuits"},
                 signals={"hf_upvotes": 40}),
    ]
    for it in items:
        it["fetched"] = now
        d = raw_dir / it["category"]
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{it['id'].replace(':', '_').replace('/', '_')}.json").write_text(json.dumps(it))


def _run_day(day, fetchers):
    """score -> track -> synthesize, as scripts/distill.sh runs them."""
    score_mod.main()
    ledger = track.load_ledger()
    if ledger:
        real_today = track._today
        track._today = lambda: day
        try:
            ledger, _ = track.refresh(ledger, fetchers=fetchers)
        finally:
            track._today = real_today
        track.save_ledger(ledger)
        track.write_carryovers(track.carryover_items(ledger))

    items = synthesize.load_scored()
    d = delta.compute_delta(items)
    system, user, n_candidates = synthesize.build_prompt(items)
    delta.save_state(items)
    track.save_ledger(track.promote(items, track.load_ledger()))
    return {"items": items, "delta": d, "user": user, "n": n_candidates}


def test_three_days_with_nothing_new_after_the_first(pipeline):
    raw = pipeline / "raw"
    _collect_day_one(raw)

    # --- Day 1: a normal collection day. -----------------------------------------------
    stars = {"ghrepo:getzep/graphiti": 900, "arxiv:2501.01234": 900}
    fetchers = {
        "github": lambda o, r: {"stars": stars["ghrepo:getzep/graphiti"], "forks": 5},
        "hf_paper": lambda key: {"hf_upvotes": 40},
    }
    day1 = _run_day("2026-07-01", fetchers)
    assert day1["n"] == 2
    assert day1["delta"]["first_run"] is True
    assert len(track.load_ledger()) == 2, "both items go on the radar"

    # --- Day 2: collectors return nothing (everything already in seen.json). ------------
    # The raw corpus is wiped exactly as a fresh CI checkout would leave it.
    for p in raw.rglob("*.json"):
        p.unlink()
    # Stars are weighted 0.5 in `magnitude`, so clearing DELTA_MAG_EPS on stars alone takes
    # roughly a tripling — 900 -> 3600 is a move; 900 -> 2400 is deliberately not.
    fetchers["github"] = lambda o, r: {"stars": 3600, "forks": 20}
    fetchers["hf_paper"] = lambda key: {"hf_upvotes": 95}

    day2 = _run_day("2026-07-02", fetchers)
    assert day2["n"] == 2, "a day with zero new items still has something to publish"
    assert all(i.get("carryover") for i in day2["items"])
    assert len(day2["delta"]["climbing"]) == 2, "traction growth is finally visible"
    assert day2["delta"]["new"] == [], "carryovers are not passed off as new"
    assert '"carryover": true' in day2["user"]

    # --- Day 3: still nothing new, traction still rising. -------------------------------
    fetchers["github"] = lambda o, r: {"stars": 12000, "forks": 40}
    fetchers["hf_paper"] = lambda key: {"hf_upvotes": 210}

    day3 = _run_day("2026-07-03", fetchers)
    assert day3["n"] == 2
    entry = track.load_ledger()["ghrepo:getzep/graphiti"]
    assert entry["streak"] == 3
    assert entry["signals"]["gh_stars"] == 12000, "the digest quotes today's count, not day one's"

    arcs = delta.story_arcs()
    assert arcs, "story arcs fire on the third consecutive rising observation"
    assert "STORY ARCS" in day3["user"], "and they reach the model"
    assert {a["title"] for a in arcs} == {i["title"] for i in day3["items"]}


def test_a_freshly_collected_item_beats_its_carryover_copy(pipeline):
    """When an item is collected again on a later day, the freshly collected copy wins —
    otherwise a stale ledger row would shadow a live observation."""
    raw = pipeline / "raw"
    _collect_day_one(raw)
    fetchers = {"github": lambda o, r: {"stars": 900, "forks": 5},
                "hf_paper": lambda key: {"hf_upvotes": 40}}
    _run_day("2026-07-01", fetchers)

    # Day 2 re-collects graphiti with a much higher star count.
    for p in raw.rglob("*.json"):
        if "graphiti" not in p.name:
            p.unlink()
    p = next(raw.rglob("*graphiti*.json"))
    it = json.loads(p.read_text())
    it["signals"]["gh_stars"] = 12000
    it["fetched"] = datetime.now(timezone.utc).isoformat()
    p.write_text(json.dumps(it))

    fetchers["github"] = lambda o, r: {"stars": 950, "forks": 5}   # stale ledger observation
    day2 = _run_day("2026-07-02", fetchers)

    graphiti = next(i for i in day2["items"] if i["id"] == "ghrepo:getzep/graphiti")
    assert graphiti["signals"]["gh_stars"] == 12000
    assert not graphiti.get("carryover"), "it was collected today, so it is not a carryover"


def test_an_item_that_stops_moving_leaves_the_radar(pipeline):
    """The ledger is committed to git daily; it must not accumulate dead weight."""
    raw = pipeline / "raw"
    _collect_day_one(raw)
    fetchers = {"github": lambda o, r: {"stars": 900, "forks": 5},
                "hf_paper": lambda key: {"hf_upvotes": 40}}
    _run_day("2026-07-01", fetchers)
    for p in raw.rglob("*.json"):
        p.unlink()

    for day in range(2, 10):
        _run_day(f"2026-07-{day:02d}", fetchers)      # flat traction, every run

    assert track.load_ledger() == {}
