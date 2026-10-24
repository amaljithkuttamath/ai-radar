"""Real local Git repositories exercise CI commit/rebase/push behavior."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def git(directory, *args):
    return subprocess.run(
        ["git", "-C", str(directory), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def identity(directory):
    git(directory, "config", "user.name", "Test")
    git(directory, "config", "user.email", "test@example.org")
    git(directory, "config", "commit.gpgsign", "false")


@pytest.fixture
def repositories(tmp_path):
    remote, seed, work, other = [tmp_path / name for name in ("remote.git", "seed", "work", "other")]
    remote.mkdir()
    git(remote, "init", "--bare")
    seed.mkdir()
    git(seed, "init", "-b", "main")
    identity(seed)
    (seed / "data").mkdir()
    (seed / "data/seen.json").write_text('["initial"]\n')
    (seed / "scripts").mkdir()
    shutil.copyfile(Path(__file__).resolve().parents[1] / "scripts/publish.sh", seed / "scripts/publish.sh")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "initial")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    for clone in (work, other):
        git(tmp_path, "clone", "--branch", "main", str(remote), str(clone))
        identity(clone)
    return remote, work, other


def test_publication_rebases_a_committed_change_over_another_writer(repositories):
    remote, work, other = repositories
    (other / "report.md").write_text("Another writer's report\n")
    git(other, "add", "report.md")
    git(other, "commit", "-m", "report")
    git(other, "push")
    (work / "data/seen.json").write_text('["initial", "fresh"]\n')
    result = subprocess.run(
        ["bash", str(work / "scripts/publish.sh"), "collect"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(git(remote, "show", "main:data/seen.json")) == ["initial", "fresh"]
    assert git(remote, "show", "main:report.md") == "Another writer's report"
    assert not git(work, "status", "--porcelain")


def test_rebase_conflict_is_fatal_and_does_not_overwrite_remote(repositories):
    remote, work, other = repositories
    (other / "data/seen.json").write_text('["remote"]\n')
    git(other, "add", "data/seen.json")
    git(other, "commit", "-m", "concurrent ledger")
    git(other, "push")
    (work / "data/seen.json").write_text('["local"]\n')
    result = subprocess.run(
        ["bash", str(work / "scripts/publish.sh"), "collect"], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert json.loads(git(remote, "show", "main:data/seen.json")) == ["remote"]
