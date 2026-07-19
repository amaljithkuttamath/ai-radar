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
]


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
