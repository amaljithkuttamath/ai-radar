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

# A sibling, and stdlib-only like this module. ADR-0007's rule is that `grader/` never
# imports `distill/`; within the package, sharing the dead-vs-declined status table beats
# keeping two copies of it that can disagree about what "broken" means.
from grader.links import dead as links_dead, inconclusive as links_inconclusive

ROOT = Path(__file__).resolve().parent.parent

# Sections the prompt asks for. Reported as a metric, NOT required: `distill/digest.md` is
# coder-editable and the model reorganises freely — 2026-09-16 grouped items thematically
# (`Benchmark`, `Cost`, `Dataset`) instead of under `Main list`, which is a fine digest and
# would have been a daily false alarm under a name-based requirement.
EXPECTED_SECTIONS = ("What changed", "Main list", "Story arcs", "Still developing",
                     "Watch-list", "Insights", "Action items")

# What a digest must actually have to be a digest at all. This is deliberately close to the
# floor, because the one real structural failure in 89 days was far below it: on 2026-09-18
# the model's reasoning transcript shipped as the newsletter — 13KB opening "Let me analyze
# the task carefully" with no headings anywhere — and nobody noticed. Requiring named
# sections would have flagged fifteen healthy digests to catch that one; requiring *any*
# structure catches it and flags nothing else.
MIN_SECTIONS = 1

# Duplicated as a literal from `distill/synthesize.py:degraded_banner`, for the same reason
# `scripts/health.py` duplicates it: importing distill would defeat the independence above.
# `tests/test_deterministic.py` asserts the two stay in step.
DEGRADED_MARKER = "Degraded run — no model synthesis"

# Main-list item shapes, measured across all 89 committed digests rather than assumed.
# The first version of this file recognised exactly one of them — `### 2. Title · 3/5` —
# which covered 34 of 176 real headings, and on its first autonomous run it filed an issue
# claiming a perfectly good digest had "nothing to say". A checker that cries wolf is worse
# than no checker; this repo has relearned that from three different directions.
#
# The variation is legitimate, not drift: `distill/digest.md` is a coder-editable prompt
# (it is on the whitelist), so the digest's formatting is *expected* to move under this
# parser. That is exactly why the check below treats "cannot parse" as unknown rather than
# as a failure — see `_main_list_check`.
_MAIN_ITEM = re.compile(
    r"""^(?:\d+\.\s+)?                             # '1. ' before either shape
        (?:
          \#{3}\s+(?:\d+\.\s+)?(?P<h>.+?)          # '### 1. Title' or '### Title'
        | \*\*(?P<b>[^*]+?)\*\*                    # '**Title**' or '**Title · 3/5**'
        )
        (?:\s*·\s*(?:score\s*)?(?P<score>\d)\s*/\s*5)?   # score AFTER the bold/heading
        \s*$""",
    re.M | re.X)
# The score sits outside the bold in some digests (`**Title** · score 3/5`) and inside it in
# others (`**Title · score 3/5**`). The group above catches the first; this suffix strip
# catches the second, from the captured title. Both are needed — four real shapes occur
# across the 89 committed digests and recognising three of them is how the first version of
# this file reported a healthy digest as having nothing to say.
_SCORE_SUFFIX = re.compile(r"\s*·\s*(?:score\s*)?(?P<score>\d)\s*/\s*5\s*$")
# Section headings are `##` in most digests and `###` in others (2026-09-02 uses `###`
# for every section including Main list). The level is a formatting choice the prompt does
# not pin, so matching only `##` reported "no sections" on days that had seven.
_SECTION = re.compile(r"^#{2,3}\s+(?P<name>.+?)\s*$", re.M)
_H1 = re.compile(r"^#\s+\S", re.M)
# Some digests label sections in bold rather than with a heading (`**Main list**`), which
# `grader/forecast.py` already has to handle for `**Climbing**`. Counted only for the
# structure check, and only when the line looks like a *label*: short, no score, no link.
# Without those guards every `**Title · score 3/5**` item would register as a section.
_BOLD_LABEL = re.compile(r"^\*\*(?P<name>[^*\[\]]{1,40}?)\*\*\s*$", re.M)
_MD_LINK = re.compile(r"\[[^\]]+\]\((?P<url>[^)\s]+)\)")


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
    """Section names at the document's primary heading level, in order.

    "Primary" rather than "`##`" because the level is not fixed: most digests use `##` for
    sections and `###` for main-list items, but 2026-09-02 uses `###` for both. Hardcoding
    `##` misses a whole digest's structure; counting every `#{2,3}` line counts the items
    as sections and inflates the metric. The shallowest level present is the one that
    means "section" in this document.
    """
    found = [(len(m.group(0)) - len(m.group(0).lstrip("#")), m.group("name").strip())
             for m in _SECTION.finditer(digest)]
    if not found:
        return []
    primary = min(level for level, _ in found)
    return [name for level, name in found if level == primary]


def section_labels(digest: str) -> list[str]:
    """Every way a digest marks a section: headings plus standalone bold labels.

    Used only by the structure check, which asks "is this organised at all?" rather than
    "is it organised the way the prompt asked?". Those are different questions, and
    conflating them is what flagged fifteen healthy digests.
    """
    bold = [m.group("name").strip() for m in _BOLD_LABEL.finditer(digest)
            if "/5" not in m.group("name")]
    return sections(digest) + bold


def section_body(digest: str, name: str) -> str | None:
    """Everything under `## <name>` up to the next `##`, or None if absent.

    Case-insensitive because the digests contain both `Main list` (66) and `Main List`
    (8). Matching case-sensitively here would report a missing section on eight days that
    had one, which is the same false-alarm failure in a different place.
    """
    head = re.compile(rf"^(?P<lvl>#{{2,3}})\s+{re.escape(name)}\s*$", re.M | re.I)
    m = head.search(digest)
    if not m:
        return None
    # Terminate at the next heading of the SAME OR HIGHER level, never at any heading.
    # A `## Main list` section's items are `###` headings, so stopping at the first `###`
    # truncates the body to nothing and reports an empty main list on every digest that
    # uses the common format — which is precisely the false alarm this rewrite exists to
    # remove, reintroduced one line lower down.
    level = len(m.group("lvl"))
    end = re.compile(rf"^#{{1,{level}}}\s", re.M)
    rest = digest[m.end():]
    stop = end.search(rest)
    return rest[:stop.start()] if stop else rest


def main_items(digest: str) -> list[dict]:
    """`[{"title", "score"}]` for every item in the main list, in order.

    Scoped to the Main list section: `###` headings appear under `Story arcs` and elsewhere
    too, and counting those would make an empty main list impossible to detect — the check
    would pass on exactly the digests it exists to catch.

    `score` is None where the digest did not carry one. Most historical digests do not, so
    requiring a score would have thrown away two thirds of the items.
    """
    body = section_body(digest, "Main list")
    if body is None:
        return []
    out = []
    for m in _MAIN_ITEM.finditer(body):
        title = (m.group("h") or m.group("b") or "").strip()
        score = int(m.group("score")) if m.group("score") else None
        if hit := _SCORE_SUFFIX.search(title):
            score = score or int(hit.group("score"))
            title = title[:hit.start()].strip()
        if title:
            out.append({"title": title, "score": score})
    return out


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


def _mean_score(items: list[dict]) -> float | None:
    scored = [i["score"] for i in items if i["score"] is not None]
    return round(sum(scored) / len(scored), 2) if scored else None


# Above this share of unverifiable links, the run has measured its own network rather than
# the digest. Half is generous: a healthy run against a live corpus sees a handful of
# anti-bot 403s at worst, while a blocked runner sees nearly all of them.
BLIND_RUNNER_SHARE = 0.5


def _links_check(broken: list[dict], link_count: int) -> Check:
    """Did the digest cite anything that is not there?

    Three states, for the same reason the main-list check has three. A dead link is the
    digest's fault and is reported. A 403 from an anti-bot host or a blocking proxy is not
    evidence of anything, and a run where most links come back that way has measured the
    runner, not the digest.

    This is not hypothetical. The 2026-09-19 eval in this repo was produced from a sandbox
    whose egress proxy refuses CONNECT: six links returned 0, two returned proxy 403s, and
    the eval recorded "2 broken links" as fact. The same digest scored zero broken links
    from CI the next day. Measured wrong is worse than not measured.
    """
    gone = links_dead(broken)
    if gone:
        return Check("links_resolve", False,
                     f"{len(gone)} dead link(s) ({', '.join(str(b['status']) for b in gone[:3])}), "
                     f"first {gone[0].get('url')}")

    unverified = links_inconclusive(broken)
    if link_count and len(unverified) / link_count >= BLIND_RUNNER_SHARE:
        return Check("links_resolve", None,
                     f"{len(unverified)}/{link_count} links unverifiable from this runner "
                     "(proxy, anti-bot or rate limit) — not read as broken")
    if unverified:
        return Check("links_resolve", True,
                     f"no dead links; {len(unverified)}/{link_count} declined to answer")
    return Check("links_resolve", True, "every link answered 2xx")


def _main_list_check(digest: str, items: list[dict]) -> Check:
    """Is the main list empty — as opposed to merely unparsable?

    The failure worth catching is the one the README describes: roughly 30% of digests once
    shipped with nothing in the main list, because the only candidates were the handful of
    items first seen that morning. That is a real product defect.

    Three states, not two, because this parser reads a prompt the coder is allowed to
    rewrite:

      * items found                  -> pass
      * section absent               -> not applicable; `structure` already reports it, and
                                        reporting one fault twice inflates the failure count
      * no items but real content    -> UNKNOWN. The digest has links and prose under the
                                        heading; the parser simply did not recognise the
                                        shape. Calling that "empty" is how a monitor earns
                                        being ignored, which costs far more than the miss.
      * no items and no content      -> fail, and this is the only branch that files

    The unknown branch is the one that matters. A checker coupled to an editable prompt will
    eventually meet a format it does not know, and the correct response is to say so rather
    than to accuse the pipeline.
    """
    body = section_body(digest, "Main list")
    if body is None:
        return Check("main_list_nonempty", None,
                     "no main-list section (reported by `structure`)")
    if items:
        return Check("main_list_nonempty", True, f"{len(items)} main-list item(s)")

    links = _MD_LINK.findall(body)
    if links or len(body.strip()) > 400:
        return Check("main_list_nonempty", None,
                     f"main list has content ({len(links)} link(s), "
                     f"{len(body.strip())} chars) in a shape this checker does not "
                     "recognise — not read as empty")
    return Check("main_list_nonempty", False,
                 "main list is empty — the digest has nothing to say")


def evaluate(digest: str, *, age_h: float, broken: list[dict], link_count: int,
             tracked: dict | None = None) -> dict:
    """The tier-0 reading: metrics plus the checks derived from them.

    Takes the link results rather than fetching them, so this stays pure and the one network
    edge lives in `grader/links.py` where it is already tested.
    """
    tracked = load_tracked() if tracked is None else tracked

    items = main_items(digest)
    present = {s.casefold() for s in section_labels(digest)}
    expected_seen = [s for s in EXPECTED_SECTIONS if s.casefold() in present]
    has_title = bool(_H1.search(digest))
    gone = links_dead(broken)
    unverified = links_inconclusive(broken)
    reobs = reobservation_rate(tracked)
    degraded = is_degraded(digest)

    metrics = {
        "age_h": round(age_h, 2),
        "links_total": link_count,
        # `broken` means dead, not "did not answer 2xx". The distinction is the whole of
        # the fix: an anti-bot 403 is not a broken link, and counting it as one wrote a
        # fabricated integrity failure into the 2026-09-19 eval.
        "links_broken": len(gone),
        "links_unverified": len(unverified),
        "main_items": len(items),
        # Only over items that carry a score. Most historical digests do not print one,
        # and a mean over a mix of scored and unscored items would be arithmetic on an
        # absence — the shape of error this whole module exists to avoid.
        "main_score_mean": _mean_score(items),
        "sections_present": len(present),
        "expected_sections": len(expected_seen),
        "tracked_items": len(tracked),
        "reobservation_rate": reobs,
        "traction_observations": traction_observations(tracked),
        "degraded_synthesis": degraded,
    }

    checks = [
        Check("structure", has_title and len(present) >= MIN_SECTIONS,
              f"title and {len(present)} section(s); {len(expected_seen)}/"
              f"{len(EXPECTED_SECTIONS)} of the prompt's sections present"
              if has_title and len(present) >= MIN_SECTIONS else
              "not a digest: " + " and ".join(
                  ([] if has_title else ["no H1 title"])
                  + ([] if len(present) >= MIN_SECTIONS else ["no section headings"]))
              + " — check whether the model's reasoning shipped instead of its output"),
        _main_list_check(digest, items),
        _links_check(broken, link_count),
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
