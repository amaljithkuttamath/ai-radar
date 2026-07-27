"""Prompt assembly: which candidates actually reach the model, and how they are labelled."""
from __future__ import annotations
import json
import re

import pytest

from distill import synthesize, delta, track
from tests.conftest import make_item


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Keep build_prompt off the repo's real state, ledger and enrichment cache, and out of
    the clustering path (which can reach for an embedder)."""
    monkeypatch.setattr(synthesize, "ENRICHED", tmp_path / "enriched")
    monkeypatch.setattr(synthesize, "cluster_items", lambda items: [])
    monkeypatch.setattr(delta, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(track, "LEDGER", tmp_path / "tracked.json")


def _candidates(user: str) -> list[dict]:
    """The compact candidate array build_prompt appends to the user message."""
    return json.loads(re.search(r"\n(\[[\s\S]*\])\s*$", user).group(1))


# Distinct subject words per item. The diversity pass collapses near-duplicate titles, so a
# fixture of "Item 1 / Item 2 / Item 3" would legitimately arrive as a single candidate and
# these tests would be measuring the wrong thing.
_WORDS = ["interpretability", "quantization", "retrieval", "planning", "diffusion", "kernels",
          "tokenizers", "distillation", "routing", "scheduling", "caching", "alignment",
          "sparsity", "decoding", "attention", "benchmarking", "serving", "compilation",
          "clustering", "provenance", "batching", "pruning", "embeddings", "guardrails",
          "telemetry", "sharding", "annotation", "curricula", "checkpoints", "watermarking",
          "orchestration", "federation", "calibration", "augmentation", "verification",
          "summarization", "grounding", "steering", "profiling", "replication", "sampling",
          "regularization", "normalization", "memoization", "prefetching"]


def _fresh(n, score=3):
    return [make_item(id=f"fresh-{i}", title=f"A study of {_WORDS[i]}", category="research",
                      source=f"arXiv feed {i}", score=score,
                      signals={"hf_upvotes": 30 + i}) for i in range(n)]


def _carried(n, score=3, delta_=1.5):
    return [make_item(id=f"ghrepo:acme/carry-{i}", title=f"acme/{_WORDS[-1 - i]}-toolkit",
                      source=f"GitHub Trending {i}", score=score, carryover=True, streak=3,
                      first_seen="2026-07-01", traction_delta=delta_,
                      signals={"gh_stars": 500 + i}) for i in range(n)]


def test_carryovers_are_capped_on_a_busy_day():
    """A normal window is mostly about what's new; carryovers get a small reserved slice."""
    _, user, _ = synthesize.build_prompt(_fresh(10) + _carried(10))
    rows = _candidates(user)
    assert sum(1 for r in rows if r.get("carryover")) == synthesize.CARRYOVER_SLOTS


def test_a_quiet_window_falls_back_on_what_the_radar_is_tracking():
    """Historically a day with one new item shipped a one-item digest — or an empty one."""
    _, user, n = synthesize.build_prompt(_fresh(1) + _carried(10))
    assert n >= synthesize.QUIET_FLOOR
    rows = _candidates(user)
    assert sum(1 for r in rows if r.get("carryover")) == synthesize.QUIET_FLOOR - 1


def test_a_window_with_no_fresh_items_still_produces_candidates():
    _, user, n = synthesize.build_prompt(_carried(10))
    assert n == synthesize.QUIET_FLOOR


def test_nothing_at_all_yields_an_empty_candidate_set():
    """The genuinely-empty case must stay empty rather than invent filler."""
    _, _, n = synthesize.build_prompt([])
    assert n == 0


def test_carryovers_carry_the_context_the_model_needs_to_label_them():
    _, user, _ = synthesize.build_prompt(_carried(2))
    row = next(r for r in _candidates(user) if r.get("carryover"))
    assert row["runs_tracked"] == 3
    assert row["first_seen"] == "2026-07-01"
    assert row["traction_delta"] == 1.5
    assert "Never describe a carryover as new" in user


def test_fresh_items_are_not_labelled_as_carryovers():
    _, user, _ = synthesize.build_prompt(_fresh(3))
    assert all("carryover" not in r for r in _candidates(user))


def test_traction_figures_are_promoted_to_named_fields():
    """Buried inside `signals` the model flattens them into 'growing interest'."""
    _, user, _ = synthesize.build_prompt(_fresh(1))
    row = _candidates(user)[0]
    assert row["hf_upvotes"] == 30
    assert set(row) >= {"title", "url", "source", "category", "score", "gh_stars", "hn_points"}


def test_compact_delta_keeps_counts_exact_while_truncating_rows():
    """The prompt gets a sample of movers, but the counts it reports must be the real ones —
    a busy window marks 300+ items new and dumping them all overflows the input limit."""
    big = {"first_run": False,
           "new": [{"title": f"t{n}", "url": "u", "score": 3} for n in range(300)],
           "climbing": [], "cooled": []}
    out = synthesize._compact_delta(big, top=5)
    assert out["new"]["count"] == 300
    assert len(out["new"]["top"]) == 5


def test_category_quotas_reserve_room_for_non_research():
    """Hardware and releases score lower than papers structurally; without a floor they are
    crowded out entirely."""
    items = (_fresh(40)
             + [make_item(id=f"hw-{i}", title=f"NVIDIA ships {_WORDS[i]} hardware",
                          category="hardware",
                          source=f"NVIDIA Blog {i}", score=1, signals={}) for i in range(4)])
    _, user, _ = synthesize.build_prompt(items, max_candidates=20)
    rows = _candidates(user)
    assert 0 < sum(1 for r in rows if r["category"] == "hardware") <= synthesize.HARDWARE_SLOTS


def test_shrink_knobs_reduce_the_payload():
    """The 413 fallback path: fewer candidates and shorter summaries must actually be sent."""
    items = _fresh(30)
    _, big, n_big = synthesize.build_prompt(items, max_candidates=24, summary_chars=600)
    _, small, n_small = synthesize.build_prompt(items, max_candidates=8, summary_chars=80)
    assert n_small < n_big
    assert len(small) < len(big)
