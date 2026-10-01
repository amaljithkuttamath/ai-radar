"""Regressions from the 2026-10-01 digest: duplicated arcs and lost source evidence."""
from __future__ import annotations

import pytest
import urllib.error

import llm
from distill import synthesize
from tests.conftest import make_item


ARC = {
    "title": "GameHorizon Suite: Multi-Horizon Data and Evaluation in Gameplay",
    "url": "https://arxiv.org/abs/2609.25001",
    "streak": 9,
    "first_seen": "2026-09-22",
    "mag_pct_change": 73.0,
}


def _prompt(monkeypatch, arcs):
    monkeypatch.setattr(synthesize, "story_arcs", lambda: arcs)
    monkeypatch.setattr(synthesize, "cluster_items", lambda items: [])
    monkeypatch.setattr(synthesize, "load_enriched", lambda: {})
    return synthesize.build_prompt([])


def _synthesize(monkeypatch, raw, prompt, truncated=False):
    monkeypatch.setattr(synthesize, "BACKEND", "openai")

    def answer(system, user):
        if truncated:
            raise llm.Truncated("token limit", partial=raw)
        return raw

    monkeypatch.setattr(synthesize, "call_openai_compat", answer)
    return synthesize.synthesize_with_fallback([], *prompt)


@pytest.mark.parametrize("heading", ["## Story arcs", "### Story arcs", "**Story arcs**"])
@pytest.mark.parametrize("truncated", [False, True])
def test_published_arcs_use_source_records_once(monkeypatch, heading, truncated):
    """A successful or recovered model response cannot repeat or embellish an arc."""
    prompt = _prompt(monkeypatch, [ARC])
    raw = (
        "# AI Radar — 2026-10-01\n\n## Main list\n\nKeep this prose.\n\n"
        f"{heading}\n\n"
        "- **GameHorizon Suite** — seen 9 runs, traction +730%.\n"
        f"- **{ARC['title']}** — seen 9 runs, traction +73.0%.\n\n"
        "## Insights\n\nKeep this insight."
    )
    out = _synthesize(monkeypatch, raw, prompt, truncated)
    assert out == (
        "# AI Radar — 2026-10-01\n\n## Main list\n\nKeep this prose.\n\n"
        "## Story arcs\n\n"
        "- [GameHorizon Suite: Multi-Horizon Data and Evaluation in Gameplay]"
        "(https://arxiv.org/abs/2609.25001) — seen 9 runs, traction +73.0% "
        "since first seen on 2026-09-22.\n\n"
        "## Insights\n\nKeep this insight."
    )


def test_repeated_arc_sections_and_source_urls_are_collapsed(monkeypatch):
    prompt = _prompt(monkeypatch, [ARC, {**ARC, "title": "GameHorizon Suite"}])
    raw = ("# AI Radar\n\n## Story arcs\n\n- First copy\n\n"
           "**Insights**\n\nKeep this.\n\n**Story arcs**\n\n- Second copy")
    out = _synthesize(monkeypatch, raw, prompt)
    assert out.count("## Story arcs") == 1
    assert out.count("https://arxiv.org/abs/2609.25001") == 1
    assert "Second copy" not in out
    assert "**Insights**\n\nKeep this." in out


def test_no_source_arcs_removes_invented_arc_section(monkeypatch):
    prompt = _prompt(monkeypatch, [])
    raw = ("# AI Radar\n\n## Main list\n\nKeep this.\n\n"
           "## Story arcs\n\n- Invented growth.\n\n## Insights\n\nKeep this too.")
    out = _synthesize(monkeypatch, raw, prompt)
    assert out == ("# AI Radar\n\n## Main list\n\nKeep this.\n\n"
                   "## Insights\n\nKeep this too.")


def test_removing_the_only_unsupported_section_falls_back(monkeypatch):
    prompt = _prompt(monkeypatch, [])
    raw = "# AI Radar\n\n## Story arcs\n\n- Invented growth."
    out = _synthesize(monkeypatch, raw, prompt)
    assert "Degraded run — no model synthesis" in out
    assert "**Main list**" in out
    assert "Invented growth" not in out


def test_omitted_optional_arcs_leave_the_digest_unchanged(monkeypatch):
    prompt = _prompt(monkeypatch, [ARC])
    raw = "# AI Radar\n\n## Main list\n\nA concise digest."
    assert _synthesize(monkeypatch, raw, prompt) == raw


def test_shrunk_request_uses_its_own_arc_evidence(monkeypatch):
    """A 413 retry must not publish numbers from the abandoned request."""
    first_prompt = _prompt(monkeypatch, [ARC])
    retry_prompt = _prompt(monkeypatch, [{**ARC, "mag_pct_change": 80.0}])
    monkeypatch.setattr(synthesize, "build_prompt", lambda *a, **kw: retry_prompt)
    monkeypatch.setattr(synthesize, "BACKEND", "openai")
    responses = iter([None, "# AI Radar\n\n## Story arcs\n\n- Made up."])

    def answer(system, user):
        raw = next(responses)
        if raw is None:
            raise urllib.error.HTTPError("https://example.test", 413, "too large", {}, None)
        return raw

    monkeypatch.setattr(synthesize, "call_openai_compat", answer)
    out = synthesize.synthesize_with_fallback([], *first_prompt)
    assert "traction +80.0%" in out
    assert "traction +73.0%" not in out


def test_arc_titles_and_urls_remain_valid_markdown(monkeypatch):
    arc = {**ARC, "title": "Tool [preview]\nwith *notes*",
           "url": "https://example.test/paper_(preview)"}
    prompt = _prompt(monkeypatch, [arc])
    out = _synthesize(monkeypatch, "# AI Radar\n\n## Story arcs\n\n- Tool", prompt)
    assert "[Tool \\[preview\\] with \\*notes\\*](https://example.test/paper_%28preview%29)" in out


def test_enrichment_preserves_source_evidence_and_dates(monkeypatch):
    """A generated brief must not replace the source the model can check it against."""
    item = make_item(raw_summary="Authors report a 12% gain on their benchmark.")
    monkeypatch.setattr(synthesize, "story_arcs", lambda: [])
    monkeypatch.setattr(synthesize, "cluster_items", lambda items: [])
    monkeypatch.setattr(synthesize, "load_enriched", lambda: {
        item["id"]: {"brief": "The first production-ready solution."},
    })
    _, user, _ = synthesize.build_prompt([item])
    row = synthesize.extract_candidates(user)[0]
    assert row.get("summary") == "Authors report a 12% gain on their benchmark."
    assert row["brief"] == "The first production-ready solution."
    assert row["published"] == "2026-07-01T00:00:00+00:00"
    assert row["fetched"] == "2026-07-27T00:00:00+00:00"
