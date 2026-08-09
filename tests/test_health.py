"""Tests for the health reporter.

The classification rules are the part worth testing: `health.py` is the single
definition of "stale" shared by `health.yml`, `watchdog.yml`, and the status
page, so a wrong threshold here is wrong in three places at once. The IO edges
(git, the Actions API) are exercised only for their failure behaviour, because
the failure behaviour is load-bearing — a monitor that reports DOWN when it
merely failed to look is a monitor you learn to ignore.

Run: uv run --with pytest pytest tests/ -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from health import (  # noqa: E402
    DOWN, OK, UNKNOWN, WARN,
    classify_age, classify_workflow, fail_streak, git_age_hours,
    humanise_age, reason_lines, render_markdown, worst,
)


# --- age classification ----------------------------------------------------

@pytest.mark.parametrize("age_h,expected", [
    (0, OK),
    (12, OK),       # inside half the threshold
    (24, OK),       # exactly half is still fine
    (25, WARN),     # past one cadence: the next run decides
    (48, WARN),     # exactly at the threshold is not yet a breach
    (49, DOWN),
    (626, DOWN),    # the real 2026-07 eval outage
])
def test_classify_age(age_h, expected):
    assert classify_age(age_h, 48) == expected


def test_missing_artifact_skips_warn():
    """Never produced is not the same as old. One slow run explains a stale
    artifact; it cannot explain a missing one."""
    assert classify_age(None, 48) == DOWN


# --- failure streaks -------------------------------------------------------

def test_streak_counts_only_leading_failures():
    assert fail_streak(["failure", "failure", "success", "failure"]) == 2


def test_streak_zero_when_latest_succeeded():
    assert fail_streak(["success", "failure", "failure"]) == 0


def test_streak_steps_over_inconclusive_runs():
    """A cancelled or in-progress run says nothing about health, so it must
    neither confirm nor break a streak."""
    assert fail_streak(["cancelled", "failure", None, "skipped", "failure"]) == 2


def test_streak_on_empty_history():
    assert fail_streak([]) == 0


# --- workflow classification ----------------------------------------------

def test_single_failure_of_fatal_workflow_is_warn_not_down():
    """One red run is a blip. Escalating on it is how a monitor trains you to
    ignore it."""
    status, streak = classify_workflow(["failure", "success"], fatal=True)
    assert (status, streak) == (WARN, 1)


def test_repeated_failure_of_fatal_workflow_is_down():
    status, streak = classify_workflow(["failure"] * 10, fatal=True)
    assert (status, streak) == (DOWN, 10)


def test_non_fatal_workflow_never_escalates_to_down():
    """The watchdog is *expected* to be red whenever something else is stale.
    If its redness could drive the overall status DOWN, the two would feed each
    other and the report would say nothing about the underlying cause."""
    status, _ = classify_workflow(["failure"] * 10, fatal=False)
    assert status == WARN


def test_green_workflow_is_ok():
    assert classify_workflow(["success", "success"], fatal=True) == (OK, 0)


# --- aggregation -----------------------------------------------------------

def test_worst_picks_the_most_severe():
    assert worst([OK, WARN, DOWN]) == DOWN
    assert worst([OK, WARN]) == WARN
    assert worst([OK, OK]) == OK


def test_worst_of_nothing_is_ok():
    assert worst([]) == OK


# --- IO failure behaviour --------------------------------------------------

def test_git_age_of_untracked_path_is_none(tmp_path, monkeypatch):
    """A path git knows nothing about must read as None (-> DOWN via
    classify_age), never as age 0 (-> OK). Reading "no commits" as "just
    committed" is the exact bug that would make a dead pipeline look green."""
    assert git_age_hours("no/such/path/anywhere.json") is None


def test_fetch_runs_returns_empty_on_network_error(monkeypatch):
    """The API being unreachable is not evidence the pipeline is broken."""
    import health

    def boom(*a, **kw):
        raise OSError("no network")

    monkeypatch.setattr(health.urllib.request, "urlopen", boom)
    assert health.fetch_runs("distill.yml") == []


def test_unobserved_workflow_is_excluded_from_overall_status():
    """No runs is unknown, not healthy — and unknown must not be laundered into
    the overall reading in either direction."""
    health = {
        "signals": [{"key": "digest", "label": "Daily digest", "status": OK,
                     "detail": "fine", "url": "#", "age_h": 1, "threshold_h": 48}],
        "workflows": [{"key": "distill", "label": "Distill digest", "status": UNKNOWN,
                       "conclusion": None, "fail_streak": 0, "last_run_at": None,
                       "url": "#", "observed": False}],
        "generated": "2026-08-09T16:00:00+00:00",
    }
    assert reason_lines(health) == []
    assert "unknown" in render_markdown(health)


def test_unreadable_api_does_not_serialise_as_ok(monkeypatch):
    """End-to-end guard on the flaw above: when the Actions API cannot be read,
    the emitted JSON must say `unknown`, not `ok`. A status page rendering a
    hardcoded green for a workflow nobody looked at is worse than no page."""
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    built = h.build_health()
    assert {w["status"] for w in built["workflows"]} == {UNKNOWN}
    assert all(w["observed"] is False for w in built["workflows"])


def test_unknown_workflow_cannot_raise_overall_status(monkeypatch):
    """A blind spot must not escalate either. With every artifact fresh and the
    API unreadable, the overall reading is OK — not WARN, not DOWN."""
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    monkeypatch.setattr(h, "git_age_hours", lambda *a, **kw: 1.0)
    assert h.build_health()["status"] == OK


# --- reason lines (the watchdog's input) -----------------------------------

def _health(signal_status: str, wf_status: str = OK, streak: int = 0) -> dict:
    return {
        "generated": "2026-08-09T16:00:00+00:00",
        "signals": [{"key": "evals", "label": "Eval loop", "status": signal_status,
                     "detail": "grader last committed 27d ago", "url": "#",
                     "age_h": 626, "threshold_h": 48}],
        "workflows": [{"key": "distill", "label": "Distill digest", "status": wf_status,
                       "conclusion": "failure" if streak else "success",
                       "fail_streak": streak, "last_run_at": "2026-08-09T11:22:00Z",
                       "url": "#", "observed": True}],
    }


def test_reasons_empty_when_everything_is_ok():
    assert reason_lines(_health(OK)) == []


def test_reasons_report_each_fault_separately():
    """The 2026-08 outage had two independent faults at once (stale evals AND a
    failing distill). A reason list that collapses them to one hides the second."""
    lines = reason_lines(_health(DOWN, DOWN, streak=10))
    assert len(lines) == 2
    assert any(line.startswith("down\tEval loop:") for line in lines)
    assert any("10 consecutive failures" in line for line in lines)


def test_reasons_are_worst_first():
    lines = reason_lines(_health(WARN, DOWN, streak=10))
    assert lines[0].startswith("down")
    assert lines[1].startswith("warn")


def test_reason_lines_are_tab_delimited():
    """watchdog.yml splits on the tab with `cut -f2-`. If this format changes,
    the alert text silently becomes 'down' with no detail."""
    line = reason_lines(_health(DOWN))[0]
    assert line.count("\t") == 1
    assert line.split("\t")[0] == DOWN


# --- presentation ----------------------------------------------------------

def test_humanise_age_rolls_up_to_days():
    assert humanise_age(None) == "never"
    assert humanise_age(0.5) == "<1h ago"
    assert humanise_age(30) == "30h ago"
    assert humanise_age(626) == "26d ago"


def test_render_markdown_includes_every_row():
    md = render_markdown(_health(DOWN, DOWN, streak=10))
    assert "Eval loop" in md and "Distill digest" in md
    assert "🔴" in md
