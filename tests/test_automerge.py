"""Tests for the archive and the auto-merge gate (ADR-0009 §2, §4).

The gate is the only thing standing between an agent and `main`, so it lives in Python with
tests rather than in YAML. Each condition is checked in isolation *and* for the property
that matters more: that it refuses by default. A gate that fails open is worse than no gate,
because it looks like one.

Run: uv run --group dev pytest tests/test_automerge.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from grader import archive  # noqa: E402
import automerge  # noqa: E402

ALLOWED = ["config/sources.yaml", "config/profile.yaml", "distill/digest.md",
           "evals/backlog.md"]


def _gate(files=("distill/digest.md",), **over):
    kw = dict(additions=8, deletions=2, recent_automerges=0,
              tier0_before={"failed": []}, tier0_after={"failed": []},
              retired_classes={}, allowed_paths=ALLOWED)
    kw.update(over)
    return automerge.gate(list(files), **kw)


# --- the happy path is deliberately narrow ---------------------------------

def test_a_small_whitelisted_prompt_change_is_allowed():
    assert _gate().allowed


def test_nothing_to_merge_is_refused_rather_than_trivially_allowed():
    """An empty change set must not satisfy "every file is fine" vacuously."""
    assert not _gate(files=()).allowed


# --- condition 1: path and kind --------------------------------------------

def test_code_is_never_auto_merged():
    """A prompt's blast radius is bounded by the next run's output. A .py file's is not,
    and no amount of diff review in CI closes that gap."""
    d = _gate(files=("distill/synthesize.py",))
    assert not d.allowed
    assert any("not prompt or config text" in r for r in d.refusals)


def test_an_out_of_whitelist_path_is_refused():
    assert not _gate(files=("README.md",)).allowed


def test_a_fence_path_is_refused_as_a_fence_not_as_a_near_miss():
    """I-08. A PR touching the evaluator is not a borderline case — and the refusal has to
    say so, because the two get handled very differently by whoever reads it."""
    d = _gate(files=("grader/deterministic.py",))
    assert not d.allowed
    assert any("fence path (I-08)" in r for r in d.refusals)


def test_the_rubric_is_a_fence_too():
    d = _gate(files=("evals/rubric.md",))
    assert any("fence path (I-08)" in r for r in d.refusals)


def test_an_odd_extension_is_refused_even_inside_the_whitelist():
    """Allow-list, not deny-list: a file type nobody thought about is refused rather than
    waved through."""
    assert not _gate(files=("config/sources.json",),
                     allowed_paths=ALLOWED + ["config/sources.json"]).allowed


# --- condition 2: size ------------------------------------------------------

def test_a_large_diff_is_refused():
    assert not _gate(additions=30, deletions=0).allowed


def test_exactly_the_bound_is_allowed():
    assert _gate(additions=automerge.MAX_CHANGED_LINES, deletions=0).allowed


def test_two_files_are_refused_even_when_both_are_allowed():
    """A structural block on batching an unrelated change into an approved one."""
    d = _gate(files=("distill/digest.md", "config/profile.yaml"))
    assert not d.allowed
    assert any("files changed" in r for r in d.refusals)


# --- condition 3: the pre-merge shadow eval ---------------------------------

def test_a_newly_failing_check_blocks_the_merge():
    d = _gate(tier0_before={"failed": []}, tier0_after={"failed": ["links_resolve"]})
    assert not d.allowed
    assert any("tier-0 regression" in r for r in d.refusals)


def test_an_already_failing_check_does_not_block():
    """The PR did not cause it, and refusing here would mean nothing could ever be merged
    while an unrelated check was red."""
    assert _gate(tier0_before={"failed": ["links_resolve"]},
                 tier0_after={"failed": ["links_resolve"]}).allowed


def test_fixing_a_check_is_not_a_regression():
    assert _gate(tier0_before={"failed": ["links_resolve"]}, tier0_after={"failed": []}).allowed


def test_a_missing_shadow_eval_is_noted_rather_than_silently_ignored():
    """Permissive here is safe only because it is one condition of five — and the note is
    what makes that visible in the log instead of implicit."""
    d = _gate(tier0_before=None, tier0_after=None)
    assert d.allowed
    assert any("shadow eval" in n for n in d.notes)


# --- condition 4: rate ------------------------------------------------------

def test_a_second_automerge_inside_the_cooldown_is_refused():
    """Each automatic change needs an observation window to itself, or the archive cannot
    attribute what either of them did."""
    d = _gate(recent_automerges=1)
    assert not d.allowed
    assert any("observation window" in r for r in d.refusals)


# --- condition 5: the archive's veto ----------------------------------------

def test_a_retired_edit_class_is_refused():
    d = _gate(retired_classes={"distill/digest.md": "2 consecutive harmed verdicts"})
    assert not d.allowed
    assert any("retired" in r for r in d.refusals)


# --- refusals accumulate ----------------------------------------------------

def test_every_reason_is_reported_not_just_the_first():
    """Reporting only the first refusal turns fixing a PR into a guessing game."""
    d = _gate(files=("distill/synthesize.py",), additions=99, recent_automerges=2)
    assert len(d.refusals) >= 3


# --- the archive ------------------------------------------------------------

def _eval(date, *, overall=None, reobs=None, files=None, mode="normal"):
    ev = {"date": date, "mode": mode,
          "trusted": {} if reobs is None else {"reobservation_rate": reobs},
          "revs": {"files": files or {}}}
    if overall is not None:
        ev["overall"] = overall
    return ev


def test_change_events_come_from_revision_transitions():
    """No second ledger to maintain: `provenance.py` already stamps each eval, so a change
    is a transition in those stamps."""
    history = [                                     # newest first
        _eval("2026-09-20", files={"distill/digest.md": "bbb"}),
        _eval("2026-09-19", files={"distill/digest.md": "aaa"}),
        _eval("2026-09-18", files={"distill/digest.md": "aaa"}),
    ]
    events = archive.change_events(history)
    assert len(events) == 1
    assert events[0]["at"] == "2026-09-20"
    assert events[0]["edit_class"] == "distill/digest.md"


def test_evals_without_provenance_are_skipped_not_treated_as_a_change():
    """Everything before ADR-0009 lacks `revs`. The absence of provenance is not evidence
    that everything changed at once."""
    assert archive.change_events([{"date": "2026-07-13"}, {"date": "2026-07-12"}]) == []


def test_a_change_followed_by_a_trusted_fall_is_harmed():
    history = ([_eval(f"2026-09-2{i}", overall=4.0, reobs=0.5,
                      files={"distill/digest.md": "bbb"}) for i in range(5)]
               + [_eval(f"2026-09-1{i}", overall=4.0, reobs=0.9,
                        files={"distill/digest.md": "aaa"}) for i in range(5)])
    entry = archive.build(history)[0]
    assert entry["verdict"] == "harmed"


def test_the_goodhart_shape_is_named_in_the_why():
    """Rubric up, ground truth down is the specific pattern Gao et al. describe, and saying
    so in the record is what makes the verdict reviewable."""
    history = ([_eval(f"2026-09-2{i}", overall=4.6, reobs=0.5,
                      files={"distill/digest.md": "bbb"}) for i in range(5)]
               + [_eval(f"2026-09-1{i}", overall=3.9, reobs=0.9,
                        files={"distill/digest.md": "aaa"}) for i in range(5)])
    assert "Goodhart" in archive.build(history)[0]["why"]


def test_a_rising_trusted_metric_is_helped():
    history = ([_eval(f"2026-09-2{i}", overall=4.0, reobs=0.95,
                      files={"distill/digest.md": "bbb"}) for i in range(5)]
               + [_eval(f"2026-09-1{i}", overall=4.0, reobs=0.6,
                        files={"distill/digest.md": "aaa"}) for i in range(5)])
    assert archive.build(history)[0]["verdict"] == "helped"


def test_a_rising_rubric_alone_never_earns_helped():
    """The rubric is the proxy the change may have been optimising. A rising proxy is not
    evidence of improvement — that is the entire finding."""
    history = ([_eval(f"2026-09-2{i}", overall=5.0, reobs=0.9,
                      files={"distill/digest.md": "bbb"}) for i in range(5)]
               + [_eval(f"2026-09-1{i}", overall=3.0, reobs=0.9,
                        files={"distill/digest.md": "aaa"}) for i in range(5)])
    assert archive.build(history)[0]["verdict"] == "neutral"


def test_a_thin_window_is_inconclusive_not_neutral():
    """"Not enough evidence" and "no effect" are different claims, and collapsing them
    would let a change with two days of data retire an edit class."""
    history = [_eval("2026-09-20", overall=4.0, reobs=0.9,
                     files={"distill/digest.md": "bbb"}),
               _eval("2026-09-19", overall=4.0, reobs=0.9,
                     files={"distill/digest.md": "aaa"})]
    assert archive.build(history)[0]["verdict"] == "inconclusive"


def test_two_consecutive_harmed_verdicts_retire_an_edit_class():
    arch = [{"edit_class": "distill/digest.md", "verdict": "harmed", "at": "2026-09-20",
             "why": "reobservation_rate fell 20%"},
            {"edit_class": "distill/digest.md", "verdict": "harmed", "at": "2026-09-10",
             "why": "reobservation_rate fell 15%"}]
    retired = archive.retired(arch)
    assert "distill/digest.md" in retired
    assert "2 consecutive" in retired["distill/digest.md"]


def test_one_harmed_verdict_does_not_retire():
    """A single daily sample is noisy."""
    arch = [{"edit_class": "distill/digest.md", "verdict": "harmed", "at": "2026-09-20",
             "why": "x"}]
    assert archive.retired(arch) == {}


def test_a_class_recovers_on_its_next_non_harmful_verdict():
    """Verdicts, not permanent bans: a class that was harmful and has since been fixed must
    not stay retired on its history."""
    arch = [{"edit_class": "distill/digest.md", "verdict": "helped", "at": "2026-09-22",
             "why": "x"},
            {"edit_class": "distill/digest.md", "verdict": "harmed", "at": "2026-09-20",
             "why": "x"},
            {"edit_class": "distill/digest.md", "verdict": "harmed", "at": "2026-09-10",
             "why": "x"}]
    assert archive.retired(arch) == {}


def test_the_archive_veto_reaches_the_gate():
    """The two halves wired together: an archive verdict actually blocks a merge."""
    arch = [{"edit_class": "distill/digest.md", "verdict": "harmed", "at": "2026-09-20",
             "why": "w"},
            {"edit_class": "distill/digest.md", "verdict": "harmed", "at": "2026-09-10",
             "why": "w"}]
    assert not _gate(retired_classes=archive.retired(arch)).allowed
