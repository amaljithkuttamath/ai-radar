"""Offline regression tests for the collect → publish boundary."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from collectors import common
from distill import delta, synthesize


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "RAW", tmp_path / "raw")
    monkeypatch.setattr(common, "SEEN_PATH", tmp_path / "seen.json")
    return tmp_path


def item(**changes):
    value = common.make_item(
        id="arxiv:1234.56789",
        category="research",
        title="Reliable agent evaluation",
        url="https://arxiv.org/abs/1234.56789",
        source="HF Daily Papers",
        signals={"hf_upvotes": 20},
    )
    return value | changes


def test_seen_item_is_rehydrated_in_fresh_checkout(corpus):
    common.SEEN_PATH.write_text('["arxiv:1234.56789"]')
    common.write_items("research", [item()])
    assert [i["id"] for i in common.iter_raw()] == ["arxiv:1234.56789"]


def test_repeat_observation_updates_traction_and_preserves_links(corpus):
    common.write_items("research", [item(links={"openai": "https://github.com/example/agent"})])
    common.write_items("research", [item(signals={"hf_upvotes": 42})])
    stored = list(common.iter_raw())
    assert len(stored) == 1
    assert stored[0]["signals"]["hf_upvotes"] == 42
    assert stored[0]["links"]["openai"] == "https://github.com/example/agent"


def test_reader_uses_latest_observation_once(corpus):
    common.RAW.mkdir()
    old = item(fetched=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    (common.RAW / "old.json").write_text(json.dumps(old))
    (common.RAW / "new.json").write_text(json.dumps(item(signals={"hf_upvotes": 51})))
    rows = list(common.iter_raw())
    assert len(rows) == 1
    assert rows[0]["signals"]["hf_upvotes"] == 51


def test_invalid_rows_do_not_crash_or_poison_corpus(corpus):
    common.RAW.mkdir()
    for n, bad in enumerate(
        [
            [],
            {"fetched": None},
            item(fetched="2026-01-01"),
            item(url="javascript:alert(1)"),
            item(signals={"gh_stars": -4}),
        ]
    ):
        (common.RAW / f"bad-{n}.json").write_text(json.dumps(bad))
    (common.RAW / "good.json").write_text(json.dumps(item()))
    assert len(list(common.iter_raw())) == 1


def test_zero_window_is_rejected():
    with pytest.raises(ValueError):
        common.parse_window("0h")


def test_template_handles_nested_prompt_blocks(monkeypatch):
    monkeypatch.setattr(synthesize, "load_enriched", lambda: {})
    monkeypatch.setattr(
        synthesize,
        "compute_delta",
        lambda _: {
            "first_run": False,
            "new": [{"title": "Mover", "url": "https://example.org", "score": 2}],
            "climbing": [],
            "cooled": [],
        },
    )
    monkeypatch.setattr(synthesize, "story_arcs", lambda: [])
    system, user, count = synthesize.build_prompt([item(score=3)])
    report = synthesize.call_template(system, user)
    assert count == 1
    assert "Template Error" not in report
    assert "https://arxiv.org/abs/1234.56789" in report


@pytest.fixture
def synthesis(tmp_path, monkeypatch):
    monkeypatch.setattr(synthesize, "ROOT", tmp_path)
    monkeypatch.setattr(synthesize, "load_scored", lambda: [item(score=3)])
    monkeypatch.setattr(synthesize, "load_enriched", lambda: {})
    monkeypatch.setattr(
        synthesize, "compute_delta", lambda _: {"first_run": True, "new": [], "climbing": [], "cooled": []}
    )
    monkeypatch.setattr(synthesize, "story_arcs", lambda: [])
    return tmp_path


def test_dryrun_never_creates_publishable_report(synthesis, monkeypatch):
    monkeypatch.setattr(synthesize, "BACKEND", "dryrun")
    output = synthesize.main()
    assert not list((synthesis / "reports").glob("*-digest.md"))
    assert output.is_file()
    assert output.parent == synthesis / "data" / "previews"


def test_unknown_backend_fails_without_writing(synthesis, monkeypatch):
    monkeypatch.setattr(synthesize, "BACKEND", "typo")
    with pytest.raises(ValueError, match="backend"):
        synthesize.main()
    assert not (synthesis / "reports").exists()


def test_empty_model_output_cannot_replace_digest(synthesis, monkeypatch):
    monkeypatch.setattr(synthesize, "BACKEND", "openai")
    monkeypatch.setattr(synthesize, "synthesize_with_fallback", lambda *a: "")
    monkeypatch.setattr(synthesize, "save_state", lambda _: pytest.fail("state advanced"))
    with pytest.raises(ValueError):
        synthesize.main()
    assert not (synthesis / "reports").exists()


def test_unknown_link_cannot_be_published(synthesis, monkeypatch):
    monkeypatch.setattr(synthesize, "BACKEND", "openai")
    today = datetime.now(timezone.utc).date().isoformat()
    monkeypatch.setattr(
        synthesize,
        "call_openai_compat",
        lambda *a: f"# AI Radar — {today}\n\n## Research\n\n[Invented](https://invented.example/fake)",
    )
    monkeypatch.setattr(synthesize, "save_state", lambda _: pytest.fail("state advanced"))
    with pytest.raises(ValueError, match="link|URL"):
        synthesize.main()


def test_category_reservations_backfill_unused_capacity(monkeypatch):
    monkeypatch.setattr(synthesize, "load_enriched", lambda: {})
    monkeypatch.setattr(synthesize, "compute_delta", lambda _: {})
    monkeypatch.setattr(synthesize, "story_arcs", lambda: [])
    rows = [
        item(
            id=f"repo:{i}", title=f"Distinct project {i}", source=f"Source {i}", category="releases", score=3
        )
        for i in range(8)
    ]
    monkeypatch.setattr(synthesize, "diversify", lambda values: values)
    _, _, count = synthesize.build_prompt(rows, max_candidates=8)
    assert count == 8


def test_same_day_snapshot_does_not_inflate_story_streak(tmp_path, monkeypatch):
    monkeypatch.setattr(delta, "STATE_PATH", tmp_path / "state.json")
    delta.save_state([item(score=3)])
    first = delta.STATE_PATH.read_text()
    delta.save_state([item(score=3)])
    assert delta.STATE_PATH.read_text() == first
