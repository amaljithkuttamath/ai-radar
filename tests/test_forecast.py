"""Tests for the deferred ground truth and the Goodhart brake (ADR-0009 §3).

What is actually being protected here. The coder edits `distill/digest.md`; the grader
scores the digest that prompt writes. Gao, Schulman & Hilton (ICML 2023) measured what
happens next: past some optimisation pressure the proxy keeps climbing while ground truth
falls. The divergence point is unpredictable, but the divergence is detectable — provided
you hold a signal the optimiser is not optimising.

`forecast.py` manufactures one out of something the repo was already throwing away: a digest
that says "Climbing" has made a falsifiable claim, and `tracked.json`'s `mag_history` settles
it three runs later. The tests below are mostly about the ways that ground truth could be
quietly corrupted, because a corrupted ground truth is worse than none — the brake would
then be measuring the same fiction it exists to catch.

Run: uv run --group dev pytest tests/test_forecast.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from grader import forecast, trusted  # noqa: E402
import check_whitelist  # noqa: E402

DIGEST = """\
# AI Radar — 2026-09-19

## What changed

**New today**
- [Brand new](https://arxiv.org/abs/2609.00001) — a thing

**Climbing**
- [Rising paper](https://arxiv.org/abs/2609.11111) — traction +2.5x

**Cooled**
- [Falling paper](https://arxiv.org/abs/2609.22222) — fell off radar

## Main list

### 1. Something · 4/5

## Story arcs

- **An Arc With No Link** — seen 4 runs, traction +127.8% since first seen.

## Still developing

- **A Flat Item** — 8th run, traction flat.
"""


def _ledger(**series) -> dict:
    return {k: {"id": k, "mag_history": list(v), "misses": 0,
                "title": {"arxiv:2609.33333": "An Arc With No Link",
                          "arxiv:2609.44444": "A Flat Item"}.get(k, f"Title {k}")}
            for k, v in series.items()}


# --- what counts as a claim -------------------------------------------------

def test_urls_map_onto_the_collectors_id_scheme():
    assert forecast.item_key("https://arxiv.org/abs/2609.17523") == "arxiv:2609.17523"
    assert forecast.item_key("https://huggingface.co/org/model") == "hfmodel:org/model"
    assert forecast.item_key("https://huggingface.co/datasets/org/ds") == "hfdataset:org/ds"
    assert forecast.item_key("https://github.com/org/repo") == "ghrepo:org/repo"
    assert forecast.item_key("https://example.com/whatever") is None


def test_climbing_and_cooled_are_claims_with_opposite_directions():
    claims = {c["key"]: c for c in forecast.extract_claims(DIGEST)}
    assert claims["arxiv:2609.11111"]["direction"] == "up"
    assert claims["arxiv:2609.22222"]["direction"] == "down"


def test_new_today_is_not_a_claim():
    """"New today" asserts nothing about the future. Scoring it would invent a prediction
    the digest never made."""
    assert "arxiv:2609.00001" not in {c["key"] for c in forecast.extract_claims(DIGEST)}


def test_still_developing_is_not_a_claim():
    """Its real entries routinely say "traction flat", so the section asserts continued
    attention, not continued rise. Counting it as "up" would guarantee a stream of wrong
    verdicts against claims nobody made."""
    assert "Still developing" not in forecast.CLAIM_SECTIONS
    ledger = _ledger(**{"arxiv:2609.44444": [1.0, 1.0]})
    assert forecast.extract_claims(DIGEST, ledger) == [
        c for c in forecast.extract_claims(DIGEST, ledger) if c["section"] != "Still developing"]


def test_bold_entries_without_links_are_resolved_by_title():
    """Story arcs and Cooled name the item in bold with no URL. Matching only URLs saw a
    third of the claims, which is too small a sample for an accuracy figure to mean
    anything."""
    ledger = _ledger(**{"arxiv:2609.33333": [1.0, 2.0]})
    keys = {c["key"] for c in forecast.extract_claims(DIGEST, ledger)}
    assert "arxiv:2609.33333" in keys


def test_an_ambiguous_title_is_dropped_rather_than_guessed():
    """Resolving to the wrong series would put a fabricated verdict into the one metric
    here that is meant to be incorruptible."""
    ledger = {"a": {"title": "Same Name", "mag_history": [1.0]},
              "b": {"title": "same   name!", "mag_history": [1.0]}}
    assert forecast.title_index(ledger) == {}


def test_a_claim_about_an_untracked_item_is_dropped():
    """There is no series to settle it against, and inventing one is the fabrication this
    module exists to avoid."""
    assert forecast.open_claims(DIGEST, {}, "2026-09-19") == []


def test_claims_record_the_series_length_they_were_made_at():
    """`mag_history` has order but no timestamps, so the length at claim time is the only
    way to later ask "and what happened after that?"."""
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 2.0, 3.0]})
    claim = forecast.open_claims(DIGEST, ledger, "2026-09-19")[0]
    assert claim["history_len"] == 3
    assert claim["mag_at_claim"] == 3.0


# --- settling ---------------------------------------------------------------

def _claim(direction="up", mag=10.0, at=2):
    return {"key": "arxiv:2609.11111", "direction": direction, "section": "Climbing",
            "title": "t", "url": "", "date": "2026-09-19",
            "mag_at_claim": mag, "history_len": at}


def test_a_claim_is_unsettled_until_the_horizon_has_passed():
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 10.0, 11.0]})
    assert forecast.settle(_claim(), ledger) is None


def test_a_rising_item_confirms_an_up_claim():
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 10.0, 11.0, 12.0, 20.0]})
    assert forecast.settle(_claim(), ledger)["verdict"] == "correct"


def test_a_falling_item_refutes_an_up_claim():
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 10.0, 9.0, 8.0, 5.0]})
    assert forecast.settle(_claim(), ledger)["verdict"] == "wrong"


def test_a_falling_item_confirms_a_down_claim():
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 10.0, 9.0, 8.0, 5.0]})
    assert forecast.settle(_claim(direction="down"), ledger)["verdict"] == "correct"


def test_jitter_inside_the_flat_band_is_neither_right_nor_wrong():
    """Counting re-fetch noise as a successful forecast would inflate the single metric
    here that is supposed to be incorruptible."""
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 10.0, 10.1, 10.2, 10.3]})
    assert forecast.settle(_claim(), ledger)["verdict"] == "flat"


def test_a_zero_baseline_does_not_divide_by_zero():
    ledger = _ledger(**{"arxiv:2609.11111": [0.0, 0.0, 0.0, 0.0, 0.0]})
    assert forecast.settle(_claim(mag=0.0), ledger)["verdict"] == "flat"


def test_accuracy_excludes_flat_claims_from_the_denominator():
    """"Traction did not move much" says nothing about whether the digest read the item
    correctly, so it is not a failure."""
    settled = [{"verdict": "correct"}, {"verdict": "wrong"},
               {"verdict": "flat"}, {"verdict": "flat"}]
    assert forecast.accuracy(settled) == 0.5


def test_accuracy_is_unknown_rather_than_zero_without_evidence():
    """Same rule tier 0 applies with `ok=None`: no evidence is not evidence of failure."""
    assert forecast.accuracy([]) is None
    assert forecast.accuracy([{"verdict": "flat"}]) is None


# --- the ledger -------------------------------------------------------------

def test_update_settles_records_and_does_not_duplicate(tmp_path):
    p = tmp_path / "forecasts.jsonl"
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 10.0],
                        "arxiv:2609.22222": [1.0, 10.0]})
    first = forecast.update(DIGEST, ledger, "2026-09-19", p)
    assert first["claims_recorded"] == 2

    # same digest, same day -> nothing new, and the open claims are still pending
    second = forecast.update(DIGEST, ledger, "2026-09-19", p)
    assert second["claims_recorded"] == 0
    assert second["claims_pending"] == 2


def test_update_resolves_once_the_series_grows(tmp_path):
    p = tmp_path / "forecasts.jsonl"
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 10.0], "arxiv:2609.22222": [1.0, 10.0]})
    forecast.update(DIGEST, ledger, "2026-09-19", p)

    grown = _ledger(**{"arxiv:2609.11111": [1.0, 10.0, 12.0, 14.0, 20.0],
                       "arxiv:2609.22222": [1.0, 10.0, 12.0, 14.0, 20.0]})
    stats = forecast.update(DIGEST, grown, "2026-09-23", p)
    assert stats["claims_settled"] == 2
    # the "Climbing" claim rose (correct); the "Cooled" claim also rose (wrong)
    assert stats["forecast_accuracy"] == 0.5


def test_a_settled_claim_is_never_re_settled(tmp_path):
    p = tmp_path / "forecasts.jsonl"
    ledger = _ledger(**{"arxiv:2609.11111": [1.0, 10.0]})
    forecast.update(DIGEST, ledger, "2026-09-19", p)
    grown = _ledger(**{"arxiv:2609.11111": [1.0, 10.0, 12.0, 14.0, 20.0]})
    forecast.update(DIGEST, grown, "2026-09-23", p)
    verdicts = [c["verdict"] for c in forecast.load(p) if c.get("verdict")]
    forecast.update(DIGEST, grown, "2026-09-24", p)
    assert [c["verdict"] for c in forecast.load(p) if c.get("verdict")] == verdicts


def test_a_malformed_line_does_not_take_out_the_ledger(tmp_path):
    p = tmp_path / "forecasts.jsonl"
    p.write_text('{"key": "a"}\ngarbage\n{"key": "b"}\n')
    assert [c["key"] for c in forecast.load(p)] == ["a", "b"]


# --- the Goodhart brake -----------------------------------------------------

def _history(n, overall, reobs, start=0):
    return [{"date": f"2026-09-{start + i:02d}", "mode": "normal", "overall": overall,
             "trusted": {"reobservation_rate": reobs}} for i in range(n)]


def test_no_divergence_when_the_proxy_is_not_rising():
    """Nothing to be suspicious of: Goodhart is specifically proxy-up, truth-down."""
    history = _history(14, 4.0, 0.9) + _history(14, 4.2, 0.8)
    assert trusted.divergence(history) is None


def test_divergence_when_the_rubric_rises_and_ground_truth_falls():
    history = _history(14, 4.5, 0.6) + _history(14, 3.8, 0.9)
    finding = trusted.divergence(history)
    assert finding["metric"] == "reobservation_rate"
    assert finding["drop"] > trusted.DEGRADE_BAND
    assert "Goodhart" in finding["detail"]


def test_no_divergence_when_both_rise():
    assert trusted.divergence(_history(14, 4.5, 0.95) + _history(14, 3.8, 0.9)) is None


def test_small_trusted_movements_are_noise_not_regression():
    history = _history(14, 4.5, 0.88) + _history(14, 3.8, 0.90)
    assert trusted.divergence(history) is None


def test_the_brake_will_not_fire_on_a_thin_sample():
    """Its response is to revert a change. Firing on noise is strictly worse than not
    firing."""
    history = _history(3, 4.5, 0.5) + _history(3, 3.8, 0.9)
    assert trusted.divergence(history) is None


def test_deterministic_evals_cannot_trigger_the_brake():
    """A model's absence is not a falling score. Otherwise the brake would revert changes
    every time the provider was down — precisely when nothing was being optimised."""
    blank = [{"date": "d", "mode": "deterministic", "trusted": {"reobservation_rate": 0.1}}
             for _ in range(30)]
    assert trusted.divergence(blank) is None


def test_reading_omits_metrics_it_could_not_compute():
    """A metric that could not be computed is not a metric that read zero."""
    assert trusted.reading({"metrics": {}}, {}) == {}
    assert trusted.reading({"metrics": {"reobservation_rate": 0.9}},
                           {"forecast_accuracy": None}) == {"reobservation_rate": 0.9}


# --- invariant I-10 ---------------------------------------------------------

def test_the_trusted_set_is_out_of_the_coders_reach():
    """I-10, checked against the real whitelist. If this fails, the Goodhart brake is
    reading a number the planner can move, and is measuring nothing."""
    roles = check_whitelist.parse_whitelist(check_whitelist.WHITELIST.read_text())
    assert check_whitelist.trusted_disjointness(roles["coder"]) == []


def test_i10_fires_when_a_trusted_source_becomes_writable():
    violations = check_whitelist.trusted_disjointness(
        ["distill/track.py"], {"reobservation_rate": ["distill/track.py"]})
    assert violations and "I-10" in violations[0]


def test_i10_catches_a_directory_level_widening():
    """`collectors/` and `collectors/*.py` are the same problem stated two ways."""
    assert check_whitelist.trusted_disjointness(
        ["collectors/*.py"], {"m": ["collectors/"]})


def test_the_duplicated_trusted_sources_agree_with_the_package():
    """`check_whitelist.py` must run before any dependency install, so it cannot import the
    package it polices. The copy is the price; drift is the risk this test removes."""
    assert check_whitelist.TRUSTED_SOURCES.keys() == trusted.SOURCES.keys()
    for metric, paths in trusted.SOURCES.items():
        assert list(paths) == check_whitelist.TRUSTED_SOURCES[metric]


def test_the_evaluator_is_a_fence_not_merely_out_of_scope():
    """ADR-0009. Before this, an agent editing the thing that grades it tripped the same
    check as an agent editing an unrelated file."""
    assert check_whitelist.is_fence("grader/deterministic.py")
    assert check_whitelist.is_fence("grader/forecast.py")
    assert check_whitelist.is_fence("evals/rubric.md")
    assert not check_whitelist.is_fence("evals/backlog.md")
