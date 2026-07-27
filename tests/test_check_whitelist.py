"""Tests for the whitelist enforcer.

These are deliberately written against the real docs/operating/whitelist.md
rather than a fixture. The enforcer's job is to be true about *this* repo, so a
test that passes against a synthetic whitelist while the real one is malformed
would be worse than no test.

Run: uv run --with pytest pytest tests/ -q
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_whitelist.py"

sys.path.insert(0, str(ROOT / "scripts"))
from check_whitelist import check, is_fence, parse_whitelist  # noqa: E402


def run(paths: list[str], role: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--role", role],
        input="\n".join(paths), capture_output=True, text=True,
    )


# ── parsing the real whitelist ────────────────────────────────────────────────

def test_parses_real_whitelist():
    roles = parse_whitelist((ROOT / "docs" / "operating" / "whitelist.md").read_text())
    assert "coder" in roles and "grader" in roles


def test_coder_scope_matches_documented_six_paths():
    """The whitelist's coder PR set is the fence everyone reasons about.

    If this test fails, someone widened agent write scope — which is exactly the
    change that should require a human to look, so the failure is the feature.
    """
    roles = parse_whitelist((ROOT / "docs" / "operating" / "whitelist.md").read_text())
    assert set(roles["coder"]) == {
        "config/sources.yaml", "config/profile.yaml", "config/routines.yaml",
        "config/broken_sources.yaml", "distill/digest.md", "distill/brief_spec.md",
        "evals/backlog.md",
    }


def test_malformed_whitelist_raises_rather_than_failing_open():
    """An unparseable whitelist must not degrade to an empty (permissive) set."""
    with pytest.raises(ValueError):
        parse_whitelist("# Whitelist\n\nNo machine-readable block here.\n")


# ── the fence: paths no role may ever touch ───────────────────────────────────

@pytest.mark.parametrize("path", [
    ".github/workflows/distill.yml",
    ".github/workflows/whitelist.yml",
    ".github/CODEOWNERS",
    ".github/AGENTS.md",
    "docs/operating/whitelist.md",
    "docs/operating/coder.md",
    "scripts/check_whitelist.py",
])
def test_fence_paths_are_denied(path):
    """Self-modification is the one failure with no recovery: an agent that can
    edit the allowlist has no allowlist. Denied regardless of role."""
    assert is_fence(path)
    assert run([path], "coder").returncode == 1


def test_enforcer_cannot_be_disabled_by_the_role_it_governs():
    fence, _ = check(["scripts/check_whitelist.py"], allowed=["**"])
    assert fence == ["scripts/check_whitelist.py"]


# ── role scope ────────────────────────────────────────────────────────────────

def test_coder_allowed_paths_pass():
    r = run(["config/sources.yaml", "distill/digest.md"], "coder")
    assert r.returncode == 0, r.stderr


def test_coder_cannot_touch_python():
    """The live gap this whole harness exists to close: today nothing stops an
    agent editing distill/score.py, which silently changes every future digest."""
    r = run(["distill/score.py"], "coder")
    assert r.returncode == 1
    assert "distill/score.py" in r.stderr


def test_coder_cannot_touch_reindex_the_site_contract():
    """reindex.py writes reports/latest.md + README.md, which radar.astro parses
    at runtime. Breaking it breaks the live site with no build-time signal."""
    assert run(["distill/reindex.py"], "coder").returncode == 1


def test_grader_and_coder_scopes_are_distinct():
    """invariants.md I-01: one writer per state file. evals/*.json is grader-only."""
    assert run(["evals/2026-07-19.json"], "coder").returncode == 1
    assert run(["evals/2026-07-19.json"], "grader").returncode == 0


def test_mixed_diff_fails_on_the_one_bad_path():
    r = run(["config/sources.yaml", "distill/score.py"], "coder")
    assert r.returncode == 1
    assert "distill/score.py" in r.stderr


def test_unknown_role_fails_closed():
    assert run(["config/sources.yaml"], "nonexistent").returncode == 1


def test_empty_diff_is_not_a_violation():
    assert run([], "coder").returncode == 0
