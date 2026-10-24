import json
from datetime import datetime, timedelta, timezone

import pytest

from collectors import common
from distill import deliver, focus, reindex, score, synthesize
from radar.config import Settings


def test_brand_substrings_do_not_create_authorship_claims():
    value, reasons = score.heuristic_score(
        {"title": "Fairness metrics for metadata", "source": "Independent Lab"}
    )
    assert value == 0
    assert not reasons


def test_static_star_count_is_not_reported_as_velocity():
    _, reasons = score.heuristic_score({"title": "Tool", "signals": {"gh_stars": 1000}})
    assert not any("trending" in reason or "velocity" in reason for reason in reasons)


def test_score_uses_all_five_observable_signals():
    item = {
        "title": "A reproducible benchmark",
        "source": "OpenAI Blog",
        "links": {"github": "https://github.com/example/project"},
        "signals": {"hf_upvotes": 50},
    }
    assert score.heuristic_score(item)[0] == 5


def test_empty_focus_override_disables_profile(monkeypatch):
    monkeypatch.setenv("FOCUS", "")
    assert focus.active_terms() == []
    assert focus.focus_match({"title": "agent evaluation benchmark"}) is False


def test_reindex_excludes_dryruns_and_wrong_dates(tmp_path):
    reindex.REPORTS.mkdir()
    (reindex.REPORTS / "2026-10-22-digest.md").write_text("# AI Radar — 2026-10-22\n\nGood | digest\n")
    (reindex.REPORTS / "2026-10-23-digest.md").write_text("# DRYRUN — assembled prompt\n")
    (reindex.REPORTS / "2026-10-24-digest.md").write_text("# AI Radar — 2026-10-01\n\nWrong date\n")
    reindex.main()
    assert "2026-10-22" in (reindex.REPORTS / "latest.md").read_text()
    assert "Good \\| digest" in (reindex.REPORTS / "README.md").read_text()
    before = {path: path.read_bytes() for path in reindex.REPORTS.glob("*.md")}
    reindex.main()
    assert {path: path.read_bytes() for path in reindex.REPORTS.glob("*.md")} == before


def test_delivery_cannot_select_readme_or_dryrun(tmp_path, monkeypatch):
    monkeypatch.setattr(deliver, "REPORTS", tmp_path)
    monkeypatch.delenv("RADAR_REPORT_PATH", raising=False)
    (tmp_path / "README.md").write_text("# Reports")
    (tmp_path / "2026-10-23-digest.md").write_text("# DRYRUN\n")
    assert deliver.latest_report() is None


def test_pipeline_lock_rejects_overlapping_writers():
    from radar.pipeline import pipeline_lock

    with pipeline_lock():
        with pytest.raises(RuntimeError, match="another pipeline"):
            with pipeline_lock():
                pytest.fail("concurrent writer admitted")


def test_stale_manifest_cannot_publish(tmp_path):
    from radar.pipeline import collection_manifest

    path = tmp_path / "data/collection.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "status": "ok",
                "item_ids": [],
                "finished_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            }
        )
    )
    with pytest.raises(ValueError, match="stale"):
        collection_manifest("48h")


def test_manifest_window_cannot_be_silently_relabelled(tmp_path):
    from radar.pipeline import collection_manifest

    path = tmp_path / "data/collection.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "status": "ok",
                "item_ids": [],
                "window": "24h",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    )
    with pytest.raises(ValueError, match="window"):
        collection_manifest("48h")


def test_template_displays_hf_observations_as_snapshots(monkeypatch):
    row = common.make_item(
        id="hfmodel:example/model",
        category="releases",
        title="Example model",
        source="HF Trending Models",
        url="https://huggingface.co/example/model",
        signals={"hf_likes": 200, "hf_downloads": 1000},
    )
    row["score"] = 3
    system, user, _ = synthesize.build_prompt([row])
    report = synthesize.call_template(system, user)
    assert "200 HF likes" in report
    assert "1000 HF downloads" in report
    assert row["fetched"] in report


def test_settings_honor_cli_over_environment(monkeypatch):
    monkeypatch.setenv("WINDOW", "7d")
    monkeypatch.setenv("MAX_ITEMS", "9")
    settings = Settings.load({"window": "24h", "max_items": 3})
    assert settings.window == "24h"
    assert settings.max_items == 3


@pytest.mark.parametrize("value", ["-1", "0", "abc", "nan"])
def test_invalid_numeric_configuration_is_rejected(value, monkeypatch):
    monkeypatch.setenv("MAX_ITEMS", value)
    with pytest.raises(ValueError, match="max_items"):
        Settings.load()


def test_preview_settings_disable_optional_model_calls(monkeypatch):
    monkeypatch.setenv("FOCUS_BACKEND", "embed")
    monkeypatch.setenv("CLUSTER_BACKEND", "embed")
    monkeypatch.setenv("RADAR_AGENT", "on")
    Settings.load({"backend": "template"})
    import os

    assert os.environ["FOCUS_BACKEND"] == "lexical"
    assert os.environ["CLUSTER_BACKEND"] == "lexical"


def test_configured_enrichment_limits_reach_the_runtime(tmp_path, monkeypatch):
    import shutil
    import os

    config = tmp_path / "config"
    shutil.copytree(common.CONFIG, config)
    (config / "routines.yaml").write_text(
        "collectors: [arxiv]\nagent:\n  top_n: 3\n  budget: 4\n  sleep_between: 0\n"
    )
    monkeypatch.setattr(common, "CONFIG", config)
    for name in ("RADAR_AGENT_TOP_N", "RADAR_AGENT_BUDGET", "RADAR_AGENT_SLEEP"):
        monkeypatch.delenv(name, raising=False)
    Settings.load()
    assert os.environ["RADAR_AGENT_TOP_N"] == "3"
    assert os.environ["RADAR_AGENT_BUDGET"] == "4"
    assert os.environ["RADAR_AGENT_SLEEP"] == "0.0"


def test_unsafe_reference_scheme_cannot_be_published():
    with pytest.raises(ValueError, match="URL|link"):
        synthesize.validate_report(
            "# AI Radar — 2026-10-24\n[Known](https://example.org)\n[unsafe][x]\n[x]: javascript:alert(1)",
            'TODAY=2026-10-24\n[{"url":"https://example.org"}]',
            1,
        )


def test_blocking_applies_to_already_collected_corpus(tmp_path, monkeypatch):
    from collectors import blocklist

    value = common.make_item(
        id="blocked:1",
        category="research",
        title="Old blocked item",
        source="Fixture",
        url="https://blocked.example/story",
    )
    common.RAW.mkdir(parents=True)
    (common.RAW / "item.json").write_text(json.dumps(value))
    ledger = tmp_path / "broken_sources.yaml"
    ledger.write_text("blocked_domains: [blocked.example]\n")
    monkeypatch.setattr(blocklist, "LEDGER", ledger)
    assert list(common.iter_raw()) == []
