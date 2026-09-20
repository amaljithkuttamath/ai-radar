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

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from health import (  # noqa: E402
    DOWN, OK, UNKNOWN, WARN,
    classify_age, classify_loop, classify_workflow, fail_streak, git_age_hours,
    humanise_age, humanise_duration, reason_lines, render_markdown, worst,
)
# Bound before the autouse fixture can replace the module attribute, so the two tests
# that exercise the real Issues read get the real function rather than the stub.
from health import (  # noqa: E402
    fetch_open_alarms as real_fetch_open_alarms,
    latest_eval_is_unjudged as real_latest_eval_is_unjudged,
)

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _no_network_and_full_history(monkeypatch):
    """`build_health` has two IO edges beyond the Actions API: the Issues read behind
    the loop signal, and the shallow-clone probe. Both are neutralised by default so
    every pre-existing test keeps measuring what it was written to measure — and so
    the suite's no-network rule survives the new signal. Tests that care about either
    edge patch it back explicitly."""
    import health as h

    monkeypatch.setattr(h, "fetch_open_alarms", lambda *a, **kw: [])
    monkeypatch.setattr(h, "is_shallow_clone", lambda: False)
    # Reads the repo's real `evals/latest.json`, so without this the suite's result
    # depends on whether a grader run happened to leave a deterministic eval there —
    # which is exactly what it did, once. Tests must not read live pipeline state.
    monkeypatch.setattr(h, "latest_eval_is_unjudged", lambda *a, **kw: False)


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


# --- degraded-synthesis signal --------------------------------------------

def test_degraded_marker_matches_the_string_synthesize_actually_writes():
    """health.py duplicates the marker as a literal so it can stay stdlib-only. That is a
    fine trade only while something checks the copies agree — otherwise the status page
    silently reports every degraded digest as fully synthesized."""
    import health as h
    from distill import synthesize

    banner = synthesize.degraded_banner("anthropic", "HTTP 410 Gone")
    assert h.DEGRADED_MARKER in banner


def test_degraded_digest_is_detected(tmp_path):
    import health as h
    from distill import synthesize

    d = tmp_path / "latest.md"
    d.write_text(synthesize.degraded_banner("anthropic", "HTTP 410 Gone") + "# AI Radar\n")
    assert h.digest_is_degraded(d) is True


def test_synthesized_digest_is_not_flagged(tmp_path):
    import health as h

    d = tmp_path / "latest.md"
    d.write_text("# AI Radar — 2026-08-09\n\n**Top-line** — a real synthesized read.\n")
    assert h.digest_is_degraded(d) is False


def test_missing_digest_is_unknown_not_healthy(tmp_path):
    import health as h
    assert h.digest_is_degraded(tmp_path / "nope.md") is None


def test_degraded_digest_warns_without_escalating(monkeypatch):
    """A degraded digest is still a digest. WARN surfaces it; DOWN would page someone over
    a budget decision."""
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    monkeypatch.setattr(h, "git_age_hours", lambda *a, **kw: 1.0)
    monkeypatch.setattr(h, "digest_is_degraded", lambda *a, **kw: True)

    built = h.build_health()
    synth = [s for s in built["signals"] if s["key"] == "synthesis"][0]
    assert synth["status"] == WARN
    assert built["status"] == WARN


# --- the self-healing loop signal ------------------------------------------
# Detecting a fault and closing one fail independently. Between 2026-08-10 and
# 2026-09-19 detection worked every single day — the eval signal read DOWN, the
# watchdog filed issue #34, the watchdog went red fifteen days running — and the
# alarm was never answered. These tests pin the signal that would have said so.

def _alarm(number: int, hours_ago: float) -> dict:
    return {"number": number, "opened": NOW - timedelta(hours=hours_ago)}


def test_no_open_alarms_is_ok():
    status, detail = classify_loop([], NOW)
    assert status == OK
    assert detail == "no unanswered alarms"


def test_fresh_alarm_warns_rather_than_escalating():
    """A filed alarm is the loop working. It only becomes a fault once it outlives
    the coder's own cadence."""
    status, detail = classify_loop([_alarm(34, 5)], NOW)
    assert status == WARN
    assert "#34" in detail


@pytest.mark.parametrize("hours,expected", [
    (71, WARN),      # inside the 72h file cooldown: a fix may still be in flight
    (72, WARN),      # exactly at the threshold is not yet a breach
    (73, DOWN),
    (24 * 40, DOWN),  # issue #34, the real one
])
def test_alarm_becomes_down_once_it_outlives_the_cooldown(hours, expected):
    status, _ = classify_loop([_alarm(34, hours)], NOW)
    assert status == expected


def test_status_is_driven_by_the_oldest_alarm_not_the_count():
    """Three alarms filed this morning is a busy day. One filed six weeks ago is a
    loop that stopped turning, and only the second means the repo is not healing."""
    busy = classify_loop([_alarm(1, 2), _alarm(2, 3), _alarm(3, 4)], NOW)
    stalled = classify_loop([_alarm(34, 24 * 40)], NOW)
    assert busy[0] == WARN
    assert stalled[0] == DOWN


def test_detail_names_the_oldest_alarm_and_the_backlog_size():
    _, detail = classify_loop([_alarm(34, 24 * 40), _alarm(50, 1)], NOW)
    assert "#34" in detail and "40d" in detail and "(2 open)" in detail


def test_unreadable_issues_api_is_unknown_never_ok():
    """`None` and `[]` mean opposite things: "we could not look" must not render as
    "nothing is outstanding". This is the same rule the workflow signals follow."""
    status, detail = classify_loop(None, NOW)
    assert status == UNKNOWN
    assert status != OK
    assert "could not read" in detail


def test_fetch_open_alarms_returns_none_on_network_error(monkeypatch):
    import health as h

    def boom(*a, **kw):
        raise OSError("no network")

    monkeypatch.setattr(h.urllib.request, "urlopen", boom)
    assert real_fetch_open_alarms() is None


class _FakeResponse:
    """Minimal stand-in for what `urlopen` yields as a context manager."""

    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_pull_requests_are_not_counted_as_unanswered_alarms(monkeypatch):
    """The Issues API returns PRs as issues. A PR is an *answer* to an alarm, so
    counting one would make the loop look most broken exactly when it was working.
    Both rows below are real: issue #34 and the draft PR #35 opened in reply to it."""
    import health as h

    payload = [
        {"number": 34, "created_at": "2026-08-10T15:56:19Z"},
        {"number": 35, "created_at": "2026-08-11T03:42:15Z", "pull_request": {"url": "#"}},
    ]
    monkeypatch.setattr(h.urllib.request, "urlopen",
                        lambda *a, **kw: _FakeResponse(payload))
    alarms = real_fetch_open_alarms()
    assert [a["number"] for a in alarms] == [34]


def test_undateable_alarm_does_not_blind_the_whole_read(monkeypatch):
    """Dropping every alarm over one malformed row would turn a parse bug into a
    blind spot, which is the failure this signal exists to prevent."""
    import health as h

    payload = [
        {"number": 34, "created_at": "not-a-date"},
        {"number": 36, "created_at": "2026-09-01T00:00:00Z"},
    ]
    monkeypatch.setattr(h.urllib.request, "urlopen",
                        lambda *a, **kw: _FakeResponse(payload))
    assert [a["number"] for a in real_fetch_open_alarms()] == [36]


def test_loop_signal_is_reported_and_escalates(monkeypatch):
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    monkeypatch.setattr(h, "git_age_hours", lambda *a, **kw: 1.0)
    monkeypatch.setattr(h, "fetch_open_alarms",
                        lambda *a, **kw: [{"number": 34,
                                           "opened": datetime.now(timezone.utc)
                                           - timedelta(days=40)}])
    built = h.build_health()
    loop = [s for s in built["signals"] if s["key"] == "loop"][0]
    assert loop["status"] == DOWN
    assert loop["open_alarms"] == 1
    assert built["status"] == DOWN
    # and it reaches the watchdog, which is what makes it act rather than merely render
    assert any("Self-healing loop" in line for line in reason_lines(built))


# --- measured-wrong is worse than not measured -----------------------------

def test_shallow_checkout_reports_unknown_not_a_wrong_age(monkeypatch):
    """On a shallow clone every artifact older than the truncation point reports the
    boundary commit's age, so a 69-day-dead stage reads as fresh. `fetch-depth: 0` is
    documented in both workflows and was enforced by nothing until this check."""
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    monkeypatch.setattr(h, "is_shallow_clone", lambda: True)
    monkeypatch.setattr(h, "git_age_hours", lambda *a, **kw: 1.0)   # a lie the clone tells

    built = h.build_health()
    ages = {s["key"]: s for s in built["signals"] if s["key"] in ("digest", "evals")}
    assert {s["status"] for s in ages.values()} == {UNKNOWN}
    # the wrong number must not survive into the artifact either
    assert all(s["age_h"] is None for s in ages.values())
    assert all("fetch-depth" in s["detail"] for s in ages.values())


def test_unknown_signals_do_not_fire_the_watchdog(monkeypatch):
    """A watchdog that fires on its own blindness is a watchdog you learn to ignore.
    Nothing is lost: every artifact that can read UNKNOWN is also measured from disk."""
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    monkeypatch.setattr(h, "is_shallow_clone", lambda: True)
    monkeypatch.setattr(h, "fetch_open_alarms", lambda *a, **kw: None)

    built = h.build_health()
    assert reason_lines(built) == []


def test_unknown_signal_renders_without_crashing_the_report():
    """UNKNOWN reaching the renderer must produce a row, not a KeyError that takes out
    the whole report over a blind spot in one line."""
    health = {
        "generated": "2026-09-20T12:00:00+00:00",
        "signals": [{"key": "loop", "label": "Self-healing loop", "status": UNKNOWN,
                     "detail": "could not read open alarms", "url": "#",
                     "age_h": None, "threshold_h": 72}],
        "workflows": [],
    }
    assert "Self-healing loop" in render_markdown(health)


def test_humanise_duration_has_no_ago_suffix():
    assert humanise_duration(40 * 24) == "40d"
    assert humanise_age(40 * 24) == "40d ago"


# --- the eval loop's two halves fail independently ---------------------------
# Since ADR-0009 a tier-0 eval is committed after every distill, so freshness alone can no
# longer tell "the grader ran" from "a model judged it". Reporting the first as the second
# would put a green light on the exact outage this file exists to catch.

def test_a_deterministic_latest_eval_is_detected(tmp_path):
    import health as h
    p = tmp_path / "latest.json"
    p.write_text('{"mode": "deterministic", "date": "2026-09-19"}')
    assert real_latest_eval_is_unjudged(p) is True


def test_a_judged_latest_eval_is_not_flagged(tmp_path):
    import health as h
    p = tmp_path / "latest.json"
    p.write_text('{"mode": "normal", "overall": 4.0}')
    assert real_latest_eval_is_unjudged(p) is False


def test_a_missing_eval_is_the_freshness_signals_finding_not_this_one(tmp_path):
    """Reporting it here as well would double-count one fault."""
    import health as h
    assert real_latest_eval_is_unjudged(tmp_path / "nope.json") is False
    assert real_latest_eval_is_unjudged(tmp_path) is False


def test_the_mode_string_matches_what_the_grader_actually_writes():
    """Duplicated rather than imported, so health.py stays stdlib-only. The duplicate must
    not drift."""
    from grader import artifacts
    assert artifacts.DETERMINISTIC == "deterministic"


def test_a_fresh_but_unjudged_eval_warns_instead_of_reading_green(monkeypatch):
    """The whole point. A punctual tier-0 eval must not report the eval loop healthy while
    no model has judged anything for months."""
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    monkeypatch.setattr(h, "git_age_hours", lambda *a, **kw: 1.0)
    monkeypatch.setattr(h, "latest_eval_is_unjudged", lambda *a, **kw: True)

    built = h.build_health()
    evals = [s for s in built["signals"] if s["key"] == "evals"][0]
    assert evals["status"] == WARN
    assert "no model judgement" in evals["detail"]


def test_a_fresh_judged_eval_still_reads_green(monkeypatch):
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    monkeypatch.setattr(h, "git_age_hours", lambda *a, **kw: 1.0)
    monkeypatch.setattr(h, "latest_eval_is_unjudged", lambda *a, **kw: False)

    evals = [s for s in h.build_health()["signals"] if s["key"] == "evals"][0]
    assert evals["status"] == OK


def test_a_stale_unjudged_eval_stays_down_rather_than_softening_to_warn(monkeypatch):
    """The unjudged rule may only ever lower a reading from OK. A stale eval is DOWN
    regardless of which tier produced it."""
    import health as h

    monkeypatch.setattr(h, "fetch_runs", lambda *a, **kw: [])
    monkeypatch.setattr(h, "git_age_hours", lambda *a, **kw: 5000.0)
    monkeypatch.setattr(h, "latest_eval_is_unjudged", lambda *a, **kw: True)

    evals = [s for s in h.build_health()["signals"] if s["key"] == "evals"][0]
    assert evals["status"] == DOWN


# --- the loop signal must not gate its own resolution ------------------------

def test_the_loop_signal_is_excluded_from_escalation_by_default():
    """Otherwise it deadlocks: the signal reads `down` because an alarm is open, which
    keeps the watchdog red, which stops the close step running, which keeps it `down`.
    Filing would also mean opening an issue about an unanswered issue."""
    import health as h
    health = {
        "generated": "2026-09-20T12:00:00+00:00",
        "signals": [
            {"key": "loop", "label": "Self-healing loop", "status": DOWN,
             "detail": "alarm #34 unanswered for 40d", "url": "#",
             "age_h": 981.0, "threshold_h": 72},
            {"key": "evals", "label": "Eval loop", "status": OK, "detail": "fresh",
             "url": "#", "age_h": 1, "threshold_h": 48},
        ],
        "workflows": [],
    }
    assert reason_lines(health, exclude=h.ESCALATION_EXCLUDED) == []
    # ...but it is still reportable, which is what keeps the run red and the page honest
    assert any("Self-healing loop" in line for line in reason_lines(health))


def test_the_loop_signal_still_renders_on_the_page():
    """Excluding it from escalation must not hide it. The status page and README read the
    signals directly, so the exclusion is scoped to the watchdog's decision alone."""
    health = {
        "generated": "2026-09-20T12:00:00+00:00",
        "signals": [{"key": "loop", "label": "Self-healing loop", "status": DOWN,
                     "detail": "alarm #34 unanswered for 40d", "url": "#",
                     "age_h": 981.0, "threshold_h": 72}],
        "workflows": [],
    }
    assert "Self-healing loop" in render_markdown(health)


def test_excluding_one_signal_does_not_hide_the_others():
    import health as h
    health = {
        "generated": "2026-09-20T12:00:00+00:00",
        "signals": [
            {"key": "loop", "label": "Self-healing loop", "status": DOWN,
             "detail": "x", "url": "#", "age_h": 1, "threshold_h": 72},
            {"key": "evals", "label": "Eval loop", "status": DOWN,
             "detail": "grader last committed 68d ago", "url": "#",
             "age_h": 1600, "threshold_h": 48},
        ],
        "workflows": [],
    }
    lines = reason_lines(health, exclude=h.ESCALATION_EXCLUDED)
    assert len(lines) == 1 and "Eval loop" in lines[0]
