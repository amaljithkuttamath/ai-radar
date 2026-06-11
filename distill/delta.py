"""Delta / movers computation — what turns a daily newsletter into a *radar*.

Compares the current scored set against a snapshot of the previous run (data/state.json,
committed alongside seen.json so runs build on each other) and classifies each candidate:

  new      — not present last run
  climbing — rank_key rose materially since last run (gained traction)
  cooled   — rank_key fell materially since last run

The result is fed into the digest prompt so synthesize can emit a "What changed" section,
and the current snapshot is written back for the next run. Pure + stdlib only — no model.

Snapshot is intentionally tiny (id -> {score, rank, title, url}) so committing it daily stays
cheap. Designed to no-op cleanly on the first run (everything is "new") and degrade to silence
if state is missing/corrupt.

Run as a library (synthesize imports compute_delta); also runnable for inspection:
  python -m distill.delta
"""
from __future__ import annotations
import os, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT  # noqa: E402
from math import log1p  # noqa: E402

STATE_PATH = ROOT / "data" / "state.json"
# "Climbing/cooled" must react to traction GROWTH, not just integer-score jumps. rank_key's
# tiebreak saturates in [0,1), so a star/upvote bump on an already-popular item barely moves
# it — diffing rank_key would make these sections almost never fire. Instead we diff a raw
# (unsaturated) signal magnitude, where doubling traction is a clear, detectable move.
# A score (integer tier) change is always a mover regardless of magnitude delta.
MAG_MOVE_EPS = float(os.environ.get("DELTA_MAG_EPS", "0.5"))   # ~+65% traction to register


def _load_state() -> dict[str, dict]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text()) or {}
        except Exception:
            return {}
    return {}


def _magnitude(item: dict) -> float:
    """Unsaturated traction magnitude (log-scaled so a 0->10 jump and 1000->10000 jump are
    comparable, but NOT squashed into [0,1) the way rank_key's tiebreak is)."""
    sig = item.get("signals") or {}
    return (log1p(sig.get("hf_upvotes") or 0)
            + 0.7 * log1p(sig.get("hf_likes") or 0)
            + 0.5 * log1p(sig.get("gh_stars") or 0)
            + 0.3 * log1p(sig.get("hn_points") or 0))


def _snapshot(items: list[dict]) -> dict[str, dict]:
    snap = {}
    for it in items:
        snap[it["id"]] = {
            "score": it.get("score") or 0,
            "mag": round(_magnitude(it), 4),
            "title": it.get("title", ""),
            "url": it.get("url", ""),
        }
    return snap


def compute_delta(items: list[dict]) -> dict:
    """Classify items vs. the previous run. Returns dict with new / climbing / cooled lists
    (each a compact row), plus first_run flag. Does NOT write state — call save_state for that
    so the caller controls when the snapshot is committed (only after a successful digest)."""
    prev = _load_state()
    new, climbing, cooled = [], [], []
    if not prev:
        # First run (or wiped state): everything is "new", nothing has history to move against.
        for it in items:
            new.append({"title": it.get("title", ""), "url": it.get("url", ""),
                        "score": it.get("score") or 0})
        return {"first_run": True, "new": new, "climbing": [], "cooled": []}

    for it in items:
        iid = it["id"]
        if iid not in prev:
            new.append({"title": it.get("title", ""), "url": it.get("url", ""),
                        "score": it.get("score") or 0})
            continue
        p = prev[iid]
        cur_score = it.get("score") or 0
        score_delta = cur_score - int(p.get("score", cur_score))
        mag_delta = _magnitude(it) - float(p.get("mag", _magnitude(it)))
        # A mover is either a score-tier change OR a meaningful traction-magnitude change.
        up = score_delta > 0 or mag_delta >= MAG_MOVE_EPS
        down = score_delta < 0 or mag_delta <= -MAG_MOVE_EPS
        row = {"title": it.get("title", ""), "url": it.get("url", ""), "score": cur_score,
               "score_delta": score_delta, "mag_delta": round(mag_delta, 2)}
        if up and not down:
            climbing.append(row)
        elif down and not up:
            cooled.append(row)

    climbing.sort(key=lambda x: (x["score_delta"], x["mag_delta"]), reverse=True)
    cooled.sort(key=lambda x: (x["score_delta"], x["mag_delta"]))
    return {"first_run": False, "new": new, "climbing": climbing, "cooled": cooled}


def save_state(items: list[dict]) -> None:
    """Persist this run's snapshot for the next run to diff against."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(_snapshot(items), indent=0, sort_keys=True))


def main() -> None:
    # Inspection entrypoint: print the delta against current scored items, no state write.
    from distill.synthesize import load_scored
    d = compute_delta(load_scored())
    print(json.dumps(d, indent=2))


if __name__ == "__main__":
    main()
