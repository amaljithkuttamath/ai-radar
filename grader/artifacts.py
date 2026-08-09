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
VALID_MODES = ("normal", "recovery", "pre-merge", "demo")

TREND_DAYS = 30


class SchemaError(Exception):
    """The assembled eval does not match eval-schema.md."""


def mean1(values: list[int]) -> float:
    """Mean to one decimal, matching the schema's `1 decimal` rule on every aggregate."""
    return round(sum(values) / len(values), 1)


def assemble(*, date: str, mode: str, grader_model: str, digest_commit_time: datetime,
             age_h: float, verdict: dict, x3: int, a2_ceiling: int,
             broken: list[dict]) -> dict:
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

    return {
        "date": date,
        "mode": mode,
        "grader_model": grader_model,
        "digest_url": ("https://raw.githubusercontent.com/amaljithkuttamath/ai-radar/"
                       "main/reports/latest.md"),
        "digest_commit_time_utc": digest_commit_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "age_hours_at_eval": round(age_h, 2),
        "overall": round((q_overall + x_overall) / 2, 1),
        "quality": {"overall": q_overall, **quality},
        "experience": {"overall": x_overall, **experience},
        "broken_urls": broken,
        "missed_stories": verdict.get("missed_stories", []),
    }


def validate(ev: dict) -> None:
    """Assert the object matches eval-schema.md. Raises SchemaError with the specific
    field, never a bare truthiness check — a schema error you cannot locate is a schema
    error you work around."""
    for field in ("date", "mode", "grader_model", "digest_url", "digest_commit_time_utc",
                  "age_hours_at_eval", "overall", "quality", "experience",
                  "broken_urls", "missed_stories"):
        if field not in ev:
            raise SchemaError(f"missing required field: {field}")

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ev["date"]):
        raise SchemaError(f"date must be YYYY-MM-DD, got {ev['date']!r}")
    if ev["mode"] not in VALID_MODES:
        raise SchemaError(f"mode must be one of {VALID_MODES}, got {ev['mode']!r}")
    if not ev["grader_model"]:
        raise SchemaError("grader_model is required — it is what makes score drift "
                          "auditable across model updates")
    if not -12.0 <= ev["age_hours_at_eval"] <= 72.0:
        raise SchemaError(f"age_hours_at_eval {ev['age_hours_at_eval']} outside [-12, 72]")

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


def write_eval(ev: dict, evals_dir: Path | None = None) -> list[Path]:
    """Write `<date>.json` and `latest.json`. Both carry the identical object."""
    d = evals_dir or EVALS
    d.mkdir(parents=True, exist_ok=True)
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
        rows.append(f"| {ev.get('date','?')} | {ev.get('quality',{}).get('overall','?')} "
                    f"| {ev.get('experience',{}).get('overall','?')} "
                    f"| {ev.get('overall','?')} | {ev.get('mode','?')} |")
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
    """The reason to file a `[eval]` issue, or None. Conditions from grader.md#issues."""
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
    prior = [h for h in history if h.get("date") != ev["date"]][:2]
    if len(prior) >= 2:
        for dim, entry in dims:
            if entry["score"] > 3:
                continue
            past = [h.get("quality", {}).get(dim) or h.get("experience", {}).get(dim)
                    for h in prior]
            if all(p and p.get("score", 5) <= 3 for p in past):
                return f"{dim} has scored <=3 for 3 consecutive days (today: {entry['score']})"
    return None
