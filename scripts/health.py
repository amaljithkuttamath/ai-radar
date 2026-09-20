#!/usr/bin/env python3
"""Compute pipeline health into `data/health.json` (and a README status block).

Why this exists. On 2026-07-13 the eval loop stopped and went unnoticed for six
days. On 2026-07-31 the model backend started returning `410 Gone` and distill
failed every day for ten days while `collect-corpus` stayed green. Both were
visible in the Actions tab the whole time. Nobody was looking at the Actions tab.

So this collapses every health signal the repo has into one artifact that a page
can render without auth. It is a *reporter*, never a repairer: it makes no
judgement a human can't check, and it must never mask a bad signal.

Two rules follow from the incidents above:

  * Freshness is measured by git commit time, not by a timestamp inside the file.
    A stage that dies mid-write, or writes a stale-but-well-formed artifact, can
    leave its own `date` field looking current. git's clock is the one clock the
    stage does not author. (Same reasoning as `watchdog.yml`.)

  * `data/health.json` carries its own `generated` time so a consumer can tell
    "healthy" from "this monitor stopped running". A monitor that cannot report
    its own absence manufactures confidence, which is worse than no monitor.

A third rule was added on 2026-09-20, after the same outage recurred. Between
2026-08-10 and 2026-09-19 every surface above worked perfectly: the eval signal
read DOWN, the watchdog filed issue #34, and the watchdog went red on fifteen
consecutive days refusing to file a duplicate. Nothing changed for forty-one
days, because nothing measured whether the alarm was ever *answered*:

  * An unanswered alarm is its own signal. Detecting a fault and filing it is
    only half the loop; the repo is self-healing when filed faults get closed,
    not when they get filed. So the age of the oldest open `watchdog` issue is
    reported as a signal in its own right — see `classify_loop`.

Deliberately stdlib-only, like the collectors: this runs on a schedule whose
whole job is to still work when something else is broken, so it must not depend
on `uv sync` resolving.

Usage:
    python3 scripts/health.py                  # write data/health.json
    python3 scripts/health.py --readme         # also refresh the README block
    python3 scripts/health.py --print          # dump JSON to stdout, write nothing
    python3 scripts/health.py --reasons        # one line per non-OK signal, write nothing

`--reasons` is what `watchdog.yml` consumes. The split is deliberate: this script
reports and never escalates, the watchdog escalates and never measures. Keeping
the thresholds in one file is what stops the two surfaces disagreeing about the
meaning of "stale" — which is how the first version shipped a watchdog that
checked evals and silently ignored a ten-day digest outage.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEALTH_PATH = ROOT / "data" / "health.json"
README_PATH = ROOT / "README.md"

REPO = os.environ.get("GITHUB_REPOSITORY", "amaljithkuttamath/ai-radar")
API = "https://api.github.com"

# Markers delimiting the generated block in README.md. Everything between them is
# regenerated; everything outside is hand-written and never touched.
README_START = "<!-- health:start -->"
README_END = "<!-- health:end -->"

OK, WARN, DOWN = "ok", "warn", "down"
# "We could not look" is its own state. It must never serialise as OK: a reader
# that cannot tell "green" from "no reading" will believe a dead pipeline is fine,
# which is the failure this whole script exists to prevent. UNKNOWN ranks below
# WARN so that a blind spot can never *raise* the overall status either.
UNKNOWN = "unknown"
_RANK = {UNKNOWN: 0, OK: 0, WARN: 1, DOWN: 2}

# Both artifacts are produced daily. 48h tolerates one missed run (provider blip,
# GitHub scheduling delay) without crying wolf and still catches a genuine stop on
# day two — the same tolerance `watchdog.yml` applies to evals, kept identical so
# the two surfaces can never disagree about what "stale" means.
DIGEST_MAX_AGE_H = int(os.environ.get("DIGEST_MAX_AGE_HOURS", "48"))
EVAL_MAX_AGE_H = int(os.environ.get("EVAL_MAX_AGE_HOURS", "48"))

# How long a filed alarm may sit unanswered before the loop itself counts as broken.
# 72h is the coder's own file cooldown (docs/self-healing.md, fence 6): an alarm that
# has outlived it has survived at least three coder runs without producing a PR or a
# close, which is no longer explicable as "the fix is in flight".
LOOP_MAX_UNANSWERED_H = int(os.environ.get("LOOP_MAX_UNANSWERED_HOURS", "72"))

# The label `watchdog.yml` files under. Only that workflow applies it, so an open issue
# carrying it is unambiguously an unresolved alarm — unlike `eval`, which the grader
# also applies to routine daily scores that are not faults.
ALARM_LABEL = "watchdog"

# Marker `distill/synthesize.py:degraded_banner` writes into a digest produced without model
# synthesis. Duplicated as a literal rather than imported: this script is stdlib-only so it
# still runs when the pipeline's dependencies don't resolve, and importing `distill` would
# pull in pyyaml. `tests/test_health.py` asserts the two stay in step.
DEGRADED_MARKER = "Degraded run — no model synthesis"
LATEST_DIGEST = ROOT / "reports" / "latest.md"

# Workflows worth reporting, and whether a failure is fatal to the product.
# `watchdog` is expected to be red whenever evals are stale — that is it working,
# not it broken — so its own redness is reported as a warning and the underlying
# eval staleness is what escalates to `down`.
WORKFLOWS = [
    {"file": "collect-corpus.yml", "label": "Collect corpus", "fatal": True},
    {"file": "distill.yml", "label": "Distill digest", "fatal": True},
    {"file": "watchdog.yml", "label": "Watchdog", "fatal": False},
]


# ---------------------------------------------------------------------------
# Pure helpers — no IO, so the classification rules are unit-testable
# ---------------------------------------------------------------------------

def classify_age(age_h: float | None, threshold_h: float) -> str:
    """Age -> status. `None` means "never produced", which is not the same as old:
    a missing artifact cannot be explained by one slow run, so it skips WARN."""
    if age_h is None:
        return DOWN
    if age_h > threshold_h:
        return DOWN
    # Inside the threshold but past a single cadence: the next run is the one that
    # decides. Surfacing it early is the difference between noticing on day one and
    # noticing on day ten.
    if age_h > threshold_h / 2:
        return WARN
    return OK


def fail_streak(conclusions: list[str]) -> int:
    """How many consecutive most-recent runs failed. One failure is a blip; ten is
    a broken contract, and the digest outage looked identical to a blip on day one
    precisely because nothing counted."""
    n = 0
    for c in conclusions:
        if c == "success":
            break
        # `None` = still running, and cancelled/skipped runs say nothing about
        # health. Neither confirms nor breaks a streak, so step over them.
        if c in (None, "cancelled", "skipped"):
            continue
        n += 1
    return n


def classify_workflow(conclusions: list[str], fatal: bool) -> tuple[str, int]:
    streak = fail_streak(conclusions)
    if streak == 0:
        return OK, 0
    if not fatal:
        return WARN, streak
    return (DOWN if streak > 1 else WARN), streak


def classify_loop(alarms: list[dict] | None, now: datetime) -> tuple[str, str]:
    """(status, detail) for the self-healing loop, from the open alarms.

    `alarms` is a list of `{"number": int, "opened": datetime}`; `None` means the read
    failed, which is UNKNOWN and never OK — the same rule the workflow signals follow.
    An empty list is genuinely OK: the loop has nothing outstanding.

    The measurement is deliberately the *oldest* alarm, not the count. Three alarms
    filed this morning is a busy day; one alarm filed six weeks ago is a loop that has
    stopped closing, and only the second of those means the repo cannot be called
    self-healing.
    """
    if alarms is None:
        return UNKNOWN, "could not read open alarms"
    if not alarms:
        return OK, "no unanswered alarms"

    oldest = min(alarms, key=lambda a: a["opened"])
    age_h = (now - oldest["opened"]).total_seconds() / 3600.0
    suffix = "" if len(alarms) == 1 else f" ({len(alarms)} open)"
    if age_h > LOOP_MAX_UNANSWERED_H:
        return DOWN, f"alarm #{oldest['number']} unanswered for {humanise_duration(age_h)}{suffix}"
    return WARN, f"alarm #{oldest['number']} open {humanise_duration(age_h)}{suffix}"


def worst(statuses: list[str]) -> str:
    return max(statuses, key=lambda s: _RANK.get(s, 0), default=OK)


def humanise_duration(age_h: float) -> str:
    if age_h < 1:
        return "<1h"
    if age_h < 48:
        return f"{int(age_h)}h"
    return f"{int(age_h // 24)}d"


def humanise_age(age_h: float | None) -> str:
    if age_h is None:
        return "never"
    return f"{humanise_duration(age_h)} ago"


# ---------------------------------------------------------------------------
# IO edges
# ---------------------------------------------------------------------------

def is_shallow_clone() -> bool:
    """True if this checkout has truncated history.

    Both `health.yml` and `watchdog.yml` set `fetch-depth: 0` and say why in a comment,
    but a comment is not a check. On a shallow clone every artifact older than the
    truncation point reports the age of the *boundary commit*, so a 69-day-dead stage
    reads as fresh — silently, and in the one artifact people trust to tell them
    otherwise. Measured wrong is worse than not measured, so the callers turn this into
    UNKNOWN rather than publishing the number.
    """
    return (ROOT / ".git" / "shallow").exists()


def git_age_hours(pathspec: str, now: datetime | None = None) -> float | None:
    """Hours since the newest commit touching `pathspec`, or None if never committed.

    Needs full history: a shallow checkout reports the clone time instead of the
    commit time, which would read as permanently healthy. `is_shallow_clone` is the
    guard; this function assumes it has already been consulted.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", pathspec],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    stamp = out.stdout.strip()
    if out.returncode != 0 or not stamp:
        return None
    now = now or datetime.now(timezone.utc)
    return (now.timestamp() - int(stamp)) / 3600.0


def digest_is_degraded(path: Path | None = None) -> bool | None:
    """True if the latest digest was assembled without model synthesis, False if it carries
    synthesis, None if there is no readable digest to judge."""
    p = LATEST_DIGEST if path is None else path
    try:
        return DEGRADED_MARKER in p.read_text()
    except OSError:
        return None


def fetch_runs(workflow_file: str, limit: int = 15) -> list[dict]:
    """Recent `main` runs for one workflow, newest first. Returns [] on any error —
    the API being unreachable is not evidence that the pipeline is broken, and a
    monitor that reports DOWN when it merely failed to look would train you to
    ignore it."""
    url = (f"{API}/repos/{REPO}/actions/workflows/{workflow_file}"
           f"/runs?per_page={limit}&branch=main&exclude_pull_requests=true")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-radar-health",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("workflow_runs", [])
    except (urllib.error.URLError, OSError, ValueError, KeyError) as ex:
        print(f"[health] could not read runs for {workflow_file}: {ex}", file=sys.stderr)
        return []


def fetch_open_alarms(limit: int = 50) -> list[dict] | None:
    """Open issues carrying `ALARM_LABEL`, as `{"number", "opened"}`, or None if the read
    failed. `None` and `[]` mean opposite things here — "we could not look" versus "there
    is nothing outstanding" — so they are kept distinct all the way to the status.

    The Issues API returns pull requests as issues. They are filtered out: a PR is an
    *answer* to an alarm, and counting one as an unanswered alarm would make the loop
    look most broken exactly when it was working.
    """
    url = (f"{API}/repos/{REPO}/issues?state=open&labels={ALARM_LABEL}"
           f"&per_page={limit}")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-radar-health",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            issues = json.loads(r.read())
    except (urllib.error.URLError, OSError, ValueError) as ex:
        print(f"[health] could not read open alarms: {ex}", file=sys.stderr)
        return None

    out: list[dict] = []
    for issue in issues:
        if not isinstance(issue, dict) or "pull_request" in issue:
            continue
        try:
            opened = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, ValueError):
            # An alarm we cannot date is not measurable, but dropping the whole read
            # over one malformed row would turn a parse bug into a blind spot.
            continue
        out.append({"number": issue.get("number"), "opened": opened})
    return out


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def age_signal_status(age_h: float | None, threshold_h: float, shallow: bool) -> str:
    """Age classification, or UNKNOWN when the clock it depends on is untrustworthy."""
    return UNKNOWN if shallow else classify_age(age_h, threshold_h)


def _age_detail(template: str, age_h: float | None, shallow: bool) -> str:
    if shallow:
        return "shallow checkout — commit age not measurable (needs fetch-depth: 0)"
    return template.format(age=humanise_age(age_h))


def build_health(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    signals: list[dict] = []
    shallow = is_shallow_clone()

    digest_age = git_age_hours("reports/*-digest.md", now)
    signals.append({
        "key": "digest",
        "label": "Daily digest",
        "status": age_signal_status(digest_age, DIGEST_MAX_AGE_H, shallow),
        "age_h": None if digest_age is None or shallow else round(digest_age, 1),
        "threshold_h": DIGEST_MAX_AGE_H,
        "detail": _age_detail("last digest committed {age}", digest_age, shallow),
        "url": f"https://github.com/{REPO}/blob/main/reports/latest.md",
    })

    # Freshness alone would report green on a digest that is punctual and empty of
    # judgement. After the 2026-07-30 backend retirement the pipeline can publish daily
    # with no synthesis at all — exactly the shape of failure this repo keeps re-learning:
    # the artifact is present, on time, and quietly worth less. WARN rather than DOWN,
    # because a degraded digest is still a digest and the fix is a budget decision.
    degraded = digest_is_degraded()
    signals.append({
        "key": "synthesis",
        "label": "Model synthesis",
        "status": WARN if degraded else (OK if degraded is False else UNKNOWN),
        "age_h": None,
        "threshold_h": None,
        "detail": ("latest digest was assembled without a model (no key, or the backend "
                   "failed)" if degraded else
                   "latest digest carries model synthesis" if degraded is False else
                   "no digest to inspect"),
        "url": f"https://github.com/{REPO}/blob/main/reports/latest.md",
    })

    eval_age = git_age_hours("evals/latest.json", now)
    signals.append({
        "key": "evals",
        "label": "Eval loop",
        "status": age_signal_status(eval_age, EVAL_MAX_AGE_H, shallow),
        "age_h": None if eval_age is None or shallow else round(eval_age, 1),
        "threshold_h": EVAL_MAX_AGE_H,
        # The grader is an external scheduled task (ADR-0003) and appears in no
        # workflow run list, so artifact age is the only signal that exists here.
        "detail": _age_detail("grader last committed {age}", eval_age, shallow),
        "url": f"https://github.com/{REPO}/blob/main/evals/latest.json",
    })

    # The loop's second half. Everything above measures whether a fault is *detected*;
    # this measures whether a detected fault is ever *closed*. They fail independently:
    # through August and September 2026 detection worked every single day and closure
    # never happened once, and with only the signals above that reads as one stale
    # artifact rather than as a loop that has stopped turning.
    alarms = fetch_open_alarms()
    loop_status, loop_detail = classify_loop(alarms, now)
    # The age of the oldest open alarm, which is what the threshold is measured
    # against. None while nothing is outstanding — a loop with no alarms has no
    # latency, and reporting 0 would render as a signal about to breach.
    oldest_h = (min((now - a["opened"]).total_seconds() for a in alarms) / 3600.0
                if alarms else None)
    signals.append({
        "key": "loop",
        "label": "Self-healing loop",
        "status": loop_status,
        "age_h": None if oldest_h is None else round(oldest_h, 1),
        "threshold_h": LOOP_MAX_UNANSWERED_H,
        "open_alarms": None if alarms is None else len(alarms),
        "detail": loop_detail,
        "url": f"https://github.com/{REPO}/issues?q=is%3Aissue+is%3Aopen+label%3A{ALARM_LABEL}",
    })

    workflows: list[dict] = []
    for wf in WORKFLOWS:
        runs = fetch_runs(wf["file"])
        conclusions = [r.get("conclusion") for r in runs]
        status, streak = classify_workflow(conclusions, wf["fatal"])
        latest = runs[0] if runs else {}
        workflows.append({
            "key": wf["file"].removesuffix(".yml"),
            "label": wf["label"],
            "status": status if runs else UNKNOWN,
            "conclusion": latest.get("conclusion"),
            "fail_streak": streak,
            "last_run_at": latest.get("updated_at"),
            "url": latest.get("html_url") or
                   f"https://github.com/{REPO}/actions/workflows/{wf['file']}",
            # No runs at all is unknown, not healthy. Say so rather than showing green.
            "observed": bool(runs),
        })

    overall = worst([s["status"] for s in signals] +
                    [w["status"] for w in workflows if w["observed"]])

    return {
        # Consumers key their own staleness check off this. See module docstring:
        # the monitor must be able to report its own absence.
        "generated": now.isoformat(),
        "repo": REPO,
        "status": overall,
        "signals": signals,
        "workflows": workflows,
    }


def render_markdown(health: dict) -> str:
    # UNKNOWN is in the map deliberately. Any signal can be unreadable — `synthesis`
    # when there is no digest, `loop` when the Issues API refuses — and a KeyError in
    # the renderer would take out the whole report over a blind spot in one row.
    icon = {OK: "🟢", WARN: "🟡", DOWN: "🔴", UNKNOWN: "⚪"}
    rows = [f"| signal | status | detail |", "|---|---|---|"]
    for s in health["signals"]:
        rows.append(f"| [{s['label']}]({s['url']}) | {icon[s['status']]} {s['status']} "
                    f"| {s['detail']} |")
    for w in health["workflows"]:
        if not w["observed"]:
            rows.append(f"| [{w['label']}]({w['url']}) | ⚪ unknown | no runs observed |")
            continue
        detail = (f"{w['fail_streak']} consecutive failures"
                  if w["fail_streak"] else f"last run {w['conclusion']}")
        rows.append(f"| [{w['label']}]({w['url']}) | {icon[w['status']]} {w['status']} "
                    f"| {detail} |")
    stamp = health["generated"][:16].replace("T", " ")
    return "\n".join(rows) + f"\n\nGenerated {stamp} UTC by `scripts/health.py`.\n"


def update_readme(health: dict) -> bool:
    """Replace the delimited block in README.md. Returns False (without writing) if
    the markers are missing, rather than guessing where the block belongs."""
    text = README_PATH.read_text()
    start, end = text.find(README_START), text.find(README_END)
    if start == -1 or end == -1 or end < start:
        print(f"[health] README markers not found; skipping README update", file=sys.stderr)
        return False
    block = f"{README_START}\n\n{render_markdown(health)}\n{README_END}"
    README_PATH.write_text(text[:start] + block + text[end + len(README_END):])
    return True


def reason_lines(health: dict) -> list[str]:
    """`<status>\\t<label>: <detail>` for every signal that is not OK, worst first.

    UNKNOWN is omitted wherever it appears, workflow or signal: "the API told us
    nothing" is not a fault, and a watchdog that fires on it would be firing on its
    own blindness. Nothing is lost by the omission — every artifact whose reading can
    come back UNKNOWN is also covered by a signal that measures it from disk.
    """
    rows: list[tuple[str, str]] = []
    for s in health["signals"]:
        if s["status"] not in (OK, UNKNOWN):
            rows.append((s["status"], f"{s['label']}: {s['detail']}"))
    for w in health["workflows"]:
        if not w["observed"] or w["status"] == OK:
            continue
        detail = (f"{w['fail_streak']} consecutive failures"
                  if w["fail_streak"] else f"last run {w['conclusion']}")
        rows.append((w["status"], f"{w['label']}: {detail}"))
    rows.sort(key=lambda r: -_RANK.get(r[0], 0))
    return [f"{status}\t{text}" for status, text in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readme", action="store_true", help="refresh the README status block")
    ap.add_argument("--print", dest="to_stdout", action="store_true",
                    help="print JSON to stdout and write nothing")
    ap.add_argument("--reasons", action="store_true",
                    help="print one line per non-OK signal and write nothing")
    args = ap.parse_args()

    health = build_health()

    if args.reasons:
        for line in reason_lines(health):
            print(line)
        return

    if args.to_stdout:
        print(json.dumps(health, indent=2))
        return

    HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_PATH.write_text(json.dumps(health, indent=2) + "\n")
    print(f"[health] wrote {HEALTH_PATH.relative_to(ROOT)} · status={health['status']}")

    if args.readme:
        update_readme(health)

    for s in health["signals"]:
        print(f"  {s['status']:>4}  {s['label']}: {s['detail']}")
    for w in health["workflows"]:
        state = w["conclusion"] if w["observed"] else "no runs"
        print(f"  {w['status']:>4}  {w['label']}: {state} (streak={w['fail_streak']})")

    # Exit 0 regardless of what was found. This job's contract is "the report was
    # produced"; going red on a bad *reading* would conflate "the pipeline is
    # broken" with "the monitor is broken", and the whole point is to tell those
    # two apart. Escalation belongs to watchdog.yml.


if __name__ == "__main__":
    main()
