"""How old is the digest, and is it worth grading at all.

Every rule here is transcribed from `docs/operating/grader.md#freshness`, which was
written after each of them was got wrong at least once by an agent following prose. The
contract already spells out the failure modes; this module is the version that cannot
drift from them.

Stdlib only, like the rest of the grader: the eval loop's whole job is to be a working
critic of a pipeline that may itself be broken, so it must not share a dependency
resolution with the thing it grades.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Strictly greater than 36h is stale. Exactly 36.0 is fresh — grader.md calls that out
# explicitly under "Never escalate on", because an earlier implementation escalated on the
# boundary and produced a daily false alarm.
STALE_AFTER_H = 36.0

# Outside this band the number is not believable and the run must escalate rather than
# score. Negative beyond -12h means clock skew or a parser bug; beyond +72h means the
# pipeline has been down for days and a score would be measuring a corpse.
SANE_AGE_RANGE = (-12.0, 72.0)

_H1_DATE = re.compile(r"^#\s*AI Radar[.\s—-]+(\d{4}-\d{2}-\d{2})", re.MULTILINE)


class Escalate(Exception):
    """A condition grader.md says must halt the run rather than be scored around."""


def commit_time(path: str = "reports/latest.md", root: Path | None = None) -> datetime | None:
    """Authoritative publication time: the git commit time of the digest.

    Not a timestamp inside the file. A pipeline that writes a stale-but-well-formed digest,
    or dies mid-write, leaves its own header date looking current — git's clock is the one
    the pipeline does not author. Same reasoning as `watchdog.yml` and `scripts/health.py`.
    """
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", path],
                             cwd=root or ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    stamp = out.stdout.strip()
    if out.returncode != 0 or not stamp:
        return None
    return datetime.fromtimestamp(int(stamp), tz=timezone.utc)


def h1_date(body: str) -> datetime | None:
    """Fallback publication time: the digest's own H1 date, anchored at noon UTC.

    Two traps, both from grader.md, both previously hit:

      * Never parse the date out of the nav block at the top of `latest.md`. That
        `[<- YYYY-MM-DD]` link points at the PREVIOUS digest and is always wrong. The
        regex is anchored to the `# AI Radar` heading for exactly this reason.
      * Never anchor at midnight. A digest published 13:00 UTC is not "13h old" at
        midnight of the same day; midnight-anchoring silently inflates X3 freshness.
    """
    m = _H1_DATE.search(body)
    if not m:
        return None
    d = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return d.replace(hour=12)


def age_hours(published: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    return round((now - published).total_seconds() / 3600.0, 2)


def check_sane(age_h: float) -> None:
    lo, hi = SANE_AGE_RANGE
    if not (lo <= age_h <= hi):
        raise Escalate(
            f"digest age {age_h}h is outside the sane band [{lo}, {hi}] — clock skew, a "
            "parser bug, or a pipeline that has been down for days. Not scoring.")


def is_stale(age_h: float) -> bool:
    """Stale runs end SILENTLY per grader.md: no eval written, no email, no issue. A stale
    digest is the pipeline's failure to report, not the grader's to score, and writing a
    low eval for it would corrupt the trend with the grader's own opinion of an absence.
    Detecting the absence is `watchdog.yml`'s job."""
    return age_h > STALE_AFTER_H


def x3_score(age_h: float) -> int:
    """X3 freshness, fully determined by age. Anchors from `evals/rubric.md`:
    <6h=5, 6-12=4, 12-24=3, 24-36=2, >36=1. No model judgement involved, so no model
    gets to be generous about it."""
    if age_h < 6:
        return 5
    if age_h < 12:
        return 4
    if age_h < 24:
        return 3
    if age_h <= 36:
        return 2
    return 1


def resolve(body: str, path: str = "reports/latest.md",
            root: Path | None = None, now: datetime | None = None) -> tuple[datetime, float]:
    """(published_at, age_hours) using the priority order in grader.md: git commit time
    first, H1-at-noon only if that lookup fails. Raises Escalate if neither works or the
    resulting age is not believable."""
    published = commit_time(path, root) or h1_date(body)
    if published is None:
        raise Escalate(
            "could not determine the digest's publication time: no git commit for "
            f"{path} and no parsable `# AI Radar <date>` heading in the body.")
    age = age_hours(published, now)
    check_sane(age)
    return published, age
