import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from collectors import common
from distill import delta, enrich, reindex, synthesize
from radar import pipeline


def seed():
    common.write_items(
        "releases",
        [
            common.make_item(
                id="repo:agent",
                category="releases",
                title="Agent evaluation toolkit",
                source="Test source",
                url="https://example.org/tool",
                raw_summary="Open source benchmark code for evaluating agents",
                signals={"gh_stars": 120},
            )
        ],
    )


def settings(backend="openai"):
    return SimpleNamespace(window="48h", backend=backend, enrich=False, collectors=("arxiv", "hf_papers"))


def model(monkeypatch):
    monkeypatch.setattr(synthesize, "BACKEND", "openai")
    today = datetime.now(timezone.utc).date().isoformat()
    monkeypatch.setattr(
        synthesize,
        "call_openai_compat",
        lambda *args: (
            f"# AI Radar — {today}\n\n## Research\n\n[Agent evaluation toolkit](https://example.org/tool)\n\nA grounded summary."
        ),
    )


def test_successful_publication_updates_report_state_and_receipt(tmp_path, monkeypatch):
    seed()
    model(monkeypatch)
    output = pipeline.distill(settings())
    assert output.read_text() == (tmp_path / "reports/latest.md").read_text()
    assert "repo:agent" in json.loads(delta.STATE_PATH.read_text())
    receipt = json.loads((tmp_path / "data/publication.json").read_text())
    assert receipt["item_count"] == 1
    assert receipt["collection_status"] == "unverified"


def test_index_failure_restores_previous_publication(tmp_path, monkeypatch):
    seed()
    model(monkeypatch)
    pipeline.distill(settings())
    paths = [*list((tmp_path / "reports").glob("*.md")), delta.STATE_PATH, tmp_path / "data/publication.json"]
    before = {path: path.read_bytes() for path in paths}

    def fail_index():
        (tmp_path / "reports/latest.md").write_text("incomplete")
        raise OSError("disk full")

    monkeypatch.setattr(reindex, "main", fail_index)
    with pytest.raises(OSError, match="disk full"):
        pipeline.distill(settings())
    assert {path: path.read_bytes() for path in paths} == before


def test_partial_collection_is_retained_and_reported(tmp_path, monkeypatch):
    from collectors import arxiv, hf_papers

    def failed():
        raise RuntimeError("source unavailable")

    def succeeded():
        seed()
        return {"collector": "hf_papers", "status": "ok", "written": 1, "sources": []}

    monkeypatch.setattr(arxiv, "main", failed)
    monkeypatch.setattr(hf_papers, "main", succeeded)
    manifest = pipeline.collect(settings())
    assert manifest["status"] == "degraded"
    assert manifest["item_ids"] == ["repo:agent"]
    model(monkeypatch)
    output = pipeline.distill(settings())
    assert "Collection was incomplete: arxiv" in output.read_text()


def test_failed_collection_blocks_old_corpus(tmp_path, monkeypatch):
    from collectors import arxiv, hf_papers

    seed()

    def failed():
        raise RuntimeError("offline")

    for module in (arxiv, hf_papers):
        monkeypatch.setattr(module, "main", failed)
    with pytest.raises(RuntimeError, match="all enabled collectors failed"):
        pipeline.collect(settings())
    with pytest.raises(ValueError, match="corpus"):
        pipeline.distill(settings())
    assert not (tmp_path / "reports").exists()


def test_enrichment_updates_only_scored_artifact(tmp_path, monkeypatch):
    seed()
    raw_before = {path: path.read_bytes() for path in common.RAW.rglob("*.json")}
    scored = tmp_path / "scored.json"
    scored.write_text(json.dumps({"signals": {"gh_stars": 120}}))
    enrich.merge_signals(
        {"id": "repo:agent", "_scored_path": str(scored)},
        {"github": {"stars": 150}, "hn": {"points": 20, "url": "https://news.ycombinator.com/item?id=1"}},
    )
    assert json.loads(scored.read_text())["signals"] == {"gh_stars": 150, "hn_points": 20}
    assert {path: path.read_bytes() for path in common.RAW.rglob("*.json")} == raw_before


def test_previews_never_reuse_an_old_enrichment_brief(tmp_path, monkeypatch):
    synthesize.ENRICHED.mkdir(parents=True)
    (synthesize.ENRICHED / "old.json").write_text(
        json.dumps({"item_id": "repo:agent", "brief": "Stale claim"})
    )
    assert synthesize.load_enriched() == {}


def test_reference_links_are_validated_too():
    user = 'TODAY=2026-10-24\n[{"url":"https://example.org/tool"}]'
    with pytest.raises(ValueError, match="URL|link"):
        synthesize.validate_report(
            "# AI Radar — 2026-10-24\n[Known](https://example.org/tool)\n[Fake][1]\n\n[1]: https://fake.example",
            user,
            1,
        )


def test_brief_from_previous_observation_is_not_used(monkeypatch):
    value = common.make_item(
        id="repo:agent",
        category="releases",
        title="Agent toolkit",
        url="https://example.org/tool",
        source="Fixture",
        raw_summary="Current evidence",
    )
    value["score"] = 3
    monkeypatch.setattr(
        synthesize,
        "load_enriched",
        lambda: {"repo:agent": {"brief": "Outdated claim", "observed_at": "2020-01-01T00:00:00Z"}},
    )
    _, prompt, _ = synthesize.build_prompt([value])
    assert "Current evidence" in prompt
    assert "Outdated claim" not in prompt


def test_failed_publication_restores_refreshed_tracking_ledger(tmp_path, monkeypatch):
    from distill import track
    from radar.storage import atomic_json

    seed()
    model(monkeypatch)
    original = {"tracked:1": {"title": "Existing observation"}}
    atomic_json(track.LEDGER, original)
    monkeypatch.setattr(track, "main", lambda: atomic_json(track.LEDGER, {"changed": {}}))
    monkeypatch.setattr(synthesize, "main", lambda: (_ for _ in ()).throw(ValueError("invalid output")))
    with pytest.raises(ValueError, match="invalid output"):
        pipeline.distill(settings())
    assert json.loads(track.LEDGER.read_text()) == original


def test_auto_fallback_is_published_but_explicit_template_is_preview(tmp_path, monkeypatch):
    seed()
    monkeypatch.setattr(synthesize, "BACKEND", "template")
    monkeypatch.setattr(synthesize, "_REQUESTED_BACKEND", "auto")
    published = pipeline.distill(settings("auto"))
    assert published.parent == tmp_path / "reports"
    assert (tmp_path / "reports/latest.md").read_text() == published.read_text()
    before = {p: p.read_bytes() for p in (tmp_path / "reports").glob("*.md")}
    monkeypatch.setattr(synthesize, "_REQUESTED_BACKEND", "template")
    preview = pipeline.distill(settings("template"))
    assert preview.parent == tmp_path / "data/previews"
    assert {p: p.read_bytes() for p in before} == before


def test_degraded_banner_remains_in_latest_report(tmp_path, monkeypatch):
    seed()
    monkeypatch.setattr(synthesize, "BACKEND", "openai")
    monkeypatch.setattr(synthesize, "call_openai_compat", lambda *a: "not a digest")
    published = pipeline.distill(settings("openai"))
    assert "Degraded run" in published.read_text()
    assert (tmp_path / "reports/latest.md").read_text() == published.read_text()


def test_hashed_fresh_observation_wins_over_tracking_copy(monkeypatch):
    from distill import score, track

    fresh = common.make_item(
        id="ghrepo:acme/tool",
        title="Fresh observation",
        category="releases",
        source="Fixture",
        url="https://github.com/acme/tool",
    )
    score.score_items([fresh])
    assert track.write_carryovers([{**fresh, "title": "Stale", "carryover": True}]) == 0
    records = [json.loads(p.read_text()) for p in score.SCORED.glob("*.json")]
    assert len(records) == 1 and records[0]["title"] == "Fresh observation"


def test_canonical_arxiv_reference_matches_versioned_input():
    user = 'TODAY=2026-10-24\n[{"url":"http://arxiv.org/abs/2610.31574v1"}]'
    synthesize.validate_report("# AI Radar — 2026-10-24\n[Paper](https://arxiv.org/abs/2610.31574)", user, 1)
    with pytest.raises(ValueError, match="unsupported URL"):
        synthesize.validate_report(
            "# AI Radar — 2026-10-24\n[Fake](https://arxiv.org/abs/2610.99999)", user, 1
        )
    with pytest.raises(ValueError, match="unsupported URL"):
        synthesize.validate_report(
            "# AI Radar — 2026-10-24\n[Fake](https://arxiv.org.evil.example/abs/2610.31574)", user, 1
        )


def test_rejected_output_is_retained_without_publication(tmp_path, monkeypatch):
    seed()
    model(monkeypatch)
    monkeypatch.setattr(
        synthesize,
        "call_openai_compat",
        lambda *a: "# AI Radar — 1900-01-01\n\n## Main list\n[Tool](https://example.org/tool)",
    )
    with pytest.raises(ValueError, match="date"):
        pipeline.distill(settings("openai"))
    artifacts = list((tmp_path / "data/previews").glob("rejected-*.json"))
    assert len(artifacts) == 1
    evidence = json.loads(artifacts[0].read_text())
    assert "1900-01-01" in evidence["report"] and "CANDIDATES_JSON" in evidence["user"]
    assert not (tmp_path / "reports/latest.md").exists()


@pytest.mark.parametrize("wrapper", ["**", "*", "`", ""])
def test_link_formatting_is_not_part_of_the_destination(wrapper):
    user = 'TODAY=2026-10-24\n[{"url":"https://example.org/tool"}]'
    synthesize.validate_report(
        f"# AI Radar — 2026-10-24\n{wrapper}[Tool](https://example.org/tool){wrapper}", user, 1
    )
    with pytest.raises(ValueError, match="unsupported URL"):
        synthesize.validate_report(
            f"# AI Radar — 2026-10-24\n{wrapper}[Tool](https://evil.example/fake){wrapper}", user, 1
        )
