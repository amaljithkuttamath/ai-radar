"""Which revision of the tunable files produced this digest — ADR-0009 §2.

The gap this closes. `evals/<date>.json` has always recorded what the digest scored and,
since ADR-0007, which model judged it. It never recorded which revision of
`distill/digest.md`, `config/profile.yaml` or `config/sources.yaml` wrote the digest being
scored. So the one relation a self-improving system runs on — *change produced outcome* —
was the one relation not stored, and "did that change help?" was unanswerable.

Only the coder-tunable paths are tracked. A revision of the whole repo would be useless for
attribution: every daily corpus commit would move it, so every eval would look like it
followed a change.

Git is the source, never a timestamp written into a file. Same reasoning as ADR-0005: the
commit clock is the one clock the producer does not author.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The coder's whitelist, minus `evals/backlog.md` (prose, not behaviour). These are the
# files an improvement can actually change the digest through, so these are the files whose
# revisions an outcome can be attributed to.
TUNABLE = (
    "distill/digest.md",
    "distill/brief_spec.md",
    "config/profile.yaml",
    "config/sources.yaml",
    "config/routines.yaml",
    "config/broken_sources.yaml",
)


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                             text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    value = out.stdout.strip()
    return value if out.returncode == 0 and value else None


def file_rev(path: str) -> str | None:
    """Short SHA of the newest commit touching `path`, or None if untracked/unavailable."""
    return _git("log", "-1", "--format=%h", "--", path)


def is_shallow() -> bool:
    """True if this checkout has truncated history.

    On a shallow clone `git log -1 -- <path>` returns the *boundary* commit for every path
    older than the truncation, so every tunable file reports the same revision and no
    transition is ever visible. The archive would then be permanently empty and would look
    exactly like a period with no changes — which is the failure mode this ADR exists to
    remove, reappearing inside the machinery meant to prevent it.

    `scripts/health.py` carries the same guard for the same reason. Both workflows set
    `fetch-depth: 0`; neither of them can be trusted to keep doing so.
    """
    return (ROOT / ".git" / "shallow").exists()


def revs(paths: tuple[str, ...] = TUNABLE) -> dict:
    """`{"prompt_rev", "config_rev", "files": {path: sha}}`.

    The two roll-ups exist because they are what a trend is grouped by: a prompt change and
    a config change have different mechanisms and are worth separating. `files` keeps the
    per-path detail so an attribution can be narrowed after the fact.
    """
    if is_shallow():
        # Measured wrong is worse than not measured: an empty `files` map yields no change
        # events, which is the honest answer, rather than one bogus transition per file.
        return {"prompt_rev": None, "config_rev": None, "files": {}, "shallow": True}
    files = {p: file_rev(p) for p in paths}
    prompt = [v for k, v in files.items() if k.startswith("distill/") and v]
    config = [v for k, v in files.items() if k.startswith("config/") and v]
    return {
        # The newest revision among each group. Two files changed in one commit share a
        # sha, which is exactly the grouping wanted.
        "prompt_rev": max(prompt) if prompt else None,
        "config_rev": max(config) if config else None,
        "files": {k: v for k, v in files.items() if v},
    }


def changed_since(rev: str | None, paths: tuple[str, ...] = TUNABLE) -> list[str]:
    """Tunable paths modified since `rev`. The planner's "what changed between these two
    evals" question, answered from git rather than from memory."""
    if not rev:
        return []
    out = _git("diff", "--name-only", f"{rev}..HEAD", "--", *paths)
    return sorted(out.splitlines()) if out else []
