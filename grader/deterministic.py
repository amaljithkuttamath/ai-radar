"""Tier 0: everything about a digest that can be established without asking a model.

Why this tier exists. On 2026-07-13 the grader stopped because `RADAR_GRADER_MODEL` was
unset, and it wrote *nothing* for 69 days — no eval, therefore no issue, therefore an empty
coder queue. One missing environment variable took out Analyze, Plan and Execute together.
The pipeline already solved this class of problem for synthesis in ADR-0006 (a degraded
digest is still a digest); ADR-0009 carries the same rule across to the grader. Losing the
model must degrade the eval's *resolution*, never its *existence*.

It is also the part of the evaluation worth trusting most. Huang et al. (ICLR 2024) found
that revising with no external signal leaves performance flat or worse: improvement tracks
the quality of the external feedback, not the eloquence of the critique. So the deterministic
dims are not a detail of ADR-0007, they are the load-bearing part, and there should be more
of them than the two ADR-0007 shipped.

Deliberately stdlib-only and importing nothing from `distill` (ADR-0007): this must still
run when the pipeline's dependencies are the thing that is broken, which is precisely the
scenario where an eval matters most.

This module is a FENCE path (`docs/operating/whitelist.md`). No agent may edit it, and
`module_hash()` is recorded in every eval it produces so that an edit which evaded the fence
is visible in the permanent trend next to the scores it produced. The Darwin Gödel Machine
(Zhang et al. 2025) had a variant delete the marker tokens its hallucination detector
searched for, scoring a perfect 2.0 while solving nothing — with objective hacking more
frequent when the checking functions were visible to the agent.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Sections `distill/digest.md` instructs synthesis to emit. Absence is a structural defect
# the model judge would score inconsistently and arithmetic scores exactly.
REQUIRED_SECTIONS = ("What changed", "Main list")
OPTIONAL_SECTIONS = ("Story arcs", "Still developing", "Watch-list", "Insights",
                     "Action items")

# Duplicated as a literal from `distill/synthesize.py:degraded_banner`, for the same reason
# `scripts/health.py` duplicates it: importing distill would defeat the independence above.
# `tests/test_deterministic.py` asserts the two stay in step.
DEGRADED_MARKER = "Degraded run — no model synthesis"

# A main-list heading: `### 2. Some title · 3/5`
_MAIN_ITEM = re.compile(r"^###\s+\d+\.\s+(?P<title>.+?)\s+·\s+(?P<score>\d)/5\s*$", re.M)
_SECTION = re.compile(r"^##\s+(?P<name>.+?)\s*$", re.M)


class Check:
    """One deterministic finding: a machine-checkable claim about the digest.

    `ok=None` means "not applicable today" — a quiet window with no tracked items cannot
    fail a re-observation check. It is distinct from False and must never be counted as a
    pass, the same rule `scripts/health.py` applies to UNKNOWN.
    """

    __slots__ = ("key", "ok", "detail")

    def __init__(self, key: str, ok: bool | None, detail: str):
        self.key, self.ok, self.detail = key, ok, detail

    def as_dict(self) -> dict:
        return {"key": self.key, "ok": self.ok, "detail": self.detail}

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return f"Check({self.key}, ok={self.ok}, {self.detail!r})"


def module_hash() -> str:
    """Short content hash of this file — invariant I-11.

    Recorded in every eval. A checker that was silently modified shows up as a hash change
    in the trend, beside the scores the modified checker produced.
    """
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]


# --- parsing (pure) --------------------------------------------------------

def sections(digest: str) -> list[str]:
    return [m.group("name").strip() for m in _SECTION.finditer(digest)]


def main_items(digest: str) -> list[dict]:
    """`[{"title", "score"}]` for every main-list heading, in order."""
    return [{"title": m.group("title").strip(), "score": int(m.group("score"))}
            for m in _MAIN_ITEM.finditer(digest)]


def is_degraded(digest: str) -> bool:
    return DEGRADED_MARKER in digest


# --- tracked-ledger metrics (pure, given the ledger) -----------------------

def reobservation_rate(tracked: dict) -> float | None:
    """Fraction of the radar whose counters were actually re-read on the latest run.

    This is a *trusted* metric under ADR-0009: it is produced by `distill/track.py` and the
    collectors, neither of which is on the coder whitelist, so no prompt or config edit the
    planner is allowed to make can move it. `misses` is the ledger's own count of
    consecutive failed re-fetches; zero misses means the item was seen this run.

    None on an empty ledger — no items is not a re-observation failure.
    """
    if not tracked:
        return None
    seen = sum(1 for it in tracked.values() if (it.get("misses") or 0) == 0)
    return round(seen / len(tracked), 3)


def traction_observations(tracked: dict) -> int:
    """How many tracked items carry at least two traction readings.

    The repo's headline claim is that "Climbing" means two observations of the same counter
    rather than two guesses (README, invariants). This counts the evidence behind it.
    """
    return sum(1 for it in tracked.values() if len(it.get("mag_history") or []) >= 2)


# --- assembly --------------------------------------------------------------

def load_tracked(path: Path | None = None) -> dict:
    """The radar ledger, or {} if unreadable. Unreadable is reported as a check, not raised:
    tier 0's contract is that it always produces a reading."""
    p = path or (ROOT / "data" / "tracked.json")
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def evaluate(digest: str, *, age_h: float, broken: list[dict], link_count: int,
             tracked: dict | None = None) -> dict:
    """The tier-0 reading: metrics plus the checks derived from them.

    Takes the link results rather than fetching them, so this stays pure and the one network
    edge lives in `grader/links.py` where it is already tested.
    """
    tracked = load_tracked() if tracked is None else tracked

    items = main_items(digest)
    present = set(sections(digest))
    missing = [s for s in REQUIRED_SECTIONS if s not in present]
    real_broken = [b for b in broken if b.get("status") != 0]
    unreachable = [b for b in broken if b.get("status") == 0]
    reobs = reobservation_rate(tracked)
    degraded = is_degraded(digest)

    metrics = {
        "age_h": round(age_h, 2),
        "links_total": link_count,
        "links_broken": len(real_broken),
        "links_unreachable": len(unreachable),
        "main_items": len(items),
        "main_score_mean": (round(sum(i["score"] for i in items) / len(items), 2)
                            if items else None),
        "sections_present": len(present),
        "tracked_items": len(tracked),
        "reobservation_rate": reobs,
        "traction_observations": traction_observations(tracked),
        "degraded_synthesis": degraded,
    }

    checks = [
        Check("structure", not missing,
              "all required sections present" if not missing
              else f"missing section(s): {', '.join(missing)}"),
        Check("main_list_nonempty", bool(items),
              f"{len(items)} main-list item(s)" if items
              else "main list is empty — the digest has nothing to say"),
        Check("links_resolve", not real_broken,
              "every link answered 2xx" if not real_broken
              else f"{len(real_broken)} broken link(s), first {real_broken[0].get('url')}"),
        Check("synthesis_present", not degraded,
              "digest carries model synthesis" if not degraded
              else "degraded run — assembled without a model"),
        # None, not False, when the ledger is empty: a radar with nothing on it cannot fail
        # to re-observe. 0.5 is the ledger's own churn floor — below it the traction claims
        # in "Climbing" and "Story arcs" rest on fewer than half the items being re-read.
        Check("traction_observed", None if reobs is None else reobs >= 0.5,
              "no tracked items" if reobs is None
              else f"re-observed {reobs:.0%} of {len(tracked)} tracked items"),
    ]

    failed = [c for c in checks if c.ok is False]
    return {
        "module_hash": module_hash(),
        "metrics": metrics,
        "checks": [c.as_dict() for c in checks],
        "failed": [c.key for c in failed],
    }


def summary_line(tier0: dict) -> str:
    m = tier0["metrics"]
    failed = tier0["failed"]
    state = "all checks pass" if not failed else f"FAILED: {', '.join(failed)}"
    return (f"[grader] tier-0: {m['main_items']} items · {m['links_total']} links "
            f"({m['links_broken']} broken) · reobs "
            f"{'n/a' if m['reobservation_rate'] is None else format(m['reobservation_rate'], '.0%')}"
            f" · {state}")
