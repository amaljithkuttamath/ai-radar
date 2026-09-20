#!/usr/bin/env python3
"""Enforce docs/operating/whitelist.md against a set of changed paths.

`whitelist.md` has always claimed it is "enforced in code (each agent asserts
before every git operation)". It was not: the assertion lived in a prose code
block inside `coder.md`, which an LLM was trusted to perform. An instruction
inside the agent's reasoning loop is not a control. This script is the control.

Usage:
    git diff --name-only BASE...HEAD | python3 scripts/check_whitelist.py --role coder

Exit 0 if every path is in the role's allowed set, 1 otherwise. The role's
allowed set is parsed from the `## Machine-readable list` YAML block in
whitelist.md, so the doc stays the single source of truth: widening the fence
means editing that block, which is owner-reviewed via CODEOWNERS.

Deliberately stdlib-only. This runs as a required status check, so it must not
depend on `uv sync` succeeding.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WHITELIST = ROOT / "docs" / "operating" / "whitelist.md"

# Paths that configure the fence itself. An agent that can edit these can widen
# its own permissions, which is the one failure mode with no recovery: if the
# allowlist is in scope, there is no allowlist. Denied for every role, including
# roles not yet invented, so a future contract cannot quietly grant them.
FENCE_PATHS = [
    ".github/workflows/*",
    ".github/CODEOWNERS",
    ".github/AGENTS.md",
    "docs/operating/*",
    "scripts/check_whitelist.py",
    # ADR-0009. The evaluator and the rubric it scores against. Before this they were
    # merely out-of-scope, which is the weaker of the two violation classes — an agent
    # editing the thing that grades it tripped the same check as an agent editing an
    # unrelated file. The Darwin Godel Machine (Zhang et al. 2025) had a variant delete
    # the marker tokens its hallucination detector searched for, scoring a perfect 2.0
    # while solving nothing, and reported objective hacking was *more* frequent when the
    # checking functions were visible to the agent. Visibility cannot be removed here;
    # the edit can.
    "grader/*",
    "evals/rubric.md",
]

# Invariant I-10 (ADR-0009): a metric is TRUSTED iff it is computed solely from code and
# state outside the coder's whitelist. The Goodhart brake reads these, so if the coder can
# move one, the brake is measuring the thing it is supposed to be independent of.
#
# Duplicated from `grader/trusted.py:SOURCES` rather than imported, for the same reason
# `parse_whitelist` is hand-rolled: this script runs before any dependency install and must
# not import the package it is policing. `test_whitelist_check.py` asserts the two agree.
TRUSTED_SOURCES = {
    "reobservation_rate": ["distill/track.py", "collectors/"],
    "forecast_accuracy": ["grader/forecast.py", "distill/track.py"],
}


def parse_whitelist(text: str) -> dict[str, list[str]]:
    """Pull the `## Machine-readable list` YAML block into {role: [globs]}.

    Hand-rolled rather than pyyaml: this must run before any dependency install
    so a broken lockfile can't disable the check. The block's shape is fixed by
    whitelist.md ("Adding a path" requires a reviewed PR), so a 20-line parser
    is honest here. Anything unparseable raises rather than silently returning
    an empty set, because an empty allowlist would fail open on `--role` lookup.
    """
    match = re.search(r"## Machine-readable list.*?```yaml\n(.*?)```", text, re.S)
    if not match:
        raise ValueError("no '## Machine-readable list' yaml block in whitelist.md")

    roles: dict[str, list[str]] = {}
    role = None
    for raw in match.group(1).splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t", "-")):           # `coder:` — new role
            role = line.rstrip(":").strip()
            roles.setdefault(role, [])
        elif line.lstrip().startswith("- ") and role:        # `    - config/x.yaml`
            roles[role].append(line.lstrip()[2:].strip())
        # Mid-level keys (`pr:`, `write:`, `direct:`) are intentionally flattened.
        # The distinction between "may PR this" and "may commit this directly" is
        # about *how* a path is written, which CI cannot observe from a diff. This
        # check answers only "may this role touch this path at all". Branch
        # protection enforces the PR-vs-direct half.
    if not roles:
        raise ValueError("machine-readable block parsed to zero roles")
    return roles


def is_fence(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in FENCE_PATHS)


def trusted_disjointness(allowed: list[str],
                         sources: dict[str, list[str]] | None = None) -> list[str]:
    """Invariant I-10: no trusted metric may be derived from a path the coder can edit.

    Returns one violation string per offending (metric, path) pair, empty when the rule
    holds. This is the check that keeps the Goodhart brake honest — Gao et al. (2023) show
    a proxy and its ground truth diverge under optimisation pressure, which is only
    detectable while the ground truth is genuinely out of reach.

    A prefix like `collectors/` is treated as a directory: it conflicts with a whitelist
    entry if either one covers the other, because "the coder may edit `collectors/x.py`"
    and "a trusted metric reads `collectors/`" are the same problem.
    """
    out = []
    for metric, paths in (sources or TRUSTED_SOURCES).items():
        for src in paths:
            for pat in allowed:
                if (fnmatch.fnmatch(src, pat) or src.startswith(pat.rstrip("*"))
                        or pat.startswith(src)):
                    out.append(
                        f"I-10: trusted metric `{metric}` is derived from `{src}`, which "
                        f"the coder whitelist permits via `{pat}`. A metric the planner "
                        "can move is not a referee.")
    return out


def check(paths: list[str], allowed: list[str]) -> tuple[list[str], list[str]]:
    """Split paths into (fence violations, out-of-scope violations)."""
    fence, outside = [], []
    for path in paths:
        if is_fence(path):
            fence.append(path)
        elif not any(fnmatch.fnmatch(path, pat) for pat in allowed):
            outside.append(path)
    return fence, outside


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--role", required=True, help="role key from whitelist.md (e.g. coder)")
    ap.add_argument("--paths-from", default="-", help="file of changed paths, or - for stdin")
    args = ap.parse_args()

    stream = sys.stdin if args.paths_from == "-" else open(args.paths_from)
    paths = [ln.strip() for ln in stream if ln.strip()]

    if not paths:
        print("[whitelist] no changed paths; nothing to check.")
        return 0

    roles = parse_whitelist(WHITELIST.read_text())
    if args.role not in roles:
        print(f"[whitelist] FAIL unknown role '{args.role}'. "
              f"Known: {', '.join(sorted(roles))}", file=sys.stderr)
        return 1

    allowed = roles[args.role]

    # I-10 is a property of the whitelist itself, not of this diff, so it is checked on
    # every invocation regardless of what changed. A whitelist that has grown to cover a
    # trusted metric's source has silently disarmed the Goodhart brake, and the diff that
    # did it would look perfectly in-scope.
    if drift := trusted_disjointness(allowed):
        print("[whitelist] FAIL  the trusted set is no longer out of reach.\n",
              file=sys.stderr)
        for line in drift:
            print(f"  {line}", file=sys.stderr)
        return 1

    fence, outside = check(paths, allowed)

    if not fence and not outside:
        print(f"[whitelist] OK  {len(paths)} path(s) within '{args.role}' scope.")
        return 0

    print(f"[whitelist] FAIL  role '{args.role}' touched paths it does not own.\n",
          file=sys.stderr)
    if fence:
        print("  Fence config (never writable by any agent — this would let the",
              file=sys.stderr)
        print("  agent widen its own permissions):", file=sys.stderr)
        for p in fence:
            print(f"    ✗ {p}", file=sys.stderr)
    if outside:
        print("\n  Outside role scope:", file=sys.stderr)
        for p in outside:
            print(f"    ✗ {p}", file=sys.stderr)
    print(f"\n  Allowed for '{args.role}':", file=sys.stderr)
    for pat in allowed:
        print(f"    · {pat}", file=sys.stderr)
    print("\n  To widen: PR docs/operating/whitelist.md + .github/CODEOWNERS +"
          " the role contract, per whitelist.md 'Adding a path'.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
