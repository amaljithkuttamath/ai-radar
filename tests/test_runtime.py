"""Exercise the public CLI and source-failure reporting without network access."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from collectors import arxiv, hf_papers, hf_trending, github_trending, lab_blogs
from distill import cluster

ROOT = Path(__file__).resolve().parents[1]


def cli(tmp_path, *args, **env):
    environment = {
        k: v
        for k, v in os.environ.items()
        if k not in {"RADAR_HOME", "RADAR_MODEL_BACKEND", "FOCUS_BACKEND", "CLUSTER_BACKEND"}
    }
    return subprocess.run(
        [sys.executable, "-m", "radar", "--root", str(tmp_path), *args],
        cwd=ROOT,
        env=environment | env,
        capture_output=True,
        text=True,
    )


def test_cli_help_describes_operational_commands(tmp_path):
    result = cli(tmp_path, "--help")
    assert result.returncode == 0, result.stderr
    assert all(command in result.stdout for command in ("collect", "distill", "doctor", "demo"))


def test_doctor_reports_missing_publication_without_creating_it(tmp_path):
    result = cli(tmp_path, "doctor", "--json")
    assert result.returncode == 1
    status = json.loads(result.stdout)
    assert status["healthy"] is False
    assert status["checks"]["digest"]["status"] == "missing"
    assert not (tmp_path / "reports").exists()


def test_demo_runs_offline_and_does_not_publish(tmp_path):
    result = cli(tmp_path, "demo")
    assert result.returncode == 0, result.stderr
    previews = list(tmp_path.glob("data/demo/*/data/previews/*-template.md"))
    assert len(previews) == 1
    assert "AI Radar" in previews[0].read_text()
    assert "example.org" in previews[0].read_text()
    assert not (tmp_path / "reports").exists()
    assert not (tmp_path / "data/state.json").exists()


def test_invalid_settings_fail_before_creating_data(tmp_path):
    result = cli(tmp_path, "run", "--window", "0h")
    assert result.returncode == 2
    assert "window" in result.stderr
    assert not (tmp_path / "data").exists()


def test_live_distillation_refuses_missing_corpus(tmp_path):
    result = cli(tmp_path, "distill", "--backend", "github", GITHUB_TOKEN="test-token")
    assert result.returncode != 0
    assert "corpus" in result.stderr.lower() or "candidate" in result.stderr.lower()
    assert not (tmp_path / "reports").exists()


@pytest.mark.parametrize(
    "module,fetcher",
    [
        (arxiv, "fetch"),
        (hf_papers, "fetch_day"),
        (hf_trending, "fetch"),
        (github_trending, "fetch_topic"),
        (lab_blogs, "parse_feed"),
    ],
)
def test_total_source_failure_cannot_report_success(module, fetcher, monkeypatch):
    def unavailable(*args):
        raise OSError("fixture service unavailable")

    monkeypatch.setattr(module, fetcher, unavailable)
    monkeypatch.setattr(module, "write_items", lambda *args: 0)
    with pytest.raises(RuntimeError, match="failed|failure|unavailable"):
        module.main()


def test_default_clustering_does_not_call_embedding_backend(monkeypatch):
    monkeypatch.delenv("CLUSTER_BACKEND", raising=False)
    monkeypatch.setattr(cluster, "_semantic_clusters", lambda _: pytest.fail("unexpected model call"))
    cluster.cluster_items([{"id": str(i), "title": f"Agent benchmark {i}"} for i in range(6)])
