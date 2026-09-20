#!/usr/bin/env python3
"""The auto-merge gate — ADR-0009 §4. Decides; never merges.

Why this exists. Every improvement, however small and however reversible, waited on a human
merge. PR #35 waited 40 days, during which the self-healing loop healed nothing. The fences
were good and the throughput was zero, which is its own kind of broken.

Why it is narrow. The Darwin Gödel Machine (Zhang et al. 2025) had a variant delete the
marker tokens its own hallucination detector searched for — an exploit that lived entirely
*inside* a legitimate edit surface. A whitelist bounds blast radius, not correctness. So
autonomy here is granted only where the change is reversible, non-executing, small, verified
before merge, rate-limited, and automatically undone if the trusted metrics move against it.
Everything else stays a draft for a human, unchanged.

The five conditions are conjunctive and each one is independently sufficient to refuse. They
are in this file rather than in the workflow because a gate written in YAML cannot be
unit-tested, and an untested gate is the thing standing between an agent and `main`.

This module is a FENCE path, decides only, and exits non-zero to mean "human review". The
merge itself is `auto-improve.yml`'s single, auditable step.

Usage:
    python3 scripts/automerge.py --files-from - --additions 12 --deletions 3 \\
        --recent-automerges 0 [--tier0-before a.json --tier0-after b.json]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_whitelist import WHITELIST, is_fence, parse_whitelist  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Condition 1. Text the pipeline *reads*, never code it *runs*. A prompt or a config value
# has a blast radius bounded by the next run's output; a `.py` file's is unbounded, and no
# amount of diff review in CI closes that gap.
ALLOWED_SUFFIXES = (".md", ".yaml", ".yml")
FORBIDDEN_SUFFIXES = (".py", ".sh", ".lock", ".toml", ".cfg", ".ini")

# Condition 2. One file, small diff. Not a proxy for safety — a 20-line prompt change can be
# very bad — but a hard bound on how much has to be understood when reverting at 3am, and a
# structural block on batching an unrelated change into an approved one.
MAX_FILES = 1
MAX_CHANGED_LINES = 20

# Condition 4. One auto-merge per 72h, matching the coder's own file cooldown. The point is
# that each automatic change gets a full observation window to itself; two in flight makes
# every subsequent verdict unattributable, which would quietly destroy the archive's value.
COOLDOWN_H = 72


class Decision:
    """Allowed, or the reasons it is not. Reasons are plural on purpose: reporting only the
    first refusal turns fixing a PR into a guessing game."""

    __slots__ = ("refusals", "notes")

    def __init__(self) -> None:
        self.refusals: list[str] = []
        self.notes: list[str] = []

    @property
    def allowed(self) -> bool:
        return not self.refusals

    def refuse(self, why: str) -> None:
        self.refusals.append(why)

    def note(self, what: str) -> None:
        self.notes.append(what)

    def as_dict(self) -> dict:
        return {"allowed": self.allowed, "refusals": self.refusals, "notes": self.notes}


def tier0_regressed(before: dict | None, after: dict | None) -> str | None:
    """Condition 3: the pre-merge shadow eval must not be worse than main's.

    Compares the *set* of failing checks, not a score. A check that was passing and is now
    failing is a regression regardless of what else improved, because these are objective
    findings rather than a balance to be traded off — the digest either resolves its links
    or it does not.

    Returns None when either side is missing. That is deliberately permissive and is safe
    only because it is one condition of five: a missing shadow eval is reported as a note,
    and the size, path and rate limits still apply.
    """
    if not before or not after:
        return None
    was = set(before.get("failed") or [])
    now = set(after.get("failed") or [])
    introduced = sorted(now - was)
    if introduced:
        return (f"tier-0 regression: {', '.join(introduced)} "
                f"{'passes' if len(introduced) == 1 else 'pass'} on main and "
                f"{'fails' if len(introduced) == 1 else 'fail'} on this branch")
    return None


def gate(files: list[str], *, additions: int, deletions: int,
         recent_automerges: int = 0, tier0_before: dict | None = None,
         tier0_after: dict | None = None, retired_classes: dict | None = None,
         allowed_paths: list[str] | None = None) -> Decision:
    """The whole decision, pure. Every input is a value so the gate is testable without a
    network, a clone, or a GitHub token."""
    d = Decision()
    allowed = allowed_paths if allowed_paths is not None else \
        parse_whitelist(WHITELIST.read_text()).get("coder", [])

    if not files:
        d.refuse("no files changed — nothing to merge")
        return d

    # 1a. fence paths, checked first and separately: a PR touching the evaluator is not a
    # near miss, it is the I-08 case.
    for path in files:
        if is_fence(path):
            d.refuse(f"`{path}` is a fence path (I-08) — never auto-mergeable, and this PR "
                     "should be inspected rather than merged")

    # 1b. whitelist and file type
    for path in files:
        if not any(fnmatch.fnmatch(path, pat) for pat in allowed):
            d.refuse(f"`{path}` is outside the coder whitelist")
        suffix = Path(path).suffix
        if suffix in FORBIDDEN_SUFFIXES or suffix not in ALLOWED_SUFFIXES:
            d.refuse(f"`{path}` is not prompt or config text — auto-merge never covers code "
                     "the pipeline runs, only text it reads")

    # 2. size
    if len(files) > MAX_FILES:
        d.refuse(f"{len(files)} files changed; auto-merge covers at most {MAX_FILES}. "
                 "One file's worth of intent per PR.")
    changed = additions + deletions
    if changed > MAX_CHANGED_LINES:
        d.refuse(f"{changed} lines changed; auto-merge covers at most {MAX_CHANGED_LINES}")

    # 3. pre-merge shadow eval
    if regression := tier0_regressed(tier0_before, tier0_after):
        d.refuse(regression)
    elif not (tier0_before and tier0_after):
        d.note("no pre-merge shadow eval was supplied; the size, path and rate limits are "
               "carrying this decision alone")

    # 4. rate limit
    if recent_automerges:
        d.refuse(f"{recent_automerges} auto-merge(s) in the last {COOLDOWN_H}h. Each "
                 "automatic change gets an observation window to itself, or the archive "
                 "cannot attribute what either of them did.")

    # 5. retirement — the archive's veto (ADR-0009 §2)
    for path in files:
        if reason := (retired_classes or {}).get(path):
            d.refuse(f"edit class `{path}` is retired: {reason}")

    return d


def _load(path: str | None) -> dict | None:
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--files-from", default="-", help="file of changed paths, or - for stdin")
    ap.add_argument("--additions", type=int, default=0)
    ap.add_argument("--deletions", type=int, default=0)
    ap.add_argument("--recent-automerges", type=int, default=0)
    ap.add_argument("--tier0-before", help="tier0 block from main's latest eval")
    ap.add_argument("--tier0-after", help="tier0 block from the shadow eval on this branch")
    ap.add_argument("--archive", help="evals/archive.json, for the retirement veto")
    ap.add_argument("--json", action="store_true", help="emit the decision as JSON")
    args = ap.parse_args()

    stream = sys.stdin if args.files_from == "-" else open(args.files_from)
    files = [ln.strip() for ln in stream if ln.strip()]

    decision = gate(
        files, additions=args.additions, deletions=args.deletions,
        recent_automerges=args.recent_automerges,
        tier0_before=_load(args.tier0_before), tier0_after=_load(args.tier0_after),
        retired_classes=(_load(args.archive) or {}).get("retired_edit_classes", {}))

    if args.json:
        print(json.dumps(decision.as_dict(), indent=2))
    elif decision.allowed:
        print(f"[automerge] ALLOW  {len(files)} file(s), "
              f"{args.additions + args.deletions} line(s).")
        for note in decision.notes:
            print(f"  note: {note}")
    else:
        print("[automerge] HOLD for human review:", file=sys.stderr)
        for why in decision.refusals:
            print(f"  · {why}", file=sys.stderr)

    # Non-zero means "a human decides", which is the safe default and the previous
    # behaviour for every PR. It is not an error and the workflow does not treat it as one.
    return 0 if decision.allowed else 1


if __name__ == "__main__":
    sys.exit(main())
