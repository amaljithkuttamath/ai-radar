"""Change → outcome. The Knowledge the loop never had — ADR-0009 §2.

Read against MAPE-K (Kephart & Chess 2003), this repo had a strong Monitor, a single-point
Analyze, a Plan step that was a static lookup table, an Execute step with a human in it, and
essentially no K. The K is what self-evolution runs on, and its absence had one concrete
symptom: nothing here could answer *"did that change help?"*. A PR merged, the scores moved,
and the pairing was never written down.

**A derived view, not a second ledger.** ADR-0009 proposed `evals/archive.jsonl`, appended
at merge time. This is better: every fact needed is already in the eval history, because
`provenance.py` now stamps each eval with the revisions of the coder-tunable files that
produced the digest. So a change event is simply a *transition* in those revisions between
consecutive evals, and the archive is recomputed from the evals rather than maintained
alongside them. Three things follow, all of which matter more than the convenience of an
append:

  * One writer, one source of truth. A separate ledger would be a second writer over the
    same facts (I-01) and could disagree with the evals it claims to summarise.
  * It cannot silently stop. A ledger that stops being appended looks exactly like a period
    with no changes — the failure mode this whole ADR exists to remove.
  * It is correct retroactively. Improve the attribution rule and every past change is
    re-attributed, rather than only the ones that happen after the deploy.

**What the verdicts are for.** Selection ("do more of what helped") is not supportable at
one sample a day — the DGM and AlphaEvolve archives work because they evaluate thousands of
variants in parallel and this evaluates one newsletter. Retirement ("stop doing what harms")
is supportable, because it needs only a consistent sign, and that is the direction this
module is wired for.

This module is a FENCE path. No agent may edit it.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "evals" / "archive.json"

# Evals on each side of a change used to judge it. Fewer than this and the verdict is a
# coin flip dressed as evidence.
WINDOW = 5
MIN_SIDE = 2

# Relative movement below which nothing is claimed. Matches `trusted.DEGRADE_BAND` and
# `forecast.FLAT_BAND`: the repo has one idea of what counts as noise.
BAND = 0.05

VERDICTS = ("helped", "harmed", "neutral", "inconclusive")

# Two consecutive `harmed` verdicts retire an edit class until a human re-enables it. Two
# rather than one because a single daily sample is noisy; consecutive rather than cumulative
# because a class that has since been fixed should not stay retired on its history.
RETIRE_AFTER = 2


def _mean(values: list) -> float | None:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else None


def _side(evals: list[dict]) -> dict:
    """The measurable summary of one side of a change."""
    judged = [e for e in evals if e.get("mode") != "deterministic" and "overall" in e]
    return {
        "n": len(evals),
        "n_judged": len(judged),
        "rubric": _mean([e.get("overall") for e in judged]),
        "trusted": {
            key: _mean([(e.get("trusted") or {}).get(key) for e in evals])
            for key in ("reobservation_rate", "forecast_accuracy")
        },
    }


def change_events(history: list[dict]) -> list[dict]:
    """Every transition in the tunable revisions, newest first.

    `history` is newest-first, as `artifacts.load_history` returns it. An eval with no
    `revs` predates ADR-0009 and is skipped rather than treated as a change: the absence of
    provenance is not evidence that everything changed at once.
    """
    stamped = [e for e in history if (e.get("revs") or {}).get("files")]
    events = []
    for newer, older in zip(stamped, stamped[1:]):
        new_files = (newer["revs"] or {}).get("files", {})
        old_files = (older["revs"] or {}).get("files", {})
        changed = sorted(p for p in set(new_files) | set(old_files)
                         if new_files.get(p) != old_files.get(p))
        if changed:
            events.append({
                "at": newer.get("date"),
                "files": changed,
                "from_rev": old_files.get(changed[0]),
                "to_rev": new_files.get(changed[0]),
                "edit_class": edit_class(changed),
            })
    return events


def edit_class(files: list[str]) -> str:
    """The unit a verdict is remembered against.

    Per-file rather than per-PR: the same file gets edited repeatedly for the same reason,
    and "editing digest.md for A1 keeps making things worse" is the pattern worth retiring.
    Per-PR verdicts would never accumulate enough evidence to say anything.
    """
    if not files:
        return "none"
    return files[0] if len(files) == 1 else "multi:" + ",".join(files)


def attribute(event: dict, history: list[dict], window: int = WINDOW) -> dict:
    """Judge one change against the evals on either side of it.

    Trusted metrics decide. The rubric is reported but never used to *promote* a verdict to
    `helped`, because the rubric is the proxy the change may have been optimising — Gao et
    al. (2023) is precisely the finding that a rising proxy is not evidence of improvement.
    It is used to *detect* the Goodhart shape: rubric up, ground truth down, which is
    `harmed` and not `neutral`.
    """
    dates = [e.get("date") for e in history]
    try:
        idx = dates.index(event["at"])
    except ValueError:
        return {**event, "verdict": "inconclusive", "why": "eval for the change date is gone"}

    after = _side(history[max(0, idx - window + 1):idx + 1])   # newest-first: after is nearer 0
    before = _side(history[idx + 1:idx + 1 + window])

    if after["n"] < MIN_SIDE or before["n"] < MIN_SIDE:
        return {**event, "before": before, "after": after, "verdict": "inconclusive",
                "why": f"fewer than {MIN_SIDE} evals on one side"}

    moves = []
    for key, now in after["trusted"].items():
        then = before["trusted"].get(key)
        if now is None or then is None or then == 0:
            continue
        moves.append((key, (now - then) / abs(then)))

    if not moves:
        return {**event, "before": before, "after": after, "verdict": "inconclusive",
                "why": "no trusted metric was measurable on both sides"}

    worst_key, worst = min(moves, key=lambda m: m[1])
    best_key, best = max(moves, key=lambda m: m[1])
    rubric_rose = (after["rubric"] is not None and before["rubric"] is not None
                   and after["rubric"] > before["rubric"])

    if worst < -BAND:
        why = f"{worst_key} fell {worst:.0%}"
        if rubric_rose:
            why += (f" while the rubric rose {before['rubric']}→{after['rubric']} "
                    "— the Goodhart shape")
        return {**event, "before": before, "after": after, "verdict": "harmed", "why": why}
    if best > BAND:
        return {**event, "before": before, "after": after, "verdict": "helped",
                "why": f"{best_key} rose {best:.0%}"}
    return {**event, "before": before, "after": after, "verdict": "neutral",
            "why": "no trusted metric moved beyond noise"}


def build(history: list[dict], window: int = WINDOW) -> list[dict]:
    """The whole archive, newest first."""
    return [attribute(e, history, window) for e in change_events(history)]


def retired(archive: list[dict], threshold: int = RETIRE_AFTER) -> dict[str, str]:
    """`{edit_class: why}` for classes the planner must stop using.

    Consecutive from the most recent, so a class that was harmful and has since been fixed
    recovers on its next non-harmful verdict rather than staying retired on its history.
    """
    streaks: dict[str, list] = {}
    for entry in archive:                                  # newest first
        cls = entry["edit_class"]
        if cls in streaks and streaks[cls] == "done":
            continue
        if entry["verdict"] == "harmed":
            streaks.setdefault(cls, []).append(entry)
        elif entry["verdict"] in ("helped", "neutral"):
            streaks[cls] = streaks.get(cls) or []
            if len(streaks[cls]) < threshold:
                streaks[cls] = "done"                      # broken before reaching threshold
    return {
        cls: (f"{len(entries)} consecutive `harmed` verdicts, most recently "
              f"{entries[0]['at']}: {entries[0]['why']}")
        for cls, entries in streaks.items()
        if isinstance(entries, list) and len(entries) >= threshold
    }


def render(archive: list[dict], retired_classes: dict[str, str]) -> str:
    """`evals/archive.json` is the machine copy; this is the line a human reads."""
    counts = {v: sum(1 for a in archive if a["verdict"] == v) for v in VERDICTS}
    parts = [f"{n} {v}" for v, n in counts.items() if n]
    head = f"{len(archive)} attributed change(s)" + (f" — {', '.join(parts)}" if parts else "")
    if retired_classes:
        head += f" · retired: {', '.join(sorted(retired_classes))}"
    return head


def write(archive: list[dict], retired_classes: dict[str, str],
          path: Path | None = None) -> Path:
    p = path or ARCHIVE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "note": ("Derived from evals/*.json — do not edit. Rebuilt on every grader run; "
                 "see grader/archive.py."),
        "retired_edit_classes": retired_classes,
        "changes": archive,
    }, indent=2, ensure_ascii=False) + "\n")
    return p


def load(path: Path | None = None) -> dict:
    try:
        return json.loads((path or ARCHIVE).read_text())
    except (OSError, json.JSONDecodeError):
        return {"retired_edit_classes": {}, "changes": []}
