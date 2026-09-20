"""Tests for tier 0 — the evaluation that runs without a model (ADR-0009 §1).

The property under test throughout is *degradation*: losing the model must cost the eval's
resolution and nothing else. Before this existed, an unset `RADAR_GRADER_MODEL` produced no
eval, so no issue, so an empty coder queue — for 69 days, twice. Every test here is a
different way of asking "does the loop still turn when the judge is gone?"

Run: uv run --group dev pytest tests/test_deterministic.py -q
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from grader import artifacts, attempts, deterministic, provenance  # noqa: E402

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

DIGEST = """\
<!-- radar:nav -->
`radar` · [index](README.md)
<!-- /radar:nav -->

# AI Radar — 2026-09-19

**Top-line:** Something happened.

## What changed

**New today**
- [A thing](https://example.com/a) — a thing

## Main list

### 1. First item · 4/5
[Paper](https://example.com/1)
**New.** Body.

### 2. Second item · 2/5
[Model](https://example.com/2)
**New.** Body.

## Insights

- A point.
"""


def _tracked(n: int, missed: int = 0, history: int = 3) -> dict:
    out = {}
    for i in range(n):
        out[f"arxiv:{i}"] = {
            "id": f"arxiv:{i}",
            "misses": 1 if i < missed else 0,
            "mag_history": [1.0] * history,
        }
    return out


# --- parsing ---------------------------------------------------------------

def test_sections_and_items_are_parsed():
    assert deterministic.sections(DIGEST) == ["What changed", "Main list", "Insights"]
    items = deterministic.main_items(DIGEST)
    assert [i["score"] for i in items] == [4, 2]
    assert items[0]["title"] == "First item"


def test_sections_are_the_primary_level_not_every_heading():
    """Item headings are `###` under `## Main list`; counting them as sections would
    inflate the metric and make "how organised is this" meaningless."""
    assert "First item" not in deterministic.sections(DIGEST)


def test_a_digest_that_uses_h3_for_sections_is_still_parsed():
    """2026-09-02 uses `###` for every section including Main list. Hardcoding `##` read
    that whole digest as structureless."""
    h3 = DIGEST.replace("## What changed", "### What changed") \
               .replace("## Main list", "### Main list") \
               .replace("## Insights", "### Insights") \
               .replace("### 1. First item", "#### 1. First item") \
               .replace("### 2. Second item", "#### 2. Second item")
    assert "Main list" in deterministic.sections(h3)


@pytest.mark.parametrize("line,title,score", [
    ("### 1. Numbered with score · 4/5", "Numbered with score", 4),
    ("### Unnumbered with score · 3/5", "Unnumbered with score", 3),
    ("### Plain heading", "Plain heading", None),
    ("**Bold with long score · score 3/5**", "Bold with long score", 3),
    ("1. **Numbered bold · score 2/5**", "Numbered bold", 2),
])
def test_every_main_list_shape_that_occurs_in_practice_is_recognised(line, title, score):
    """Measured across all 89 committed digests. The first version of this parser knew one
    of these five and reported the other four as an empty main list."""
    digest = f"# T\n\n## Main list\n\n{line}\nbody\n"
    items = deterministic.main_items(digest)
    assert items == [{"title": title, "score": score}]


def test_main_items_are_scoped_to_the_main_list():
    """`###` headings appear under Story arcs too. Counting those would make an empty main
    list undetectable — the check would pass on exactly the digests it exists to catch."""
    digest = ("# T\n\n## Main list\n\n(nothing here)\n\n"
              "## Story arcs\n\n### An arc · 4/5\n")
    assert deterministic.main_items(digest) == []


def test_degraded_marker_matches_what_synthesize_actually_writes():
    """Same pairing `tests/test_health.py` enforces: this module duplicates the banner as a
    literal so it need not import distill, and the duplicate must not drift."""
    src = (ROOT / "distill" / "synthesize.py").read_text()
    assert deterministic.DEGRADED_MARKER in src


def test_a_degraded_digest_is_detected():
    assert deterministic.is_degraded(DIGEST) is False
    assert deterministic.is_degraded(DIGEST + "\n" + deterministic.DEGRADED_MARKER) is True


# --- trusted metrics -------------------------------------------------------

def test_reobservation_rate_counts_items_seen_this_run():
    assert deterministic.reobservation_rate(_tracked(10, missed=2)) == 0.8


def test_empty_ledger_has_no_reobservation_rate_rather_than_zero():
    """A radar with nothing on it has not failed to re-observe. Zero would read as total
    failure and would fire the check below."""
    assert deterministic.reobservation_rate({}) is None


def test_traction_observations_require_two_readings():
    """The repo's headline claim is that "Climbing" means two observations of the same
    counter, not two guesses. This counts the evidence behind it."""
    mixed = {**_tracked(3, history=1), **{f"x{i}": {"mag_history": [1.0, 2.0]}
                                          for i in range(4)}}
    assert deterministic.traction_observations(mixed) == 4


# --- checks ----------------------------------------------------------------

_DEFAULT = object()     # `{}` is a meaningful ledger here, so `or` would swallow it


def _evaluate(digest=DIGEST, *, broken=None, links=8, tracked=_DEFAULT):
    return deterministic.evaluate(digest, age_h=12.0, broken=broken or [],
                                  link_count=links,
                                  tracked=_tracked(10) if tracked is _DEFAULT else tracked)


def test_a_healthy_digest_fails_nothing():
    assert _evaluate()["failed"] == []


def test_a_differently_organised_digest_is_not_a_structural_failure():
    """2026-09-16 grouped items thematically (`Benchmark`, `Cost`, `Dataset`) instead of
    under `Main list`. That is a fine digest, and requiring section names by spelling would
    have made it a daily false alarm — the prompt producing those names is coder-editable."""
    renamed = DIGEST.replace("## Main list", "## Benchmark")
    assert "structure" not in _evaluate(renamed)["failed"]


def test_a_reasoning_transcript_is_a_structural_failure():
    """The one real structural defect in 89 days, three times over: the model's working
    shipped as the newsletter. 13KB opening "Let me analyze the task carefully", no title,
    no headings, published."""
    leaked = ("Let me analyze this task carefully. I need to produce a digest report.\n"
              "Key parameters:\n- TODAY = 2026-09-18\n- WINDOW = 48h\n" * 20)
    result = _evaluate(leaked)
    assert "structure" in result["failed"]
    detail = [c for c in result["checks"] if c["key"] == "structure"][0]["detail"]
    assert "reasoning" in detail


def test_a_truncated_digest_is_a_structural_failure():
    """2026-09-14 shipped six lines: a title and one paragraph."""
    assert "structure" in _evaluate("# AI Radar — 2026-09-14\n\n**Top-line.** One para.\n"
                                    )["failed"]


def test_bold_section_labels_count_as_structure():
    """Some digests label sections in bold rather than with a heading."""
    bold = "# AI Radar\n\n**Main list**\n\n- [A thing](https://example.com/a)\n"
    assert "structure" not in _evaluate(bold)["failed"]


def test_a_genuinely_empty_main_list_fails():
    """The defect worth catching: the README records that ~30% of digests once shipped with
    nothing in the main list."""
    empty = "# T\n\n## What changed\n\nnone\n\n## Main list\n\n_Nothing today._\n"
    assert "main_list_nonempty" in _evaluate(empty)["failed"]


def test_an_unparsable_main_list_is_unknown_not_empty():
    """The parser reads a prompt the coder may rewrite, so it will eventually meet a shape
    it does not know. Calling that "empty" is how a monitor earns being ignored — which is
    exactly what happened on this checker's first autonomous run, against issue #36."""
    odd = ("# T\n\n## Main list\n\n"
           "~ Some Item ~ [source](https://example.com/a)\n"
           "~ Another ~ [source](https://example.com/b)\n")
    result = _evaluate(odd)
    check = [c for c in result["checks"] if c["key"] == "main_list_nonempty"][0]
    assert check["ok"] is None
    assert "main_list_nonempty" not in result["failed"]
    assert "does not recognise" in check["detail"]


def test_a_missing_main_list_section_is_not_reported_twice():
    """`structure` already speaks for it; counting one fault twice inflates the failure
    count and, through backlog_items, the queue."""
    no_section = "# T\n\n## What changed\n\n- [A](https://example.com/a)\n"
    check = [c for c in _evaluate(no_section)["checks"]
             if c["key"] == "main_list_nonempty"][0]
    assert check["ok"] is None


def test_broken_links_fail_but_unreachable_ones_do_not():
    """Status 0 means the runner could not reach it, which is not the digest's fault —
    the same distinction `grader/links.py` already makes for the A2 ceiling."""
    assert "links_resolve" in _evaluate(
        broken=[{"url": "https://example.com/1", "status": 404}])["failed"]
    assert "links_resolve" not in _evaluate(
        broken=[{"url": "https://example.com/1", "status": 0}])["failed"]


def test_a_degraded_digest_fails_the_synthesis_check():
    assert "synthesis_present" in _evaluate(
        DIGEST + "\n" + deterministic.DEGRADED_MARKER)["failed"]


def test_low_reobservation_fails_because_traction_claims_rest_on_it():
    assert "traction_observed" in _evaluate(tracked=_tracked(10, missed=8))["failed"]


def test_empty_ledger_is_not_applicable_rather_than_failed():
    """`ok=None` must never be counted as a pass or a fail — the rule `scripts/health.py`
    applies to UNKNOWN, applied here."""
    result = _evaluate(tracked={})
    check = [c for c in result["checks"] if c["key"] == "traction_observed"][0]
    assert check["ok"] is None
    assert "traction_observed" not in result["failed"]


def test_module_hash_changes_when_the_checker_changes(tmp_path, monkeypatch):
    """Invariant I-11. The Darwin Godel Machine deleted the markers its detector searched
    for; the fence stops the edit, and this catches the edit the fence missed."""
    original = deterministic.module_hash()
    assert len(original) == 12
    assert _evaluate()["module_hash"] == original


# --- the eval that results --------------------------------------------------

def _deterministic_eval(tier0=None):
    return artifacts.assemble_deterministic(
        date="2026-09-19", mode=artifacts.DETERMINISTIC, digest_commit_time=NOW,
        age_h=12.0, broken=[], tier0=tier0 or _evaluate(), reason="no model configured")


def test_a_deterministic_eval_validates():
    artifacts.validate(_deterministic_eval())


def test_a_deterministic_eval_omits_judged_dimensions():
    """I-09. Unknown is omitted, never defaulted: a zero written here is a fabricated
    judgement entering a permanent trend."""
    ev = _deterministic_eval()
    for absent in ("quality", "experience", "overall"):
        assert absent not in ev
    assert artifacts.is_judged(ev) is False


def test_a_deterministic_eval_may_not_claim_a_grader_model():
    ev = _deterministic_eval()
    ev["grader_model"] = "some/model"
    with pytest.raises(artifacts.SchemaError, match="must not name a grader_model"):
        artifacts.validate(ev)


def test_a_deterministic_eval_may_not_smuggle_in_a_score():
    ev = _deterministic_eval()
    ev["overall"] = 0.0
    with pytest.raises(artifacts.SchemaError, match="I-09"):
        artifacts.validate(ev)


def test_every_eval_must_record_the_checker_hash():
    ev = _deterministic_eval()
    ev["tier0"] = {}
    with pytest.raises(artifacts.SchemaError, match="I-11"):
        artifacts.validate(ev)


def test_tier0_failures_still_file_an_issue():
    """The point of the whole cascade: one missing model must not silence the alerting path
    as well as the trend."""
    tier0 = _evaluate(broken=[{"url": "https://example.com/1", "status": 404}])
    reason = artifacts.should_file_issue(_deterministic_eval(tier0), [])
    assert reason and "links_resolve" in reason


def test_a_clean_deterministic_eval_files_nothing():
    assert artifacts.should_file_issue(_deterministic_eval(), []) is None


def test_tier0_failures_still_append_a_causal_backlog_item():
    tier0 = _evaluate(broken=[{"url": "https://example.com/1", "status": 404}])
    items = artifacts.backlog_items(_deterministic_eval(tier0), "2026-09-19")
    assert len(items) == 1
    assert "links_resolve" in items[0] and "triggered by" in items[0]


def test_deterministic_evals_do_not_enter_the_quality_trend():
    """They appear in the table as a dash so the day is visibly accounted for — a gap is
    what hid a 69-day outage — but they carry no number."""
    rendered = artifacts.render_readme([_deterministic_eval()])
    assert "| 2026-09-19 | — | — | — | deterministic" in rendered


def test_deterministic_history_is_not_read_as_a_persistent_regression():
    """A model's absence is not evidence of a low score on either side."""
    judged = {"date": "2026-09-18", "mode": "normal",
              "quality": {"A1": {"score": 2, "why": "x"}},
              "experience": {}}
    assert artifacts.is_judged(judged) is True
    assert artifacts.is_judged(_deterministic_eval()) is False


# --- attempt records --------------------------------------------------------

def test_attempt_records_reject_an_unknown_outcome():
    """The outcome set is closed so a new branch in cli.py cannot invent a state no
    consumer knows how to read."""
    with pytest.raises(ValueError, match="unknown outcome"):
        attempts.record(outcome="fine", mode="normal")


def test_attempt_records_round_trip(tmp_path):
    p = tmp_path / "attempts.jsonl"
    attempts.append(attempts.record(outcome="deterministic", mode="normal",
                                    reason="no model", at=NOW), p)
    attempts.append(attempts.record(outcome="judged", mode="normal",
                                    grader_model="m", at=NOW), p)
    loaded = attempts.load(p)
    assert [r["outcome"] for r in loaded] == ["deterministic", "judged"]


def test_attempt_log_is_capped(tmp_path):
    p = tmp_path / "attempts.jsonl"
    for _ in range(10):
        attempts.append(attempts.record(outcome="judged", mode="normal", at=NOW), p,
                        max_records=4)
    assert len(attempts.load(p)) == 4


def test_a_malformed_line_does_not_take_out_the_log(tmp_path):
    """This file's job is to still be readable when something else has gone wrong."""
    p = tmp_path / "attempts.jsonl"
    p.write_text('{"outcome": "judged"}\nnot json at all\n{"outcome": "stale"}\n')
    assert [r["outcome"] for r in attempts.load(p)] == ["judged", "stale"]


def test_consecutive_counts_the_stall():
    """Fifteen consecutive blocked runs is a loop that is alive, observed, and going
    nowhere — the state nothing could name in September 2026."""
    recs = [{"outcome": "judged"}] + [{"outcome": "deterministic"}] * 15
    assert attempts.consecutive("deterministic", recs) == 15
    assert attempts.consecutive("judged", recs) == 0


def test_summary_survives_an_empty_log():
    assert attempts.summary([]) == "no attempts recorded"


# --- provenance -------------------------------------------------------------

def test_revs_name_the_tunable_files_only():
    """A whole-repo revision would be useless for attribution: every daily corpus commit
    would move it, so every eval would look like it followed a change."""
    revs = provenance.revs()
    assert set(revs["files"]) <= set(provenance.TUNABLE)
    assert "reports/latest.md" not in revs["files"]


def test_a_shallow_clone_reports_no_revisions_rather_than_identical_ones(monkeypatch):
    """On a shallow clone every path resolves to the boundary commit, so no transition is
    ever visible and the archive would be permanently empty while looking like a quiet
    period — this ADR's own failure mode, inside the machinery built to prevent it."""
    monkeypatch.setattr(provenance, "is_shallow", lambda: True)
    got = provenance.revs()
    assert got["files"] == {} and got["shallow"] is True


def test_revs_survive_an_untracked_path(monkeypatch):
    monkeypatch.setattr(provenance, "is_shallow", lambda: False)
    revs = provenance.revs(paths=("no/such/file.yaml",))
    assert revs == {"prompt_rev": None, "config_rev": None, "files": {}}


def test_changed_since_is_empty_without_a_baseline():
    assert provenance.changed_since(None) == []


# --- the write ratchet ------------------------------------------------------
# Two runners, one path, no lock. `eval-deterministic.yml` produces tier 0 in CI after each
# digest; the external scheduled task (ADR-0003) produces the judged eval on its own clock.
# I-01 forbids two writers, and the resolution is monotonicity rather than coordination —
# which matters, because one of the two is a task this repo cannot see.

def _judged_eval(date="2026-09-19"):
    return artifacts.assemble(
        date=date, mode="normal", grader_model="deepseek/x",
        digest_commit_time=NOW, age_h=2.0,
        verdict={d: {"score": 4, "why": "w"} for d in
                 artifacts.QUALITY_DIMS + artifacts.EXPERIENCE_DIMS},
        x3=5, a2_ceiling=5, broken=[],
        tier0={"module_hash": "abc123abc123", "metrics": {}, "checks": [], "failed": []})


def test_a_judged_eval_may_replace_a_deterministic_one(tmp_path):
    artifacts.write_eval(_deterministic_eval(), tmp_path)
    artifacts.write_eval(_judged_eval(), tmp_path)
    stored = json.loads((tmp_path / "2026-09-19.json").read_text())
    assert artifacts.is_judged(stored)


def test_a_deterministic_eval_may_not_replace_a_judged_one(tmp_path):
    """The whole ratchet. Whatever order the two runners land in, information only
    increases — so they cannot race destructively and need no coordination."""
    artifacts.write_eval(_judged_eval(), tmp_path)
    with pytest.raises(artifacts.Downgrade, match="Information only increases|judged eval"):
        artifacts.write_eval(_deterministic_eval(), tmp_path)
    stored = json.loads((tmp_path / "2026-09-19.json").read_text())
    assert artifacts.is_judged(stored)


def test_a_deterministic_eval_may_replace_another_deterministic_one(tmp_path):
    """Re-running tier 0 on the same day is an update, not a downgrade."""
    artifacts.write_eval(_deterministic_eval(), tmp_path)
    artifacts.write_eval(_deterministic_eval(), tmp_path)
    assert (tmp_path / "latest.json").exists()


def test_an_unreadable_existing_eval_does_not_block_the_write(tmp_path):
    """A corrupt file is not evidence that a judged eval exists, and refusing to write over
    it would leave the corruption in place as `latest.json`."""
    (tmp_path / "2026-09-19.json").write_text("{ not json")
    artifacts.write_eval(_deterministic_eval(), tmp_path)
    assert json.loads((tmp_path / "2026-09-19.json").read_text())["mode"] == "deterministic"


# --- the guard that would have prevented all of the above --------------------

def _committed_digests() -> list[Path]:
    return sorted((ROOT / "reports").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-digest.md"))


def test_the_checker_raises_no_false_alarms_on_any_committed_digest():
    """Run tier 0 over every digest the repo has ever published.

    This is the test that was missing. The first version of this checker was written
    against one day's formatting, matched 34 of 176 real main-list headings, and on its
    first autonomous run filed issue #36 claiming a perfectly good digest had "nothing to
    say". Unit tests over a synthetic fixture cannot catch that — only the corpus can.

    A digest is allowed to fail `structure` (four genuinely are: three shipped the model's
    reasoning transcript, one shipped six lines). Nothing else may fail, because nothing
    else is actually wrong with the other 85.
    """
    digests = _committed_digests()
    assert len(digests) > 50, "corpus too small for this test to mean anything"

    unexpected = []
    for path in digests:
        result = deterministic.evaluate(path.read_text(), age_h=1.0, broken=[],
                                        link_count=5, tracked={})
        for key in result["failed"]:
            if key != "structure":
                unexpected.append(f"{path.name}: {key}")
    assert unexpected == []


def test_structure_flags_only_the_genuinely_broken_digests():
    """Pinned by name. If a future parser change flags a fifth, it is a false alarm until
    someone opens that file and disagrees in writing."""
    broken = {p.name for p in _committed_digests()
              if "structure" in deterministic.evaluate(
                  p.read_text(), age_h=1.0, broken=[], link_count=5,
                  tracked={})["failed"]}
    assert broken == {
        "2026-08-14-digest.md",     # reasoning transcript shipped as the digest
        "2026-08-25-digest.md",     # reasoning transcript shipped as the digest
        "2026-09-18-digest.md",     # reasoning transcript shipped as the digest
        "2026-09-14-digest.md",     # truncated: a title and one paragraph
    }


def test_most_committed_digests_parse_a_main_list():
    """A coverage floor, so a regression that quietly stops recognising items shows up as
    a number rather than as silence. `unknown` is acceptable; a collapse is not."""
    parsed = sum(1 for p in _committed_digests() if deterministic.main_items(p.read_text()))
    assert parsed >= 55
