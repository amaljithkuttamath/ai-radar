"""Assemble, validate, and write the grader's outputs.

Every file here is one the grader owns outright per `docs/operating/invariants.md#i-01`:
`evals/<date>.json`, `evals/latest.json`, `evals/README.md`, and appends to
`evals/backlog.md`. Nothing else is touched.

The schema in `docs/operating/eval-schema.md` is enforced here rather than trusted,
because that file's own rule is that mixed shapes break README regeneration — a malformed
eval does not fail loudly at write time, it fails later and quietly in a different module.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"

QUALITY_DIMS = ("A1", "A2", "A3", "A4", "A5")
EXPERIENCE_DIMS = ("X1", "X2", "X3", "X4", "X5")
# `deterministic` (ADR-0009) is an eval produced without a model: tier 0 ran, tier 1 did
# not. It carries metrics and checks and NO judged dimensions. Invariant I-09 — unknown is
# omitted, never defaulted — is what keeps it out of the quality trend instead of
# contaminating it with a fabricated score.
VALID_MODES = ("normal", "recovery", "pre-merge", "demo", "deterministic")
DETERMINISTIC = "deterministic"

TREND_DAYS = 30


class SchemaError(Exception):
    """The assembled eval does not match eval-schema.md."""


def mean1(values: list[int]) -> float:
    """Mean to one decimal, matching the schema's `1 decimal` rule on every aggregate."""
    return round(sum(values) / len(values), 1)


def _envelope(*, date: str, mode: str, grader_model: str, digest_commit_time: datetime,
              age_h: float, broken: list[dict], tier0: dict, revs: dict | None) -> dict:
    """The fields every eval carries regardless of whether a model was involved.

    `prompt_rev`/`config_rev` (ADR-0009 §2) are the git revisions of the whitelisted files
    that produced this digest. Without them `change -> outcome` is inexpressible, which is
    why nothing in this repo could previously answer "did that change help?".
    """
    return {
        "date": date,
        "mode": mode,
        "grader_model": grader_model,
        "digest_url": ("https://raw.githubusercontent.com/amaljithkuttamath/ai-radar/"
                       "main/reports/latest.md"),
        "digest_commit_time_utc": digest_commit_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "age_hours_at_eval": round(age_h, 2),
        "tier0": tier0,
        "revs": revs or {},
        "broken_urls": broken,
    }


def assemble_deterministic(*, date: str, mode: str, digest_commit_time: datetime,
                           age_h: float, broken: list[dict], tier0: dict,
                           revs: dict | None = None, reason: str = "") -> dict:
    """An eval with tier 0 only — no model was available, or the fence refused it.

    Deliberately omits `quality`, `experience` and `overall` rather than defaulting them
    (I-09). A zero written here would be a fabricated judgement entering a permanent trend;
    an absent key is a fact. `evals/README.md` renders it as `—`, and `load_history`'s
    consumers skip it, so the trend compares only evals that were actually judged.
    """
    ev = _envelope(date=date, mode=mode, grader_model="", age_h=age_h,
                   digest_commit_time=digest_commit_time, broken=broken,
                   tier0=tier0, revs=revs)
    ev["missed_stories"] = []
    ev["degraded_reason"] = reason
    return ev


def is_judged(ev: dict) -> bool:
    """True if a model scored this eval. The one predicate that decides whether an eval may
    enter the quality trend."""
    return ev.get("mode") != DETERMINISTIC and "quality" in ev


def assemble(*, date: str, mode: str, grader_model: str, digest_commit_time: datetime,
             age_h: float, verdict: dict, x3: int, a2_ceiling: int,
             broken: list[dict], tier0: dict | None = None,
             revs: dict | None = None) -> dict:
    """Build the eval object. Aggregates are always recomputed from the dim scores — the
    schema says they are never edited by hand, and a model asked to sum its own scores
    gets it wrong often enough to matter."""
    quality = {}
    for dim in QUALITY_DIMS:
        score = verdict[dim]["score"]
        if dim == "A2":
            # The observed-link ceiling, applied after judging. A model cannot see an HTTP
            # status; letting its read of "source integrity" override a measured 404 would
            # make the one checkable dimension unfalsifiable.
            score = min(score, a2_ceiling)
        quality[dim] = {"score": score, "why": verdict[dim]["why"]}

    experience = {}
    for dim in EXPERIENCE_DIMS:
        if dim == "X3":
            experience[dim] = {
                "score": x3,
                "why": f"Digest age {age_h}h at eval; anchors in rubric.md.",
            }
        else:
            experience[dim] = {"score": verdict[dim]["score"], "why": verdict[dim]["why"]}

    q_overall = mean1([quality[d]["score"] for d in QUALITY_DIMS])
    x_overall = mean1([experience[d]["score"] for d in EXPERIENCE_DIMS])

    ev = _envelope(date=date, mode=mode, grader_model=grader_model, age_h=age_h,
                   digest_commit_time=digest_commit_time, broken=broken,
                   tier0=tier0 or {}, revs=revs)
    ev.update({
        "overall": round((q_overall + x_overall) / 2, 1),
        "quality": {"overall": q_overall, **quality},
        "experience": {"overall": x_overall, **experience},
        "missed_stories": verdict.get("missed_stories", []),
    })
    return ev


def validate(ev: dict) -> None:
    """Assert the object matches eval-schema.md. Raises SchemaError with the specific
    field, never a bare truthiness check — a schema error you cannot locate is a schema
    error you work around."""
    common = ("date", "mode", "grader_model", "digest_url", "digest_commit_time_utc",
              "age_hours_at_eval", "tier0", "broken_urls", "missed_stories")
    judged_only = ("overall", "quality", "experience")
    for field in common + (judged_only if ev.get("mode") != DETERMINISTIC else ()):
        if field not in ev:
            raise SchemaError(f"missing required field: {field}")

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ev["date"]):
        raise SchemaError(f"date must be YYYY-MM-DD, got {ev['date']!r}")
    if ev["mode"] not in VALID_MODES:
        raise SchemaError(f"mode must be one of {VALID_MODES}, got {ev['mode']!r}")
    if not -12.0 <= ev["age_hours_at_eval"] <= 72.0:
        raise SchemaError(f"age_hours_at_eval {ev['age_hours_at_eval']} outside [-12, 72]")

    # Tier 0 is required on every eval, including judged ones. It is the part that is true
    # regardless of which model looked, and `module_hash` is invariant I-11 — the record
    # that says which version of the checker produced these numbers.
    if not isinstance(ev["tier0"], dict) or not ev["tier0"].get("module_hash"):
        raise SchemaError("tier0.module_hash is required (I-11): an eval must record which "
                          "version of the deterministic checker produced it")

    if ev["mode"] == DETERMINISTIC:
        if ev["grader_model"]:
            raise SchemaError("a deterministic eval must not name a grader_model — no model "
                              "judged it, and recording one would make the trend unauditable")
        for absent in judged_only:
            if absent in ev:
                raise SchemaError(
                    f"deterministic eval must omit {absent!r} (I-09). Unknown is omitted, "
                    "never defaulted: a fabricated score here enters the permanent trend.")
        if not isinstance(ev["broken_urls"], list):
            raise SchemaError("broken_urls must be an array")
        return

    if not ev["grader_model"]:
        raise SchemaError("grader_model is required — it is what makes score drift "
                          "auditable across model updates")

    for axis, dims in (("quality", QUALITY_DIMS), ("experience", EXPERIENCE_DIMS)):
        block = ev[axis]
        if "overall" not in block:
            raise SchemaError(f"{axis}.overall missing")
        for dim in dims:
            if dim not in block:
                raise SchemaError(f"{axis}.{dim} missing")
            entry = block[dim]
            if not isinstance(entry.get("score"), int) or not 0 <= entry["score"] <= 5:
                raise SchemaError(f"{axis}.{dim}.score must be an int 0-5, "
                                  f"got {entry.get('score')!r}")
            if not str(entry.get("why", "")).strip():
                raise SchemaError(f"{axis}.{dim}.why is empty")
        expected = mean1([block[d]["score"] for d in dims])
        if abs(block["overall"] - expected) > 0.05:
            raise SchemaError(f"{axis}.overall is {block['overall']}, recomputes to {expected}")

    if not isinstance(ev["broken_urls"], list) or not isinstance(ev["missed_stories"], list):
        raise SchemaError("broken_urls and missed_stories must both be arrays")

    # Long-form dim keys are the specific mistake eval-schema.md calls out by name.
    for axis in ("quality", "experience"):
        for key in ev[axis]:
            if "_" in key:
                raise SchemaError(
                    f"{axis}.{key}: use the short dim key (A1, X2), never the long form")


class Downgrade(Exception):
    """A deterministic eval would have replaced a judged one for the same day."""


def write_eval(ev: dict, evals_dir: Path | None = None) -> list[Path]:
    """Write `<date>.json` and `latest.json`. Both carry the identical object.

    **The ratchet.** Since ADR-0009 the eval has two runners: `eval-deterministic.yml` in CI
    produces tier 0 immediately after each digest, and the external scheduled task (ADR-0003)
    produces the judged eval on its own clock. That is two processes writing one path, which
    invariant I-01 forbids for good reason.

    The resolution is monotonicity rather than locking: information only ever increases.
    A judged eval may replace a deterministic one for the same date; the reverse is refused.
    So the two runners cannot race destructively no matter what order they land in, and no
    coordination between them is required — which matters, because one of them is a
    scheduled task this repo cannot see.
    """
    d = evals_dir or EVALS
    d.mkdir(parents=True, exist_ok=True)

    dated = d / f"{ev['date']}.json"
    if not is_judged(ev) and dated.exists():
        try:
            existing = json.loads(dated.read_text())
        except (OSError, json.JSONDecodeError):
            existing = {}
        if is_judged(existing):
            raise Downgrade(
                f"{dated.name} already holds a judged eval; refusing to overwrite it with "
                "a deterministic one. Information only increases (ADR-0009 ratchet).")

    body = json.dumps(ev, indent=2, ensure_ascii=False) + "\n"
    written = []
    for name in (f"{ev['date']}.json", "latest.json"):
        p = d / name
        p.write_text(body)
        written.append(p)
    return written


def load_history(evals_dir: Path | None = None) -> list[dict]:
    """Every dated eval, newest first. `demo/` and `pre-merge/` are excluded by living in
    subdirectories, so a plain top-level glob is already correct."""
    d = evals_dir or EVALS
    out = []
    for p in sorted(d.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"), reverse=True):
        try:
            out.append(json.loads(p.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def render_readme(history: list[dict]) -> str:
    """Regenerate `evals/README.md`'s trend table.

    An empty history produces a table with no rows, which grader.md explicitly calls
    correct output on a first run rather than a bug to escalate on.
    """
    rows = ["| Date | Quality | Experience | Overall | Note |",
            "|------|--------:|-----------:|--------:|------|"]
    for ev in history[:TREND_DAYS]:
        if is_judged(ev):
            rows.append(f"| {ev.get('date','?')} | {ev.get('quality',{}).get('overall','?')} "
                        f"| {ev.get('experience',{}).get('overall','?')} "
                        f"| {ev.get('overall','?')} | {ev.get('mode','?')} |")
        else:
            # An em dash, not a zero. The row exists so the day is visibly accounted for —
            # "the grader ran and could not judge" is different information from a gap in
            # the table, and the gap is what hid a 69-day outage.
            failed = ", ".join(ev.get("tier0", {}).get("failed", []))
            note = "deterministic" + (f" · tier-0 failed: {failed}" if failed else "")
            rows.append(f"| {ev.get('date','?')} | — | — | — | {note} |")
    return (
        "# Evals\n\n"
        "Daily grader output. Every entry scores today's digest against the 10-dimension "
        "rubric ([`rubric.md`](rubric.md)). Schema in "
        "[`../docs/operating/eval-schema.md`](../docs/operating/eval-schema.md).\n\n"
        f"## {TREND_DAYS}-day trend\n\n" + "\n".join(rows) + "\n\n"
        "Regenerated by `python -m grader` on every run. Do not edit by hand.\n"
    )


def backlog_items(ev: dict, date: str) -> list[str]:
    """One causal backlog line per lowest-scoring dimension.

    "Causal" is the whole requirement: the item must be tied to the dim that triggered it.
    A generic wishlist entry is a grader bug per grader.md, so the dim and its score are
    embedded in the line rather than described around it.
    """
    if not is_judged(ev):
        # A deterministic eval still has something causal to say. Without this, losing the
        # model emptied the backlog as well as the trend, and the coder woke to an empty
        # queue for 69 days.
        return [f"- [ ] {date} · Fix tier-0 `{c['key']}` · `distill/digest.md` — "
                f"{c['detail']} — triggered by deterministic check {c['key']}"
                for c in ev.get("tier0", {}).get("checks", []) if c.get("ok") is False][:3]

    scored = [(ev["quality"][d]["score"], d, ev["quality"][d]["why"]) for d in QUALITY_DIMS]
    scored += [(ev["experience"][d]["score"], d, ev["experience"][d]["why"])
               for d in EXPERIENCE_DIMS]
    scored.sort(key=lambda r: r[0])
    worst = scored[0][0]
    # Every dim tied at the bottom, capped at three so a uniformly weak day does not append
    # ten items and drown the list it is supposed to prioritise.
    return [
        f"- [ ] {date} · Raise {dim} (scored {score}) · `distill/digest.md` — {why} "
        f"— triggered by {dim} {score}"
        for score, dim, why in scored[:3] if score == worst
    ]


def append_backlog(lines: list[str], path: Path | None = None) -> bool:
    """Append under `## Open — pipeline (ai-radar)`. Append-only: existing items are never
    rewritten, per invariant I-02. Returns False if the section is missing rather than
    guessing where the items belong."""
    p = path or (EVALS / "backlog.md")
    if not lines:
        return False
    try:
        text = p.read_text()
    except OSError:
        return False
    marker = "## Open — pipeline (ai-radar)"
    idx = text.find(marker)
    if idx == -1:
        return False
    insert_at = idx + len(marker)
    p.write_text(text[:insert_at] + "\n\n" + "\n\n".join(lines) + text[insert_at:])
    return True


def should_file_issue(ev: dict, history: list[dict]) -> str | None:
    """The reason to file a `[eval]` issue, or None. Conditions from grader.md#issues.

    A deterministic eval files on its own evidence: a failed tier-0 check is an objective
    defect, and one missing model must not silence the alerting path as well as the trend.
    """
    if not is_judged(ev):
        failed = [c for c in ev.get("tier0", {}).get("checks", []) if c.get("ok") is False]
        if failed:
            return (f"tier-0 check `{failed[0]['key']}` failed: {failed[0]['detail']}"
                    + (f" (+{len(failed) - 1} more)" if len(failed) > 1 else ""))
        return None

    dims = [(d, ev["quality"][d]) for d in QUALITY_DIMS]
    dims += [(d, ev["experience"][d]) for d in EXPERIENCE_DIMS]

    for dim, entry in dims:
        if entry["score"] <= 2:
            return f"{dim} scored {entry['score']}: {entry['why']}"

    real_broken = [b for b in ev["broken_urls"] if b.get("status") != 0]
    if real_broken:
        return f"{len(real_broken)} broken URL(s), first: {real_broken[0]['url']}"

    # Persistent regression. Skipped entirely with fewer than 3 prior evals — grader.md
    # calls out that an empty history is a valid first-run condition, not a signal.
    # Judged evals only. A deterministic day is not evidence of a recovered dim *or* of a
    # persistent one; treating it as either would read a model's absence as a score.
    prior = [h for h in history if h.get("date") != ev["date"] and is_judged(h)][:2]
    if len(prior) >= 2:
        for dim, entry in dims:
            if entry["score"] > 3:
                continue
            past = [h.get("quality", {}).get(dim) or h.get("experience", {}).get(dim)
                    for h in prior]
            if all(p and p.get("score", 5) <= 3 for p in past):
                return f"{dim} has scored <=3 for 3 consecutive days (today: {entry['score']})"
    return None
