"""A record of every grader invocation, successful or not — ADR-0009 §5.

The distinction this exists to make. A deleted scheduled task and a task that runs daily and
escalates produce the identical observable: no new artifact. Diagnosing the second stall
(2026-08-11 to 2026-09-19) required a human running `python -m grader` by hand to discover
the process was alive and blocked rather than gone.

This is explicitly **not** the heartbeat `watchdog.yml` rejects, and that reasoning stands
verbatim: a success-ping on a healthy component cannot detect a failed independent one, so
artifact staleness remains the *detective* signal. An attempt record is *diagnostic*. It
never proves health — a run that appends `outcome: blocked` every day for two months is a
dead loop that is merely legible about it.

`evals/attempts.jsonl` is append-only and written by the grader alone, preserving I-01. It
is capped, because an unbounded log in a git repo is a slow leak.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATTEMPTS = ROOT / "evals" / "attempts.jsonl"

# ~3 months of daily runs. Enough to see a stall's shape in the file itself; short enough
# that the file stays reviewable in a diff.
MAX_RECORDS = 100

# Every terminal state a run can reach. Kept closed so a new branch in cli.py cannot invent
# an outcome that no consumer knows how to read.
OUTCOMES = ("judged", "deterministic", "stale", "blocked", "escalated")


def record(*, outcome: str, mode: str, reason: str = "", grader_model: str = "",
           tier0: dict | None = None, at: datetime | None = None) -> dict:
    """Build one attempt record. Pure — writing is a separate step so tests and `--dry-run`
    can assert the shape without touching the repo."""
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown outcome {outcome!r}; expected one of {OUTCOMES}")
    now = at or datetime.now(timezone.utc)
    rec = {
        "at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "outcome": outcome,
        "mode": mode,
        "grader_model": grader_model,
        "reason": reason,
    }
    if tier0:
        # The metrics, not the prose. An attempt log is for answering "was it running and
        # what did it see", and the checks are already in the eval when one was written.
        rec["tier0"] = {"module_hash": tier0.get("module_hash"),
                        "failed": tier0.get("failed", []),
                        "metrics": tier0.get("metrics", {})}
    return rec


def append(rec: dict, path: Path | None = None, max_records: int = MAX_RECORDS) -> Path:
    """Append and trim. Rewrites the whole file rather than appending in place: the trim has
    to happen somewhere, and a single atomic write is easier to reason about than an append
    plus an occasional compaction that could interleave with it."""
    p = path or ATTEMPTS
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = load(p)
    existing.append(rec)
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in existing[-max_records:])
    p.write_text(body)
    return p


def load(path: Path | None = None) -> list[dict]:
    """Oldest first. A malformed line is skipped, not fatal: this file's job is to still be
    readable when something else has gone wrong."""
    p = path or ATTEMPTS
    try:
        text = p.read_text()
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def consecutive(outcome: str, records: list[dict]) -> int:
    """How many of the most recent attempts ended in `outcome`.

    The number that distinguishes a blip from a stall. Fifteen consecutive `blocked` runs is
    a loop that is alive, observed, and going nowhere — which is exactly the state nothing
    could name in September 2026.
    """
    n = 0
    for rec in reversed(records):
        if rec.get("outcome") != outcome:
            break
        n += 1
    return n


def summary(records: list[dict]) -> str:
    if not records:
        return "no attempts recorded"
    last = records[-1]
    streak = consecutive(last.get("outcome", ""), records)
    tail = f" ×{streak}" if streak > 1 else ""
    return f"last attempt {last.get('at')} → {last.get('outcome')}{tail}"
