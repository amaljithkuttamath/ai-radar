"""The eval loop.

Weighted toward the parts that decide a number without a model: freshness anchors, the A2
link ceiling, the separation fence, aggregate arithmetic, and schema validation. Those are
what make a score falsifiable — a judge's read of "signal density" is an opinion, but the
digest's age and a 404 are facts, and the grader's credibility rests on it getting the
facts right and never letting the opinion overwrite them.

Run: uv run --group dev pytest tests/ -q
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from grader import artifacts, freshness, judge, links
import llm
from grader.separation import SeparationViolation, assert_separated, family, synthesis_model

UTC = timezone.utc


# --- freshness -------------------------------------------------------------

@pytest.mark.parametrize("age_h,expected", [
    (0.1, 5), (5.9, 5), (6.0, 4), (11.9, 4), (12.0, 3),
    (23.9, 3), (24.0, 2), (36.0, 2), (36.1, 1), (700, 1),
])
def test_x3_anchors(age_h, expected):
    assert freshness.x3_score(age_h) == expected


def test_exactly_36h_is_fresh_not_stale():
    """grader.md lists this under 'Never escalate on'. An earlier implementation treated
    the boundary as stale and produced a daily false alarm."""
    assert freshness.is_stale(36.0) is False
    assert freshness.is_stale(36.01) is True


def test_h1_date_anchors_at_noon_not_midnight():
    """A digest published 13:00 UTC is not 13h old at midnight of the same day. Anchoring
    at midnight silently inflates X3."""
    got = freshness.h1_date("# AI Radar — 2026-08-09\n\nbody")
    assert got == datetime(2026, 8, 9, 12, tzinfo=UTC)


def test_h1_date_ignores_the_nav_block():
    """The nav link at the top of latest.md points at the PREVIOUS digest and is always
    the wrong date. grader.md says never to parse it; the regex anchors on the heading."""
    body = ("<!-- radar:nav -->\n"
            "`radar`  ·  [← 2026-07-29](2026-07-29-digest.md)  ·  [index](README.md)\n"
            "<!-- /radar:nav -->\n\n"
            "# AI Radar — 2026-07-30\n\nbody")
    assert freshness.h1_date(body).strftime("%Y-%m-%d") == "2026-07-30"


def test_unparsable_body_with_no_git_time_escalates():
    with pytest.raises(freshness.Escalate):
        freshness.resolve("no heading here", path="nope/missing.md")


@pytest.mark.parametrize("age_h", [-13.0, 73.0, 5000.0])
def test_insane_ages_escalate(age_h):
    """Beyond the band the number is not believable — clock skew, a parser bug, or a
    pipeline down for days. Scoring it would put fiction in the trend."""
    with pytest.raises(freshness.Escalate):
        freshness.check_sane(age_h)


def test_sane_boundaries_are_inclusive():
    freshness.check_sane(-12.0)
    freshness.check_sane(72.0)


# --- links -----------------------------------------------------------------

def test_extract_finds_markdown_links_only():
    body = ("[A](https://example.com/a) and bare https://example.com/bare and "
            "[B](https://example.com/b)")
    assert links.extract(body) == ["https://example.com/a", "https://example.com/b"]


def test_extract_dedupes_preserving_order():
    body = "[A](https://x.test/1) [again](https://x.test/1) [B](https://x.test/2)"
    assert links.extract(body) == ["https://x.test/1", "https://x.test/2"]


def test_extract_ignores_relative_nav_links():
    assert links.extract("[← 2026-07-29](2026-07-29-digest.md)") == []


def test_a2_ceiling_caps_on_a_real_404():
    assert links.a2_ceiling([{"url": "https://x.test", "status": 404}]) == 2


def test_a2_ceiling_ignores_unreachable_links():
    """status 0 means the runner could not get out — a proxy, a policy, a local outage.
    Capping on it would punish the digest for the grader's own connectivity and inject
    noise straight into the trend."""
    assert links.a2_ceiling([{"url": "https://x.test", "status": 0}]) == 5


def test_a2_ceiling_clean_when_nothing_broken():
    assert links.a2_ceiling([]) == 5


# --- the separation fence --------------------------------------------------

@pytest.mark.parametrize("model,expected", [
    ("claude-opus-4-8", "anthropic"),
    ("anthropic/claude-sonnet-5", "anthropic"),
    ("openai/gpt-4.1", "openai"),
    ("gpt-4.1-mini", "openai"),
    ("gemini-2.5-pro", "google"),
    ("llama-3.1-70b", "meta"),
    ("qwen3:4b", "alibaba"),
    ("sonar-pro", "perplexity"),
])
def test_family_detection(model, expected):
    assert family(model) == expected


def test_unknown_model_has_no_family():
    assert family("some-new-model-9000") is None


def test_same_family_is_refused():
    """The rule the whole module exists for: a model grading its own family self-enhances
    by +10-25%, and the green scores that result are indistinguishable from real quality."""
    env = {"RADAR_MODEL_BACKEND": "anthropic", "ANTHROPIC_API_KEY": "sk-x"}
    with pytest.raises(SeparationViolation, match="anthropic"):
        assert_separated("claude-opus-4-8", env)


def test_different_family_passes():
    env = {"RADAR_MODEL_BACKEND": "anthropic", "ANTHROPIC_API_KEY": "sk-x"}
    assert assert_separated("openai/gpt-4.1", env) == "openai"


def test_unrecognised_grader_model_is_refused_not_assumed_safe():
    """A fence that opens on the unfamiliar is not a fence. A new provider appearing is
    precisely when a stale allowlist would wave a violation through."""
    with pytest.raises(SeparationViolation, match="unrecognised"):
        assert_separated("brand-new-model-x", {"RADAR_MODEL_BACKEND": "template"})


def test_template_pipeline_has_nothing_to_be_separate_from():
    """With no synthesis call there is no authorial voice for a judge to flatter, so any
    recognised grader model is fine."""
    assert assert_separated("claude-opus-4-8", {"RADAR_MODEL_BACKEND": "template"}) == "anthropic"


@pytest.mark.parametrize("env,expected", [
    ({"RADAR_MODEL_BACKEND": "auto", "ANTHROPIC_API_KEY": "k"}, "claude-opus-4-8"),
    ({"RADAR_MODEL_BACKEND": "auto"}, None),
    ({"RADAR_MODEL_BACKEND": "github", "ANTHROPIC_API_KEY": "k"}, "claude-opus-4-8"),
    ({"RADAR_MODEL_BACKEND": "github"}, None),
    ({"RADAR_MODEL_BACKEND": "template"}, None),
    ({"RADAR_MODEL_BACKEND": "dryrun"}, None),
    ({"RADAR_MODEL_BACKEND": "ollama"}, "qwen3:4b"),
])
def test_synthesis_model_mirrors_the_pipeline(env, expected):
    assert synthesis_model(env) == expected


# One provider, two models pinned from `python3 -m llm --resolve` — the shape a real
# deployment has. Ids are illustrative; only their families matter to the fence.
_ONE_PROVIDER = {
    "RADAR_LLM_BASE_URL": "https://openrouter.ai/api/v1",
    "RADAR_LLM_API_KEY": "k",
    "RADAR_SYNTHESIS_MODEL": "meta-llama/llama-3.3-70b-instruct:free",
    "RADAR_GRADER_MODEL": "deepseek/deepseek-v3:free",
}


def test_both_roles_read_one_shared_provider():
    """separation.py used to re-derive the synthesis model by mirroring distill's
    backend resolution — duplication that needed a drift test to stay honest. Both
    roles now read `llm.model_for`, so the mirror (and its test) are gone; this pins
    what replaced them."""
    assert synthesis_model(_ONE_PROVIDER) == llm.model_for(llm.SYNTHESIS, _ONE_PROVIDER)


def test_one_provider_two_families_passes_the_fence():
    """The whole point of unifying: a single account, a single key, and the grader is
    still provably not grading its own family."""
    grader_model = llm.model_for(llm.GRADER, _ONE_PROVIDER)
    assert assert_separated(grader_model, _ONE_PROVIDER) != family(synthesis_model(_ONE_PROVIDER))


def test_same_model_for_both_roles_is_refused():
    """The failure the fence exists for, now reachable through one provider: pointing
    both roles at the same model must not become easier just because it is one key."""
    env = {"RADAR_LLM_BASE_URL": "https://openrouter.ai/api/v1",
           "RADAR_LLM_API_KEY": "k",
           "RADAR_SYNTHESIS_MODEL": "anthropic/claude-sonnet-5",
           "RADAR_GRADER_MODEL": "anthropic/claude-opus-5"}
    with pytest.raises(SeparationViolation, match="anthropic"):
        assert_separated("anthropic/claude-opus-5", env)


# --- verdict parsing -------------------------------------------------------

def _verdict(**over) -> dict:
    v = {d: {"score": 4, "why": f"{d} evidence cited"} for d in judge.JUDGED_DIMS}
    v["missed_stories"] = []
    v.update(over)
    return v


def test_parse_accepts_a_fenced_verdict():
    raw = "Here you go:\n```json\n" + json.dumps(_verdict()) + "\n```\nHope that helps."
    assert parse_scores(judge.parse_verdict(raw))["A1"] == 4


def parse_scores(v: dict) -> dict:
    return {k: e["score"] for k, e in v.items() if k != "missed_stories"}


def test_parse_accepts_a_bare_verdict():
    assert judge.parse_verdict(json.dumps(_verdict()))["X5"]["score"] == 4


def test_truncated_verdict_escalates_rather_than_defaulting():
    """The documented failure of scoring incrementally. Defaulting the absent dims would
    write a fabricated score into a permanent trend."""
    partial = {d: {"score": 4, "why": "x"} for d in ("A1", "A2", "A3")}
    with pytest.raises(judge.JudgeError, match="missing"):
        judge.parse_verdict(json.dumps(partial))


def test_out_of_range_score_is_rejected():
    with pytest.raises(judge.JudgeError, match="outside"):
        judge.parse_verdict(json.dumps(_verdict(A1={"score": 9, "why": "x"})))


def test_unjustified_score_is_rejected():
    """rubric.md: every score carries a justification citing concrete evidence. An empty
    `why` is a grader bug, not a score."""
    with pytest.raises(judge.JudgeError, match="justification"):
        judge.parse_verdict(json.dumps(_verdict(A3={"score": 4, "why": "   "})))


def test_no_json_at_all_escalates():
    with pytest.raises(judge.JudgeError, match="no JSON verdict"):
        judge.parse_verdict("I think the digest was pretty good, honestly.")


# --- assembly + schema -----------------------------------------------------

def _assembled(**over):
    kw = dict(
        date="2026-08-09", mode="normal", grader_model="openai/gpt-4.1",
        digest_commit_time=datetime(2026, 8, 9, 11, 30, tzinfo=UTC),
        age_h=2.5, verdict=_verdict(), x3=5, a2_ceiling=5, broken=[])
    kw.update(over)
    return artifacts.assemble(**kw)


def test_assemble_computes_aggregates_from_the_dims():
    ev = _assembled()
    assert ev["quality"]["overall"] == 4.0
    assert ev["experience"]["overall"] == 4.2      # X3=5 lifts the four 4s
    assert ev["overall"] == 4.1


def test_x3_comes_from_age_not_from_the_model():
    ev = _assembled(x3=2, age_h=30.0)
    assert ev["experience"]["X3"]["score"] == 2
    assert "30.0h" in ev["experience"]["X3"]["why"]


def test_a2_ceiling_overrides_a_generous_judge():
    """A model cannot see an HTTP status. Letting its read of source integrity survive a
    measured 404 would make the one checkable dimension unfalsifiable."""
    ev = _assembled(verdict=_verdict(A2={"score": 5, "why": "all primary sources"}),
                    a2_ceiling=2, broken=[{"url": "https://x.test", "status": 404}])
    assert ev["quality"]["A2"]["score"] == 2


def test_assembled_eval_passes_its_own_schema():
    artifacts.validate(_assembled())


def test_schema_rejects_a_missing_grader_model():
    """The field that makes score drift auditable across model updates. The eval currently
    committed at evals/latest.json omits it, which is why validation exists."""
    ev = _assembled()
    ev["grader_model"] = ""
    with pytest.raises(artifacts.SchemaError, match="grader_model"):
        artifacts.validate(ev)


def test_schema_rejects_long_form_dim_keys():
    ev = _assembled()
    ev["quality"]["A1_signal_density"] = ev["quality"].pop("A1")
    with pytest.raises(artifacts.SchemaError):
        artifacts.validate(ev)


def test_schema_rejects_hand_edited_aggregates():
    ev = _assembled()
    ev["quality"]["overall"] = 5.0
    with pytest.raises(artifacts.SchemaError, match="recomputes"):
        artifacts.validate(ev)


def test_schema_rejects_an_impossible_age():
    with pytest.raises(artifacts.SchemaError, match="age_hours_at_eval"):
        artifacts.validate(_assembled(age_h=200.0))


# --- writes ----------------------------------------------------------------

def test_write_puts_the_same_object_in_both_files(tmp_path):
    ev = _assembled()
    written = artifacts.write_eval(ev, tmp_path)
    assert {p.name for p in written} == {"2026-08-09.json", "latest.json"}
    a, b = (json.loads(p.read_text()) for p in written)
    assert a == b == ev


def test_readme_renders_an_empty_history_without_failing(tmp_path):
    """grader.md: on a first run the table has no rows, and that is correct output rather
    than a bug to escalate on."""
    out = artifacts.render_readme([])
    assert "30-day trend" in out
    assert "| Date |" in out


def test_readme_is_capped_at_thirty_rows():
    history = [{"date": f"2026-01-{d:02d}", "mode": "normal", "overall": 4.0,
                "quality": {"overall": 4.0}, "experience": {"overall": 4.0}}
               for d in range(1, 32)]
    assert artifacts.render_readme(history).count("| 2026-01-") == 30


def test_backlog_items_are_causal_and_tied_to_the_worst_dim():
    """A generic wishlist entry is a grader bug per grader.md — the dim and its score are
    embedded so the item cannot drift from what triggered it."""
    ev = _assembled(verdict=_verdict(A5={"score": 1, "why": "missed three major releases"}))
    items = artifacts.backlog_items(ev, "2026-08-09")
    assert len(items) == 1
    assert "A5" in items[0] and "scored 1" in items[0]
    assert "missed three major releases" in items[0]


def test_backlog_append_is_additive(tmp_path):
    p = tmp_path / "backlog.md"
    p.write_text("# Improvement backlog\n\n## Open — pipeline (ai-radar)\n\n"
                 "- [ ] 2026-07-27 · An existing item\n\n## Done\n")
    assert artifacts.append_backlog(["- [ ] 2026-08-09 · A new item"], p) is True
    out = p.read_text()
    assert "An existing item" in out and "A new item" in out
    assert out.index("A new item") < out.index("An existing item")


def test_backlog_append_refuses_when_the_section_is_missing(tmp_path):
    """Rather than guessing where items belong and silently corrupting the file."""
    p = tmp_path / "backlog.md"
    p.write_text("# Improvement backlog\n\nno sections here\n")
    assert artifacts.append_backlog(["- [ ] item"], p) is False


# --- issue conditions ------------------------------------------------------

def test_issue_on_a_dimension_at_or_below_two():
    ev = _assembled(verdict=_verdict(X4={"score": 2, "why": "one feed failure cascaded"}))
    assert "X4" in artifacts.should_file_issue(ev, [])


def test_broken_url_always_produces_an_issue():
    """Reported as `A2 scored 2` rather than `broken URL`: the ceiling caps A2 first, so
    the dimension rule fires and names the dimension. Both are correct triggers and the
    more specific message wins."""
    ev = _assembled(broken=[{"url": "https://x.test/gone", "status": 404}], a2_ceiling=2)
    assert "A2" in artifacts.should_file_issue(ev, [])


def test_broken_url_branch_fires_when_a2_was_not_capped():
    """Reachable only for evals assembled elsewhere — a historical file, or a future
    caller that skips the ceiling. Kept so the rubric's second trigger is not silently
    dependent on the first."""
    ev = _assembled()
    ev["broken_urls"] = [{"url": "https://x.test/gone", "status": 404}]
    assert "broken URL" in artifacts.should_file_issue(ev, [])


def test_no_issue_on_an_unreachable_url():
    ev = _assembled(broken=[{"url": "https://x.test", "status": 0}])
    assert artifacts.should_file_issue(ev, []) is None


def test_no_issue_on_a_healthy_eval():
    assert artifacts.should_file_issue(_assembled(), []) is None


def test_persistent_regression_is_skipped_without_enough_history():
    """grader.md: fewer than 3 prior evals is a valid first-run condition, not a signal."""
    ev = _assembled(verdict=_verdict(A1={"score": 3, "why": "mixed"}))
    assert artifacts.should_file_issue(ev, []) is None


def test_persistent_regression_fires_on_the_third_day():
    ev = _assembled(verdict=_verdict(A1={"score": 3, "why": "mixed"}))
    prior = [{"date": "2026-08-08", "quality": {"A1": {"score": 3}}, "experience": {}},
             {"date": "2026-08-07", "quality": {"A1": {"score": 2}}, "experience": {}}]
    assert "3 consecutive days" in artifacts.should_file_issue(ev, prior)
